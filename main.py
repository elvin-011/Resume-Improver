# main.py
# Your FastAPI Backend

import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import uvicorn
import io
import re

# Import OpenAI
# import openai

# FastAPI and Pydantic
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel, Field
from typing import List, Dict

# File Processing Libs
import pdfplumber
from PIL import Image
# import pytesseract

# PDF Generation Lib
from fpdf import FPDF
from fastapi.responses import StreamingResponse

# --- 1. Setup and API Key Configuration ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found.")
else:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-2.5-flash')
app = FastAPI(
    title="AI Resume Improver API",
    description="Backend API for analyzing and improving resumes."
)

# --- 2. ATS Resume Templates ---
ATS_TEMPLATE_CLASSIC = """
[Full Name]
[Phone Number] | [Email Address] | [LinkedIn URL]

PROFESSIONAL SUMMARY
[One or two sentences summarizing your experience and skills.]

SKILLS
- Technical Skills: [List, e.g., Python, React, AWS, etc.]
- Soft Skills: [List, e.g., Communication, Teamwork, etc.]

EXPERIENCE
[Job Title] | [Company Name] | [City, State] | [Start Date] – [End Date or Present]
- [Accomplishment-driven bullet point.]
- [Quantifiable achievement, e.g., "Increased X by Y%".]

[Job Title] | [Company Name] | [City, State] | [Start Date] – [End Date]
- [Accomplishment-driven bullet point.]

PROJECTS
[Project Name] | [Link to GitHub/Live Demo]
- [Bullet point describing the project and its purpose.]
- [Bullet point describing your role and technologies used.]

EDUCATION
[Degree, e.g., B.S. Computer Science] | [University Name] | [Graduation Date]
"""

ATS_TEMPLATE_MODERN = """
[Full Name]
[City, State, Zip Code] | [Phone Number] | [Email Address] | [LinkedIn URL]

---
PROFESSIONAL SUMMARY
[A 3-4 line summary highlighting your key achievements and skills, 
tailored to the job description.]

---
CORE COMPETENCIES
- Skill 1: [Brief detail]
- Skill 2: [Brief detail]
- Skill 3: [Brief detail]
- Skill 4: [Brief detail]
- Skill 5: [Brief detail]
- Skill 6: [Brief detail]

---
PROFESSIONAL EXPERIENCE

[Company Name] | [City, State]
[Job Title] | [Start Date] – [End Date or Present]
- [Accomplishment-driven bullet point. Use a strong action verb.]
- [Quantifiable achievement, e.g., "Increased X by Y%".]
- [Another key responsibility or achievement.]

[Company Name] | [City, State]
[Job Title] | [Start Date] – [End Date]
- [Accomplishment-driven bullet point.]
- [Quantifiable achievement.]

---
PROJECTS

[Project Name] | [Technologies Used]
- [Bullet point describing the project and its purpose/outcome.]
- [Bullet point describing your specific contribution.]

---
EDUCATION

[University Name] | [City, State]
[Degree, e.g., B.S. Computer Science] | [Graduation Date]
"""

ATS_TEMPLATE_SKILLS_FIRST = """
[Full Name]
[Phone Number] | [Email Address] | [LinkedIn URL]

PROFESSIONAL SUMMARY
[A 2-3 line summary focused on your skills and career goals.]

---
TECHNICAL SKILLS

- Programming Languages: [List]
- Frameworks/Libraries: [List]
- Databases: [List]
- Cloud/DevOps: [List]

---
RELEVANT EXPERIENCE & PROJECTS

[Skill Category 1, e.g., "AI/Machine Learning"]
- [Project or Experience bullet point demonstrating this skill.]
- [Project or Experience bullet point demonstrating this skill.]

[Skill Category 2, e.g., "Web Development"]
- [Project or Experience bullet point demonstrating this skill.]
- [Project or Experience bullet point demonstrating this skill.]

[Skill Category 3, e.g., "Data Analysis"]
- [Project or Experience bullet point demonstrating this skill.]

---
WORK HISTORY (Chronological)

[Job Title] | [Company Name] | [Start Date] – [End Date or Present]
[Job Title] | [Company Name] | [Start Date] – [End Date]

---
EDUCATION
[Degree, e.g., B.S. Computer Science] | [University Name] | [Graduation Date]
"""

TEMPLATES: Dict[str, str] = {
    "classic": ATS_TEMPLATE_CLASSIC,
    "modern": ATS_TEMPLATE_MODERN,
    "skills_first": ATS_TEMPLATE_SKILLS_FIRST,
}

DEFAULT_JD = "No job description provided."

# --- 3. Helper Functions ---

def extract_text_from_file(uploaded_file: UploadFile):
    """Extracts text from PDF, TXT, or Image files."""
    try:
        file_bytes = uploaded_file.file.read()
        file_type = uploaded_file.content_type
        file_name = uploaded_file.filename

        if file_type == "text/plain" or file_name.endswith('.txt'):
            return file_bytes.decode("utf-8")
        
        elif file_type == "application/pdf" or file_name.endswith('.pdf'):
            import io
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        
        elif file_type in ["image/jpeg", "image/png"] or \
             file_name.endswith('.jpg') or file_name.endswith('.jpeg') or \
             file_name.endswith('.png'):
            import io
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
            return text
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


def run_analysis(resume_text: str, jd_text: str):
    """
    Calls Gemini to get analysis.
    Uses a different prompt if a JD is provided.
    """
    today = datetime.now().strftime("%B %d, %Y")
    
    is_general_request = (jd_text == DEFAULT_JD)
    
    prompt = ""
    if is_general_request:
        # Prompt for General Analysis (No JD)
        prompt = f"""
        **Today's date is {today}.**
        You are an expert resume reviewer. Analyze the following resume 
        for its general quality.

        **TASK 1: Analysis Summary**
        First, write a *brief, one-paragraph summary* of the resume's 
        overall strengths and professional presentation.
        
        **TASK 2: Weakness Analysis**
        After the summary, identify 1 scannable weaknesses. 
        Provide this as a clear, *numbered list* under a "Weaknesses:" heading.
        Focus on:
        1. Weak action verbs.
        2. Lack of quantifiable metrics.
        3. Vague descriptions.
        4. Date issues.

        **TASK 3: Total Count**
        At the very end, provide the total number of weaknesses on a new line.

        **Resume:**
        {resume_text}
        
        **YOUR RESPONSE FORMAT (Strict):**
        [Your one-paragraph summary here...]

        Weaknesses:
        1. [First weakness]
        ...
        Total Weaknesses: [Count]
        """
    else:
        # Prompt for JD-Specific Analysis (With JD)
        prompt = f"""
        **Today's date is {today}.**
        You are an expert ATS resume reviewer. Analyze the following resume 
        against the provided Job Description.

        **TASK 1: ATS Score**
        Provide a score.
        
        **TASK 2: Analysis Summary**
        After the score, write a *brief, one-paragraph summary* of how well
        the resume matches the job.

        **TASK 3: Weakness Analysis**
        After the summary, identify 1 scannable weaknesses (including missing keywords). 
        Provide this as a clear, *numbered list* under a "Weaknesses:" heading.
        
        **TASK 4: Total Count**
        At the very end, provide the total number of weaknesses on a new line.

        **Resume:**
        {resume_text}
        
        **Job Description:**
        {jd_text}
        
        **YOUR RESPONSE FORMAT (Strict):**
        ATS Score: [Score out of 100]
        
        [Your one-paragraph summary here...]

        Weaknesses:
        1. [First weakness]
        ...
        Total Weaknesses: [Count]
        """
        
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        ats_score = 0
        total_weaknesses = 1
        analysis_text = "" # This will be the main summary
        weakness_list_text = "" # This will be the weakness list

        if not is_general_request:
            if score_match := re.search(r"ATS Score: (\d+)", text, re.IGNORECASE):
                ats_score = int(score_match.group(1))
        
        if count_match := re.search(r"Total Weaknesses: (\d+)", text, re.IGNORECASE):
            total_weaknesses = int(count_match.group(1))

        # --- Robust Parsing Logic ---
        # 1. Find the weakness list
        if weakness_match := re.search(r"Weaknesses:", text, re.IGNORECASE):
            analysis_text = text[:weakness_match.start()]
            weakness_list_text = text[weakness_match.start():]
        else:
            analysis_text = text

        # 2. Clean up the parts
        analysis_text = re.sub(r"ATS Score: \d+", "", analysis_text, flags=re.IGNORECASE)
        analysis_text = re.sub(r"Total Weaknesses: \d+", "", analysis_text, flags=re.IGNORECASE)
        weakness_list_text = re.sub(r"Total Weaknesses: \d+", "", weakness_list_text, flags=re.IGNORECASE)
        
        # 3. Check for "None" or empty summary
        if not analysis_text.strip() or analysis_text.strip().lower() == "none":
            analysis_text = "Here is the analysis of your resume:"
        
        # 4. Recombine
        final_analysis = (analysis_text.strip() + "\n\n" + weakness_list_text.strip()).strip()

        return {
            "analysis_results": final_analysis,
            "ats_score": ats_score,
            "total_weaknesses": max(1, total_weaknesses)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during AI analysis: {str(e)}")

# --- 4. Pydantic Models ---
class AnalysisResponse(BaseModel):
    resume_text: str
    analysis_results: str
    ats_score: int
    total_weaknesses: int

class StartChatRequest(BaseModel):
    analysis_results: str

class StartChatResponse(BaseModel):
    first_ai_message: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    resume_text: str
    analysis_results: str
    messages: List[ChatMessage]
    jd_text: str

class ChatResponse(BaseModel):
    ai_response: str
    weakness_resolved: bool

class GenerateResumeRequest(BaseModel):
    resume_text: str
    messages: List[ChatMessage]
    template_name: str = "classic"
    jd_text: str

class BuildChatRequest(BaseModel):
    messages: List[ChatMessage]
    jd_text: str 

class BuildChatResponse(BaseModel):
    ai_response: str
    build_complete: bool

class SynthesizeRequest(BaseModel):
    messages: List[ChatMessage]
    jd_text: str
    
class TranscribeResponse(BaseModel):
    text: str

# --- 5. API Endpoints ---

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume_endpoint(
    file: UploadFile = File(...),
    jd_text: str = Form(DEFAULT_JD)
):
    print(f"Received file: {file.filename}")
    resume_text = extract_text_from_file(file)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not extract text from file.")
    
    analysis_data = run_analysis(resume_text, jd_text)
    
    return {"resume_text": resume_text, **analysis_data}


@app.post("/start-chat", response_model=StartChatResponse)
async def start_chat_endpoint(request: StartChatRequest):
    
    start_chat_prompt = f"""
    You are a proactive resume coach. You have just completed this analysis:
    ---ANALYSIS---
    {request.analysis_results}
    ---
    Start the chat session. Greet the user, state the *first* weakness
    you want to fix, and ask a specific, probing question.
    """
    try:
        response = model.generate_content(start_chat_prompt)
        
        ai_message = response.text
        if not ai_message or not ai_message.strip():
            ai_message = "I'm sorry, I had an error processing that request. Let's start with your first work experience. Can you tell me about it?"
        
        return {"first_ai_message": ai_message}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting chat: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    
    today = datetime.now().strftime("%B %d, %Y")
    user_prompt = request.messages[-1].content
    
    is_general_request = (request.jd_text == DEFAULT_JD)
    
    context_prompt = ""
    if is_general_request:
        # Prompt for General Chat (No JD)
        context_prompt = f"""
        You are a proactive, expert resume coach. Today's date is {today}.
        Your Goal: Lead this conversation to fix all weaknesses from the 'initial analysis'.
        
        Context:
        - The user's full resume: {request.resume_text}
        - The initial analysis (weaknesses): {request.analysis_results}
        - Our chat history: {request.messages}

        Your Task:
        1. Respond to the user's last message: "{user_prompt}".
        2. Ask probing questions to get metrics and details for weak bullet points.
        3. When a section is fixed, say "Great, that section looks solid," 
           and *explicitly state the [WEAKNESS_RESOLVED] token on a new line*.
        """
    else:
        # Prompt for JD-Specific Chat (With JD)
        context_prompt = f"""
        You are a proactive, expert resume coach. Today's date is {today}.
        
        **Your Goal:** Lead this conversation to:
        1.  Fix all weaknesses from the 'initial analysis'.
        2.  **Tailor the resume** to the 'Job Description'.
        
        **Context:**
        - The user's full resume: {request.resume_text}
        - The initial analysis (weaknesses): {request.analysis_results}
        - **The Job Description (Target):** {request.jd_text}
        - Our chat history: {request.messages}

        **Your Task:**
        1.  **Respond** to the user's last message: "{user_prompt}".
        2.  **Be proactive:** When suggesting rewrites, use keywords 
            from the Job Description.
        3.  **When a weakness is fixed,** say "Great, that section looks solid," 
            and *explicitly state the [WEAKNESS_RESOLVED] token on a new line*.
        """
    
    try:
        response = model.generate_content(context_prompt)
        ai_response_text = response.text
        
        resolved = "[WEAKNESS_RESOLVED]" in ai_response_text
        ai_response_text = ai_response_text.replace("[WEAKNESS_RESOLVED]", "").strip()
        
        return {
            "ai_response": ai_response_text,
            "weakness_resolved": resolved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat response: {str(e)}")


@app.post("/generate-resume")
async def generate_resume_endpoint(request: GenerateResumeRequest):
    
    try:
        template_str = TEMPLATES.get(request.template_name, TEMPLATES["classic"])
        is_general_request = (request.jd_text == DEFAULT_JD)
        synthesis_prompt = ""

        if is_general_request:
            # Prompt for General PDF (No JD)
            synthesis_prompt = f"""
            You are a meticulous resume editor. Your job is to generate a
            final, ATS-friendly resume.
            
            **RULES (Strict):**
            1.  **Use Improved Text:** You *must* use the new, improved bullet 
                points from the 'Chat History'.
            2.  **Replace, Don't Blend:** If the chat history has an improvement 
                for a section, use the new version and *discard* the old one.
            3.  **Fix Weak Verbs:** Aggressively replace weak, present-tense
                verbs with strong, past-tense action verbs.
            4.  **Format:** Format the final output *only* according to the
                ATS template. Do NOT include your own commentary.

            **Context:**
            - **ATS Template Structure:**
              {template_str}
            - **Original Resume (Base):**
              {request.resume_text}
            - **Chat History (Improvements):**
              {request.messages}
            
            **Your Output (Final Resume Text Only):**
            """
        else:
            # Prompt for JD-Specific PDF (With JD)
            synthesis_prompt = f"""
            You are a meticulous resume editor. Your job is to generate a
            final, ATS-friendly resume.
            
            **RULES (Strict):**
            1.  **Tailor to JD:** You *must* use keywords from the 'Job Description' 
                to tailor the 'Professional Summary' and relevant bullet points.
            2.  **Use Improved Text:** You *must* use the new, improved bullet 
                points from the 'Chat History'.
            3.  **Replace, Don't Blend:** If the chat history has an improvement 
                for a section, use the new version and *discard* the old one.
            4.  **Fix Weak Verbs:** Aggressively replace weak, present-tense
                verbs with strong, past-tense action verbs.
            5.  **Format:** Format the final output *only* according to the
                ATS template. Do NOT include your own commentary.

            **Context:**
            - **ATS Template Structure:**
              {template_str}
            - **Original Resume (Base):**
              {request.resume_text}
            - **Chat History (Improvements):**
              {request.messages}
            - **Job Description (Target):**
              {request.jd_text}
            
            **Your Output (Final Resume Text Only):**
            """

        response = model.generate_content(synthesis_prompt)
        final_resume_text = response.text
        
        # --- FIX: Replace unsupported characters for PDF ---
        replacements = {
            "\u2013": "-",  # en dash
            "\u2014": "--", # em dash
            "\u2018": "'",  # smart single quote left
            "\u2019": "'",  # smart single quote right
            "\u201c": '"',  # smart double quote left
            "\u201d": '"',  # smart double quote right
            "\u2022": "-",  # bullet
        }
        for char, replacement in replacements.items():
            final_resume_text = final_resume_text.replace(char, replacement)
        # ---------------------------------------------------

        pdf = FPDF()
        pdf.add_page()
        # Using built-in font Helvetica to avoid missing .ttf errors
        pdf.set_font("Helvetica", size=10)
        
        # Safety encoding to prevent crashes on other unicode chars
        safe_text = final_resume_text.encode('latin-1', 'replace').decode('latin-1')
        
        pdf.multi_cell(0, 5, safe_text)
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment;filename=improved_resume_{request.template_name}.pdf"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured. Voice features are disabled.")

    try:
        audio_bytes = await file.read()
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"
        
        client = openai.OpenAI(api_key=openai_api_key)
        
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        
        print(f"Whisper transcription: {transcription.text}")
        return {"text": transcription.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")

# --- [NEW] Endpoint 7: Start Build Chat ---
@app.post("/start-build-chat", response_model=StartChatResponse)
async def start_build_chat_endpoint(request: BuildChatRequest):
    """Starts the guided 'build from scratch' interview."""
    is_general_request = (request.jd_text == DEFAULT_JD)
    first_prompt = ""
    
    if is_general_request:
        first_prompt = "Hi! I'm here to help you build a new resume from scratch. Let's start with the basics. What is your full name?"
    else:
        first_prompt = f"Hi! I see you want to build a new resume targeted at a job. I'll ask you questions to build it. Let's start with your full name."

    return {"first_ai_message": first_prompt}

# --- [NEW] Endpoint 8: Build Chat ---
@app.post("/build-chat", response_model=BuildChatResponse)
async def build_chat_endpoint(request: BuildChatRequest):
    """Handles the 'interview' conversation for building a resume."""
    user_prompt = request.messages[-1].content
    is_general_request = (request.jd_text == DEFAULT_JD)
    
    build_prompt = ""
    if is_general_request:
        build_prompt = f"""
        You are an expert resume interviewer. Your goal is to patiently
        ask the user questions, one by one, to get all the information
        needed to build a resume.
        
        **Sections to cover (in order):**
        1.  Full Name
        2.  Contact Info (Phone, Email, LinkedIn)
        3.  Professional Summary (ask for their title/goals)
        4.  Skills (ask for technical and soft skills)
        5.  Work Experience (ask for 2-3 jobs, one by one)
        6.  Projects (ask for 1-2 projects)
        7.  Education

        **Chat History:**
        {request.messages}

        **Your Task:**
        1.  Look at the chat history to see what you just asked.
        2.  Based on the user's last answer ("{user_prompt}"), ask the *next*
            logical question.
        3.  If you have just collected the final piece of info (Education),
            end your response with the exact token on a new line:
            [BUILD_COMPLETE]
        """
    else:
        build_prompt = f"""
        You are an expert resume interviewer, and you are helping a user
        build a resume *targeted* at a specific job.
        
        **Job Description (Target):**
        {request.jd_text}
        
        **Sections to cover (in order):**
        1.  Full Name
        2.  Contact Info (Phone, Email, LinkedIn)
        3.  Professional Summary (ask for their title, then help them
            add keywords from the JD)
        4.  Skills (ask for their skills, then suggest skills from the JD)
        5.  Work Experience (ask for 2-3 jobs)
        6.  Projects (ask for 1-2 projects)
        7.  Education
        
        **Chat History:**
        {request.messages}

        **Your Task:**
        1.  Look at the chat history to see what you just asked.
        2.  Based on the user's last answer ("{user_prompt}"), ask the *next*
            logical question. Use the JD to help guide them.
        3.  If you have just collected the final piece of info (Education),
            end your response with the exact token on a new line:
            [BUILD_COMPLETE]
        """
        
    try:
        response = model.generate_content(build_prompt)
        ai_response_text = response.text
        
        build_complete = "[BUILD_COMPLETE]" in ai_response_text
        ai_response_text = ai_response_text.replace("[BUILD_COMPLETE]", "").strip()
        
        return {
            "ai_response": ai_response_text,
            "build_complete": build_complete
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in build-chat response: {str(e)}")

# --- [NEW] Endpoint 9: Synthesize and Analyze ---
@app.post("/synthesize-and-analyze", response_model=AnalysisResponse)
async def synthesize_and_analyze_endpoint(request: SynthesizeRequest):
    """Takes a build-chat history, synthesizes a resume, analyzes it, and returns the analysis."""
    try:
        # Step 1: Synthesize the resume
        synthesis_prompt = f"""
        You are a resume synthesizer. Take the following interview
        conversation and format it *only* into a simple, text-based resume.
        Do not add any commentary.
        
        **Chat History:**
        {request.messages}
        
        **Your Output (Resume Text Only):**
        """
        
        response = model.generate_content(synthesis_prompt)
        resume_text = response.text
        
        if not resume_text or len(resume_text) < 50: 
             raise HTTPException(status_code=500, detail="Failed to synthesize resume from chat.")

        # Step 2: Analyze the new resume (loop-back)
        analysis_data = run_analysis(resume_text, request.jd_text)
        
        # Step 3: Return the combined response
        return {
            "resume_text": resume_text,
            **analysis_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during synthesize/analyze: {str(e)}")


# --- 6. Run the Server ---
if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
