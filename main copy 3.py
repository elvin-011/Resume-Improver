# main.py
# Your new FastAPI Backend

import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import uvicorn  # Server to run the app

# FastAPI and Pydantic (for data models)
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import List

# File Processing Libs
import pdfplumber
from PIL import Image
import pytesseract

# --- 1. Setup and API Key Configuration ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found.")
    # In a real app, you'd have more robust error handling
else:
    genai.configure(api_key=api_key)

# Use the correct model name
model = genai.GenerativeModel('gemini-2.5-flash')

# Initialize the FastAPI app
app = FastAPI(
    title="AI Resume Improver API",
    description="Backend API for analyzing and improving resumes."
)

# --- 2. Helper Functions (Your Core Logic) ---
# These are the same as before, just part of the backend

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
        # Raise an HTTPException so the user gets a proper error
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


def run_analysis(resume_text: str):
    """Calls the Gemini API to get an initial analysis."""
    today = datetime.now().strftime("%B %d, %Y")
    try:
        prompt = f"""
        **Today's date is {today}.** Analyze the following resume. Be critical and specific. Identify clear strengths 
        and, more importantly, *actionable weaknesses*.
        
        Focus on:
        1. Weak action verbs.
        2. Lack of quantifiable metrics.
        3. Vague descriptions.
        4. Date issues (e.g., "Present" roles).

        Resume:
        {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during AI analysis: {str(e)}")

# --- 3. Pydantic Models (Defining API Data) ---
# These models define the structure of your API's JSON requests and responses

class AnalysisResponse(BaseModel):
    resume_text: str
    analysis_results: str

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
    messages: List[ChatMessage] # The frontend sends the *entire* chat history

class ChatResponse(BaseModel):
    ai_response: str

# --- 4. API Endpoints (The "Frontend-facing" part) ---

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume_endpoint(file: UploadFile = File(...)):
    """
    Endpoint 1: Upload a resume file.
    Receives a file, extracts text, and returns the text + AI analysis.
    """
    print(f"Received file: {file.filename}")
    resume_text = extract_text_from_file(file)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not extract text from file.")
    
    analysis_results = run_analysis(resume_text)
    
    return {
        "resume_text": resume_text,
        "analysis_results": analysis_results
    }

@app.post("/start-chat", response_model=StartChatResponse)
async def start_chat_endpoint(request: StartChatRequest):
    """
    Endpoint 2: User clicks "Start Improvement."
    Receives the analysis and returns the AI's first proactive message.
    """
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
        return {"first_ai_message": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting chat: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint 3: User sends a message.
    Receives all context (resume, analysis, history) and returns one new AI message.
    """
    today = datetime.now().strftime("%B %d, %Y")
    
    # The last message in the list is the new user prompt
    user_prompt = request.messages[-1].content
    
    context_prompt = f"""
    You are a proactive, expert resume coach. Today's date is {today}.
    Your Goal: Lead this conversation to fix *all* weaknesses from the analysis.
    
    Context:
    - The user's full resume: {request.resume_text}
    - The initial analysis: {request.analysis_results}
    - Our chat history: {request.messages}

    Your Task:
    1. Respond to the user's last message: "{user_prompt}".
    2. Ask probing questions to get metrics and details.
    3. When a section is fixed, move to the next weak section.
    """
    
    try:
        response = model.generate_content(context_prompt)
        return {"ai_response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat response: {str(e)}")

# --- 5. Run the Server ---
if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)