from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Document processing libraries
import PyPDF2
from PIL import Image
import pytesseract
import docx
import io
import re

# LiteLLM for AI model integration
from litellm import completion
import litellm

app = FastAPI(title="Resume Analysis System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure LiteLLM for Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# Enable verbose logging for debugging
litellm.set_verbose = False

class ResumeData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience: List[str] = []
    education: List[str] = []
    raw_text: str
    extracted_at: str

class AnalysisResponse(BaseModel):
    resume_data: dict
    ai_analysis: dict
    status: str

# ... (other Pydantic models remain the same) ...
class ImprovementQuestion(BaseModel):
    question_id: str
    question: str
    category: str
    context: str

class ImprovementAnswer(BaseModel):
    question_id: str
    answer: str

class ImprovementRequest(BaseModel):
    resume_text: str
    weaknesses: List[str]
    current_data: dict

class ImprovedContentResponse(BaseModel):
    category: str
    original_content: str
    improved_content: str
    explanation: str

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc_file = io.BytesIO(file_content)
        doc = docx.Document(doc_file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing DOCX: {str(e)}")

def extract_text_from_image(file_content: bytes) -> str:
    """Extract text from image using OCR"""
    try:
        image = Image.open(io.BytesIO(file_content))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")

# --- IMPROVEMENT 1: Renamed original function ---
def parse_resume_with_regex(text: str) -> ResumeData:
    """Parse resume text using basic regex (Fallback method)"""
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    email = emails[0] if emails else None
    
    # Extract phone
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phones = re.findall(phone_pattern, text)
    phone = phones[0] if phones else None
    
    # Extract name (usually first line)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    name = lines[0] if lines else None
    
    # Extract skills (basic keyword matching)
    skills_keywords = ['python', 'java', 'javascript', 'react', 'sql', 'machine learning', 
                       'data analysis', 'project management', 'communication', 'leadership']
    skills = [skill for skill in skills_keywords if skill.lower() in text.lower()]
    
    # Extract experience and education sections
    experience = []
    education = []
    
    text_lower = text.lower()
    if 'experience' in text_lower:
        exp_index = text_lower.index('experience')
        exp_section = text[exp_index:exp_index+500]
        experience = [line for line in exp_section.split('\n') if len(line.strip()) > 20][:3]
    
    if 'education' in text_lower:
        edu_index = text_lower.index('education')
        edu_section = text[edu_index:edu_index+300]
        education = [line for line in edu_section.split('\n') if len(line.strip()) > 10][:3]
    
    return ResumeData(
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        experience=experience,
        education=education,
        raw_text=text,
        extracted_at=datetime.now().isoformat()
    )

# --- IMPROVEMENT 2: Added new AI-powered parser ---
def parse_resume_with_ai(text: str) -> ResumeData:
    """
    Parse resume text using AI to extract structured information.
    """
    prompt = f"""
    You are an expert resume parser. Analyze the following resume text and extract the
    candidate's information. Return *only* a valid JSON object with the following keys:
    - "name": (string) The candidate's full name.
    - "email": (string) The candidate's primary email address.
    - "phone": (string) The candidate's primary phone number.
    - "skills": (list of strings) A list of key skills, technologies, and tools.
    - "experience": (list of strings) A list of brief descriptions of their most recent job roles (e.g., "Software Engineer at Google").
    - "education": (list of strings) A list of their degrees and institutions (e.g., "B.S. in Computer Science at MIT").

    If a field is not found, return null for string fields or an empty list [] for list fields.

    Resume Text:
    ---
    {text[:3000]}
    ---
    """

    try:
        if GEMINI_API_KEY == "your-gemini-api-key-here" or not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY not configured for AI parsing.")

        response = completion(
            model="gemini/gemini-1.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, # Low temp for factual extraction
            api_key=GEMINI_API_KEY
        )
        
        ai_response = response.choices[0].message.content
        
        # Extract JSON from the response
        start_idx = ai_response.find('{')
        end_idx = ai_response.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise json.JSONDecodeError("No JSON object found in AI response.", ai_response, 0)
            
        json_str = ai_response[start_idx:end_idx]
        parsed_data = json.loads(json_str)
        
        # Validate that all keys are present
        required_keys = ['name', 'email', 'phone', 'skills', 'experience', 'education']
        for key in required_keys:
            if key not in parsed_data:
                parsed_data[key] = None if key in ['name', 'email', 'phone'] else []

        return ResumeData(
            name=parsed_data.get('name'),
            email=parsed_data.get('email'),
            phone=parsed_data.get('phone'),
            skills=parsed_data.get('skills', []),
            experience=parsed_data.get('experience', []),
            education=parsed_data.get('education', []),
            raw_text=text,
            extracted_at=datetime.now().isoformat()
        )

    except Exception as e:
        print(f"Error during AI parsing: {e}")
        # Re-raise the exception to be caught by the calling function
        raise


def analyze_resume_with_ai(resume_data: ResumeData) -> dict:
    """Analyze resume using AI model via LiteLLM"""
    try:
        # Check if API key is configured
        if GEMINI_API_KEY == "your-gemini-api-key-here" or not GEMINI_API_KEY:
            return {
                "weaknesses": [
                    "AI analysis unavailable - API key not configured",
                    "Please set GEMINI_API_KEY environment variable",
                    "Get your key from: https://makersuite.google.com/app/apikey"
                ],
                "tips": [
                    "Configure your Gemini API key to enable AI analysis",
                    "Set environment variable: export GEMINI_API_KEY='your-key'",
                    "Or edit main.py and set GEMINI_API_KEY variable"
                ],
                "score": 0,
                "summary": "AI analysis requires Gemini API key configuration"
            }
        
        prompt = f"""You are a professional resume analyst. Analyze the following resume and provide:

1. Key Weaknesses: List 3-5 specific weaknesses in the resume
2. Improvement Tips: Provide 3-5 actionable tips to improve the resume
3. Overall Score: Rate the resume from 1-10
4. Summary: Brief summary of the candidate's profile

Resume Text:
{resume_data.raw_text[:2000]}

Provide your analysis in JSON format with keys: weaknesses (list), tips (list), score (number), summary (string)"""

        # Call Gemini using LiteLLM - correct model format
        response = completion(
            model="gemini/gemini-1.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            api_key=GEMINI_API_KEY
        )
        
        ai_response = response.choices[0].message.content
        
        # Try to parse JSON from response
        try:
            # Look for JSON in the response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = ai_response[start_idx:end_idx]
                analysis = json.loads(json_str)
            else:
                # Fallback: create structured response
                analysis = {
                    "weaknesses": ["Analysis completed - see full response"],
                    "tips": ["Review the detailed feedback provided"],
                    "score": 7,
                    "summary": ai_response[:200],
                    "raw_response": ai_response
                }
        except json.JSONDecodeError:
            analysis = {
                "weaknesses": ["Unable to parse structured feedback"],
                "tips": ["Review raw AI response below"],
                "score": 0,
                "summary": ai_response[:500],
                "raw_response": ai_response
            }
        
        return analysis
        
    except Exception as e:
        error_msg = str(e)
        return {
            "weaknesses": [
                f"Error in AI analysis: {error_msg}",
                "Please check API key configuration",
                "Verify internet connection"
            ],
            "tips": [
                "Set GEMINI_API_KEY environment variable",
                "Get API key from: https://makersuite.google.com/app/apikey",
                "Check LiteLLM documentation for Gemini setup"
            ],
            "score": 0,
            "summary": "Analysis failed - check configuration"
        }

def generate_improvement_questions(resume_data: dict, weaknesses: List[str]) -> List[dict]:
    """Generate dynamic questions based on resume weaknesses"""
    try:
        if GEMINI_API_KEY == "your-gemini-api-key-here" or not GEMINI_API_KEY:
            return []
        
        prompt = f"""Based on the following resume weaknesses, generate 5-8 specific, targeted questions to gather information needed to improve the resume.

Weaknesses identified:
{json.dumps(weaknesses, indent=2)}

Current Resume Data:
- Name: {resume_data.get('name', 'Not provided')}
- Skills: {', '.join(resume_data.get('skills', []))}
- Experience: {len(resume_data.get('experience', []))} entries
- Education: {len(resume_data.get('education', []))} entries

Generate questions that:
1. Are specific to the identified weaknesses
2. Help gather concrete details (numbers, achievements, technologies)
3. Focus on quantifiable results and impact
4. Explore missing information
5. Clarify vague points

Return ONLY a JSON array with this structure:
[
  {{
    "question_id": "q1",
    "question": "The specific question to ask",
    "category": "experience/skills/education/achievements/summary",
    "context": "Why this question is important"
  }}
]"""

        response = completion(
            model="gemini/gemini-1.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            api_key=GEMINI_API_KEY
        )
        
        ai_response = response.choices[0].message.content
        
        # Extract JSON
        start_idx = ai_response.find('[')
        end_idx = ai_response.rfind(']') + 1
        if start_idx != -1 and end_idx != 0:
            json_str = ai_response[start_idx:end_idx]
            questions = json.loads(json_str)
            return questions
        
        return []
        
    except Exception as e:
        print(f"Error generating questions: {str(e)}")
        return []

def generate_improved_content(resume_data: dict, weaknesses: List[str], answers: List[dict]) -> List[dict]:
    """Generate improved resume content based on user answers"""
    try:
        if GEMINI_API_KEY == "your-gemini-api-key-here" or not GEMINI_API_KEY:
            return []
        
        # Prepare answers text
        answers_text = "\n".join([f"Q: {a.get('question', '')}\nA: {a.get('answer', '')}" for a in answers])
        
        prompt = f"""You are a professional resume writer. Based on the original resume and the user's answers, generate improved, professional resume content.

Original Resume Text:
{resume_data.get('raw_text', '')[:1500]}

Identified Weaknesses:
{json.dumps(weaknesses, indent=2)}

User's Additional Information:
{answers_text}

Generate improved content for each major section. For each improvement:
1. Make it ATS-friendly with relevant keywords
2. Use strong action verbs
3. Quantify achievements where possible
4. Keep it concise and impactful
5. Follow professional resume writing standards

Return ONLY a JSON array with this structure:
[
  {{
    "category": "professional_summary/experience/skills/education/achievements",
    "original_content": "Brief excerpt from original",
    "improved_content": "The improved version",
    "explanation": "Why this is better"
  }}
]"""

        response = completion(
            model="gemini/gemini-1.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            api_key=GEMINI_API_KEY,
            max_tokens=2000
        )
        
        ai_response = response.choices[0].message.content
        
        # Extract JSON
        start_idx = ai_response.find('[')
        end_idx = ai_response.rfind(']') + 1
        if start_idx != -1 and end_idx != 0:
            json_str = ai_response[start_idx:end_idx]
            improvements = json.loads(json_str)
            return improvements
        
        return []
        
    except Exception as e:
        print(f"Error generating improvements: {str(e)}")
        return []

@app.post("/api/analyze-resume", response_model=AnalysisResponse)
async def analyze_resume(file: UploadFile = File(...)):
    """Main endpoint to upload and analyze resume"""
    
    # Read file content
    content = await file.read()
    filename = file.filename.lower()
    
    # Extract text based on file type
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(content)
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(content)
    elif filename.endswith(('.jpg', '.jpeg', '.png')):
        text = extract_text_from_image(content)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    if not text or len(text) < 50:
        raise HTTPException(status_code=400, detail="Unable to extract sufficient text from file")
    
    # --- IMPROVEMENT 3: Updated parsing logic with fallback ---
    try:
        # Try AI-powered parsing first
        print("Attempting AI parsing...")
        resume_data = parse_resume_with_ai(text)
        print("AI parsing successful.")
    except Exception as e:
        # Fallback to regex parsing
        print(f"AI parsing failed ({e}). Falling back to regex parsing.")
        resume_data = parse_resume_with_regex(text)
    # --- END OF IMPROVEMENT ---
    
    # Analyze with AI
    ai_analysis = analyze_resume_with_ai(resume_data)
    
    # Save to JSON (simulating database)
    output_data = {
        "resume_data": resume_data.dict(),
        "ai_analysis": ai_analysis,
        "file_name": file.filename,
        "processed_at": datetime.now().isoformat()
    }
    
    # Save to JSON file
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = f"data/resume_{timestamp}.json"
    
    with open(json_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    return AnalysisResponse(
        resume_data=output_data["resume_data"],
        ai_analysis=ai_analysis,
        status="success"
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Resume Analysis System"}

@app.get("/api/resumes")
async def get_all_resumes():
    """Get all analyzed resumes"""
    try:
        resumes = []
        if os.path.exists("data"):
            for filename in os.listdir("data"):
                if filename.endswith(".json"):
                    with open(f"data/{filename}", 'r') as f:
                        resumes.append(json.load(f))
        return {"resumes": resumes, "count": len(resumes)}
    except Exception as e:
        return {"resumes": [], "count": 0, "error": str(e)}

@app.post("/api/generate-questions")
async def generate_questions(request: ImprovementRequest):
    """Generate improvement questions based on resume analysis"""
    questions = generate_improvement_questions(
        request.current_data,
        request.weaknesses
    )
    return {"questions": questions, "count": len(questions)}

@app.post("/api/generate-improvements")
async def generate_improvements(data: dict):
    """Generate improved resume content based on answers"""
    resume_data = data.get('resume_data', {})
    weaknesses = data.get('weaknesses', [])
    answers = data.get('answers', [])
    
    improvements = generate_improved_content(resume_data, weaknesses, answers)
    
    return {
        "improvements": improvements,
        "count": len(improvements),
        "status": "success"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)