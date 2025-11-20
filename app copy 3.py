# frontend_app.py

import streamlit as st
import requests
import io

# Import the audio recorder component
from st_audiorec import st_audiorec

# Define the backend API address
BACKEND_URL = "http://127.0.0.1:8000"

TEMPLATE_OPTIONS = {
    "classic": "Classic (Single-Column)",
    "modern": "Modern (With Competencies)",
    "skills_first": "Skills-First (Functional)",
}

# --- Helper Function for Transcription ---
def transcribe_audio_bytes(audio_bytes):
    """
    Sends audio bytes to the backend for transcription.
    """
    try:
        audio_file = io.BytesIO(audio_bytes)
        files = {'file': ('audio.wav', audio_file, 'audio/wav')}
        response = requests.post(f"{BACKEND_URL}/transcribe", files=files)
        
        if response.status_code == 200:
            return response.json().get("text")
        else:
            st.error(f"Error transcribing audio: {response.json().get('detail')}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Is the backend server running?")
        return None
    except Exception as e:
        st.error(f"An error occurred during transcription: {e}")
        return None

# --- 1. Page Rendering Functions ---

# [NEW] Welcome Page
def render_welcome_page():
    st.title("AI Resume Improver 🤖")
    st.write("Welcome! Would you like to improve an existing resume or build a new one from scratch?")
    
    st.header("Step 1: Add Job Description (Optional, but recommended)")
    st.write("To align your resume with a specific job, paste the description below.")
    
    jd_text = st.text_area(
        "Paste Job Description Here:",
        value=st.session_state.jd_text, # Set default from state
        height=150
    )
    # Save JD to state immediately
    st.session_state.jd_text = jd_text if jd_text else "No job description provided."

    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Improve My Existing Resume", use_container_width=True, type="primary"):
            st.session_state.app_state = 'upload_mode'
            st.rerun()
            
    with col2:
        if st.button("Build a New Resume (with Voice)", use_container_width=True):
            # Call the backend to get the *first* interview question
            with st.spinner("Starting your interview..."):
                try:
                    payload = {"jd_text": st.session_state.jd_text, "messages": []} # Send empty messages list
                    response = requests.post(f"{BACKEND_URL}/start-build-chat", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        # Initialize the *build* chat history
                        st.session_state.build_messages = [
                            {"role": "assistant", "content": data.get("first_ai_message")}
                        ]
                        st.session_state.app_state = 'build_chat'
                        st.rerun()
                    else:
                        st.error(f"Error starting build chat: {response.json().get('detail')}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# [MODIFIED] Renamed from render_home_page to render_upload_page
def render_upload_page():
    st.header("Improve Your Resume")
    st.write("Upload your resume (PDF, TXT, JPG, PNG) to get started.")
    
    uploaded_file = st.file_uploader(
        "Upload Resume",
        type=['pdf', 'txt', 'jpg', 'jpeg', 'png'],
        label_visibility="collapsed"
    )
    
    if st.button("Analyze Resume", key="analyze_btn", type="primary"):
        if uploaded_file is not None:
            with st.spinner(f"Uploading and processing {uploaded_file.name}..."):
                
                files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                # We already have jd_text in session_state from the welcome page
                data = {'jd_text': st.session_state.jd_text}
                
                try:
                    response = requests.post(f"{BACKEND_URL}/analyze", files=files, data=data)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.resume_text = data.get("resume_text")
                        st.session_state.analysis_results = data.get("analysis_results")
                        st.session_state.ats_score = data.get("ats_score", 0)
                        st.session_state.total_weaknesses = data.get("total_weaknesses", 1)
                        st.session_state.weaknesses_covered = 0
                        st.session_state.final_pdf_bytes = None
                        st.session_state.app_state = 'analysis_done'
                        st.rerun()
                    else:
                        st.error(f"Error from backend: {response.json().get('detail')}")
                
                except requests.exceptions.ConnectionError:
                    st.error("Connection Error: Is the backend server running?")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.error("Please upload a resume file to continue.")

# (Unchanged)
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
                    # This is the "IMPROVEMENT" chat
                    st.session_state.messages = [
                        {"role": "assistant", "content": data.get("first_ai_message")}
                    ]
                    st.rerun()
                else:
                    st.error(f"Error from backend: {response.json().get('detail')}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# (This is the IMPROVEMENT chat)
def render_chat_page():
    st.header("Step 3: AI Improvement Chat")
    
    progress_percent = (st.session_state.weaknesses_covered / st.session_state.total_weaknesses)
    progress_text = f"Improvements: {st.session_state.weaknesses_covered} of {st.session_state.total_weaknesses} covered"
    st.progress(progress_percent, text=progress_text)
    
    st.write("Follow my lead! I'll guide you to fix your resume's weak points.")

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    is_complete = (st.session_state.weaknesses_covered == st.session_state.total_weaknesses)
    
    # --- Helper function to send chat message ---
    def send_chat_message(prompt_text):
        if not prompt_text or not prompt_text.strip():
            return # Don't send empty messages
            
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

    # --- PDF Generation (if complete) ---
    if is_complete:
        st.success("Great job! We've covered all the main improvements.")
        # ... (rest of PDF logic is unchanged) ...
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


    # --- Chat Input (if not complete) ---
    if not is_complete:
        
        # --- [MODIFIED] ---
        # Add the audio recorder with NO arguments
        st.write("Speak your response:")
        audio_bytes = st_audiorec()
        # ------------------
        
        if audio_bytes:
            with st.spinner("Transcribing your voice..."):
                transcribed_text = transcribe_audio_bytes(audio_bytes)
            
            if transcribed_text:
                send_chat_message(transcribed_text)
        
        # Text input
        if prompt := st.chat_input("Or, type your response..."):
            send_chat_message(prompt)

# --- [NEW] Page 3: Build Resume Chat ---
def render_build_page():
    st.header("Build Your Resume (Voice Interview)")
    st.write("Follow the AI's prompts to build your resume step-by-step. Use the voice recorder for the best experience.")

    # We use "build_messages" as our state key here
    if 'build_messages' not in st.session_state:
        st.session_state.build_messages = []

    for msg in st.session_state.build_messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # --- Helper function to send build chat message ---
    def send_build_message(prompt_text):
        if not prompt_text or not prompt_text.strip():
            return
            
        st.session_state.build_messages.append({"role": "user", "content": prompt_text})
        st.chat_message("user").write(prompt_text)
        
        payload = {
            "messages": st.session_state.build_messages,
            "jd_text": st.session_state.jd_text
        }
        
        with st.spinner("Thinking..."):
            try:
                response = requests.post(f"{BACKEND_URL}/build-chat", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.build_messages.append({"role": "assistant", "content": data.get("ai_response")})
                    
                    # Check for the completion flag
                    if data.get("build_complete"):
                        st.session_state.build_is_complete = True
                    
                    st.rerun()
                else:
                    st.error(f"Error from backend: {response.json().get('detail')}")
            except Exception as e:
                st.error(f"An error occurred: {e}")
    
    # --- Input section ---
    if not st.session_state.get("build_is_complete", False):
        st.write("Speak your response:")
        # --- [MODIFIED] ---
        # Add the audio recorder with NO arguments
        audio_bytes = st_audiorec()
        # ------------------
        
        if audio_bytes:
            with st.spinner("Transcribing your voice..."):
                transcribed_text = transcribe_audio_bytes(audio_bytes)
            if transcribed_text:
                send_build_message(transcribed_text)
        
        if prompt := st.chat_input("Or, type your response..."):
            send_build_message(prompt)
    else:
        # --- Synthesize Button ---
        st.success("Great! I have all the information I need.")
        if st.button("Finish & Analyze My New Resume", type="primary"):
            with st.spinner("Building your new resume and analyzing it..."):
                try:
                    payload = {
                        "messages": st.session_state.build_messages,
                        "jd_text": st.session_state.jd_text
                    }
                    response = requests.post(f"{BACKEND_URL}/synthesize-and-analyze", json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # We now have a resume! Save all the data just like
                        # the /analyze endpoint does.
                        st.session_state.resume_text = data.get("resume_text")
                        st.session_state.analysis_results = data.get("analysis_results")
                        st.session_state.ats_score = data.get("ats_score", 0)
                        st.session_state.total_weaknesses = data.get("total_weaknesses", 1)
                        st.session_state.weaknesses_covered = 0
                        st.session_state.final_pdf_bytes = None
                        
                        # Send the user to the analysis page!
                        st.session_state.app_state = 'analysis_done'
                        st.rerun()
                    else:
                        st.error(f"Error from backend: {response.json().get('detail')}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")


def clear_session():
    """Resets the frontend's state."""
    # We must preserve jd_text if it was entered on the welcome screen
    # We'll clear it *only* if we are already on the welcome screen
    current_app_state = st.session_state.get('app_state', 'welcome')
    
    # Preserve JD text if we are NOT on the welcome page
    jd_to_keep = st.session_state.get("jd_text", "")
    if current_app_state == 'welcome':
        jd_to_keep = "" # Clear it if we are on the welcome page
        
    # Clear all session state keys
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Re-initialize the app state
    st.session_state.app_state = 'welcome' # Default to welcome
    st.session_state.jd_text = jd_to_keep # Restore the JD
    st.session_state.messages = []
    st.session_state.build_messages = []


# --- 2. Main App Logic (The "Router") ---
# (Title is now in the welcome page)
st.sidebar.button("Start New Session", on_click=clear_session, type="primary")

if 'app_state' not in st.session_state:
    # Initialize jd_text on first load
    st.session_state.jd_text = ""
    clear_session()

# This is our new app "router"
if st.session_state.app_state == 'welcome':
    render_welcome_page()
elif st.session_state.app_state == 'upload_mode':
    render_upload_page()
elif st.session_state.app_state == 'build_chat':
    render_build_page()
elif st.session_state.app_state == 'analysis_done':
    render_analysis_page()
elif st.session_state.app_state == 'chat_mode':
    render_chat_page()