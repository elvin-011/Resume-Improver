# app.py
import streamlit as st
import requests
import io
import subprocess
import sys
import time

# --- 1. AUTOMATIC BACKEND LAUNCHER ---
@st.cache_resource
def start_backend():
    # Launches main.py in the background
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
    process = subprocess.Popen(cmd)
    time.sleep(3) # Wait for server to start
    return process

start_backend()
BACKEND_URL = "http://127.0.0.1:8000"

TEMPLATE_OPTIONS = {
    "classic": "Classic (Single-Column)",
    "modern": "Modern (With Competencies)",
    "skills_first": "Skills-First (Functional)",
}

# --- 1. Page Rendering Functions ---

def render_home_page():
    st.header("Step 1: Upload Your Resume")
    st.write("Upload your resume (PDF, TXT).")
    
    # Removed jpg/png from accepted types as OCR is disabled
    uploaded_file = st.file_uploader(
        "Upload Resume",
        type=['pdf', 'txt'],
        label_visibility="collapsed"
    )
    
    st.header("Step 2: Add Job Description (Optional)")
    st.write("Paste the job description to get an ATS compatibility score.")
    
    # FIX: Uncontrolled widget
    jd_text = st.text_area(
        "Paste Job Description Here:",
        value=st.session_state.jd_text,
        height=150
    )
    
    if st.button("Analyze Resume", key="analyze_btn", type="primary"):
        if uploaded_file is not None:
            with st.spinner(f"Uploading and processing {uploaded_file.name}..."):
                
                jd_text_to_send = jd_text if jd_text else "No job description provided."
                
                files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {'jd_text': jd_text_to_send}
                
                try:
                    response = requests.post(f"{BACKEND_URL}/analyze", files=files, data=data)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.resume_text = data.get("resume_text")
                        st.session_state.analysis_results = data.get("analysis_results")
                        st.session_state.ats_score = data.get("ats_score", 0)
                        st.session_state.total_weaknesses = data.get("total_weaknesses", 1)
                        st.session_state.jd_text = jd_text_to_send
                        st.session_state.weaknesses_covered = 0
                        st.session_state.final_pdf_bytes = None
                        st.session_state.app_state = 'analysis_done'
                        st.rerun()
                    else:
                        st.error(f"Error from backend: {response.json().get('detail')}")
                
                except requests.exceptions.ConnectionError:
                    st.error("Backend is starting up... please try again in 5 seconds.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.error("Please upload a resume file to continue.")

def render_analysis_page():
    st.header("Step 2: Review Analysis")
    
    if st.session_state.ats_score > 0:
        st.metric(
            "ATS Compatibility Score", 
            f"{st.session_state.ats_score} / 100",
            help="This score compares your resume to the job description you provided."
        )
    else:
        st.info("No job description was provided, so a general analysis was performed.")
    
    st.info("Here is the initial analysis of your resume:")
    st.markdown(st.session_state.analysis_results)
    
    st.write("---")
    st.header("Step 3: Start AI Improvement")
    st.write(f"I've found **{st.session_state.total_weaknesses}** key area(s) to improve. I will guide you step-by-step.")
    
    if st.button("Start AI Improvement Process", key="start_improve_btn", type="primary"):
        with st.spinner("Preparing your guided session..."):
            payload = {"analysis_results": st.session_state.analysis_results}
            try:
                response = requests.post(f"{BACKEND_URL}/start-chat", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.app_state = 'chat_mode'
                    st.session_state.messages = [
                        {"role": "assistant", "content": data.get("first_ai_message")}
                    ]
                    st.rerun()
                else:
                    st.error(f"Error from backend: {response.json().get('detail')}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

def render_chat_page():
    st.header("Step 3: AI Improvement Chat")
    
    progress_percent = (st.session_state.weaknesses_covered / st.session_state.total_weaknesses)
    progress_text = f"Improvements: {st.session_state.weaknesses_covered} of {st.session_state.total_weaknesses} covered"
    st.progress(progress_percent, text=progress_text)
    
    st.write("Follow my lead! I'll guide you to fix your resume's weak points.")

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    is_complete = (st.session_state.weaknesses_covered == st.session_state.total_weaknesses)
    
    # Helper to send message
    def send_chat_message(prompt_text):
        st.session_state.messages.append({"role": "user", "content": prompt_text})
        st.chat_message("user").write(prompt_text)
        
        payload = {
            "resume_text": st.session_state.resume_text,
            "analysis_results": st.session_state.analysis_results,
            "messages": st.session_state.messages,
            "jd_text": st.session_state.jd_text
        }
        
        with st.spinner("Thinking..."):
            try:
                response = requests.post(f"{BACKEND_URL}/chat", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("weakness_resolved"):
                        st.session_state.weaknesses_covered += 1
                    st.session_state.messages.append({"role": "assistant", "content": data.get("ai_response")})
                    st.rerun() 
                else:
                    st.error(f"Error from backend: {response.json().get('detail')}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

    if is_complete:
        st.success("Great job! We've covered all the main improvements.")
        st.write("---")
        st.subheader("Generate Your Final Resume")
        
        selected_template_key = st.selectbox(
            "Choose Your ATS Template:",
            options=list(TEMPLATE_OPTIONS.keys()),
            format_func=lambda key: TEMPLATE_OPTIONS[key]
        )
        
        if st.button("Generate Final Resume PDF"):
            with st.spinner(f"Creating your new '{TEMPLATE_OPTIONS[selected_template_key]}' resume..."):
                payload = {
                    "resume_text": st.session_state.resume_text,
                    "messages": st.session_state.messages,
                    "template_name": selected_template_key,
                    "jd_text": st.session_state.jd_text
                }
                try:
                    response = requests.post(f"{BACKEND_URL}/generate-resume", json=payload)
                    if response.status_code == 200:
                        st.session_state.final_pdf_bytes = response.content
                        st.session_state.final_pdf_name = f"improved_resume_{selected_template_key}.pdf"
                        st.rerun()
                    else:
                        st.error(f"Error generating PDF: {response.json().get('detail')}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        if st.session_state.final_pdf_bytes:
            st.download_button(
                label=f"Download {st.session_state.final_pdf_name}",
                data=st.session_state.final_pdf_bytes,
                file_name=st.session_state.final_pdf_name,
                mime="application/pdf",
                type="primary"
            )

    # Chat input
    if not is_complete:
        if prompt := st.chat_input("Your response..."):
            send_chat_message(prompt)

def clear_session():
    st.session_state.app_state = 'home'
    st.session_state.resume_text = ""
    st.session_state.analysis_results = ""
    st.session_state.messages = []
    st.session_state.ats_score = 0
    st.session_state.total_weaknesses = 0
    st.session_state.weaknesses_covered = 0
    st.session_state.final_pdf_bytes = None
    st.session_state.final_pdf_name = ""
    st.session_state.jd_text = ""

# --- Main Router ---
st.title("AI Resume Improver 🤖")
st.sidebar.button("Start New Session", on_click=clear_session, type="primary")

if 'app_state' not in st.session_state:
    st.session_state.jd_text = ""
    clear_session()

if st.session_state.app_state == 'home':
    render_home_page()
elif st.session_state.app_state == 'analysis_done':
    render_analysis_page()
elif st.session_state.app_state == 'chat_mode':
    render_chat_page()