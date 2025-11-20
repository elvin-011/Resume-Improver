import streamlit as st
import requests
import json
from datetime import datetime
import time
import subprocess
import sys
import os
import signal
import atexit
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Resume Analysis System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoint
API_BASE_URL = "http://localhost:8000"

# Global variable to track backend process
if 'backend_process' not in st.session_state:
    st.session_state.backend_process = None
if 'backend_started' not in st.session_state:
    st.session_state.backend_started = False

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def cleanup_backend():
    """Cleanup backend process on exit"""
    if st.session_state.backend_process:
        try:
            st.session_state.backend_process.terminate()
            st.session_state.backend_process.wait(timeout=5)
        except:
            try:
                st.session_state.backend_process.kill()
            except:
                pass

atexit.register(cleanup_backend)

def check_backend_connection():
    """Check if backend is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_backend():
    """Start the FastAPI backend server"""
    try:
        # Check if main.py exists
        if not os.path.exists("main.py"):
            return False, "main.py not found in current directory"
        
        # Start backend process
        if sys.platform == "win32":
            # Windows
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # Unix/Linux/Mac
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
        
        st.session_state.backend_process = process
        
        # Wait for backend to start (max 10 seconds)
        for i in range(20):
            time.sleep(0.5)
            if check_backend_connection():
                st.session_state.backend_started = True
                return True, "Backend started successfully"
        
        return False, "Backend started but not responding"
        
    except Exception as e:
        return False, f"Failed to start backend: {str(e)}"

def stop_backend():
    """Stop the backend server"""
    cleanup_backend()
    st.session_state.backend_process = None
    st.session_state.backend_started = False

def upload_and_analyze(uploaded_file):
    """Upload file to backend and get analysis"""
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        response = requests.post(
            f"{API_BASE_URL}/api/analyze-resume", 
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_msg = f"Error {response.status_code}: {response.text}"
            return None, error_msg
    except requests.exceptions.ConnectionError:
        return None, "Backend connection lost. Please restart the application."
    except requests.exceptions.Timeout:
        return None, "Request timed out. The file might be too large or complex."
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def display_resume_data(data):
    """Display extracted resume information"""
    st.subheader("Extracted Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Personal Details")
        if data.get('name'):
            st.markdown(f"**Name:** {data['name']}")
        else:
            st.markdown("**Name:** Not detected")
            
        if data.get('email'):
            st.markdown(f"**Email:** {data['email']}")
        else:
            st.markdown("**Email:** Not detected")
            
        if data.get('phone'):
            st.markdown(f"**Phone:** {data['phone']}")
        else:
            st.markdown("**Phone:** Not detected")
    
    with col2:
        st.markdown("#### Skills Detected")
        if data.get('skills'):
            skills_text = ", ".join(data['skills'])
            st.markdown(f"{skills_text}")
        else:
            st.markdown("No skills automatically detected")
    
    if data.get('experience'):
        st.markdown("#### Experience Highlights")
        for idx, exp in enumerate(data['experience'][:3], 1):
            if exp.strip():
                st.markdown(f"{idx}. {exp[:150]}")
    
    if data.get('education'):
        st.markdown("#### Education")
        for idx, edu in enumerate(data['education'][:3], 1):
            if edu.strip():
                st.markdown(f"{idx}. {edu[:150]}")

def display_ai_analysis(analysis):
    """Display AI analysis results"""
    st.subheader("AI-Powered Analysis")
    
    score = analysis.get('score', 0)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.metric(label="Resume Quality Score", value=f"{score}/10")
    
    st.markdown("---")
    
    if analysis.get('summary'):
        st.markdown("#### Executive Summary")
        st.info(analysis['summary'])
        st.markdown("")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Key Weaknesses")
        weaknesses = analysis.get('weaknesses', [])
        if weaknesses:
            for i, weakness in enumerate(weaknesses, 1):
                st.markdown(f"**{i}.** {weakness}")
        else:
            st.markdown("No specific weaknesses identified")
    
    with col2:
        st.markdown("#### Improvement Tips")
        tips = analysis.get('tips', [])
        if tips:
            for i, tip in enumerate(tips, 1):
                st.markdown(f"**{i}.** {tip}")
        else:
            st.markdown("No improvement tips available")
    
    if analysis.get('raw_response'):
        with st.expander("View Full AI Response"):
            st.text(analysis['raw_response'])

def main():
    st.title("Resume Analysis System")
    st.markdown("Upload your resume for AI-powered analysis and professional improvement suggestions")
    
    # Sidebar
    with st.sidebar:
        st.header("System Control")
        
        # Check backend status
        backend_online = check_backend_connection()
        
        if backend_online:
            st.success("Backend Status: Online")
            if st.button("Stop Backend", use_container_width=True):
                stop_backend()
                st.rerun()
        else:
            st.error("Backend Status: Offline")
            if st.button("Start Backend", type="primary", use_container_width=True):
                with st.spinner("Starting backend server..."):
                    success, message = start_backend()
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
        
        st.markdown("---")
        
        st.markdown("#### Supported Formats")
        st.markdown("- PDF documents")
        st.markdown("- DOCX documents")
        st.markdown("- JPG/JPEG images")
        st.markdown("- PNG images")
        
        st.markdown("---")
        
        st.markdown("#### Features")
        st.markdown("- Automated data extraction")
        st.markdown("- AI weakness detection")
        st.markdown("- Improvement recommendations")
        st.markdown("- Resume quality scoring")
        
        st.markdown("---")
        
        st.markdown("#### About")
        st.markdown("Version 1.0.0")
        st.markdown("Powered by FastAPI + Streamlit")
    
    # Auto-start backend on first run
    if not st.session_state.backend_started and not check_backend_connection():
        with st.spinner("Initializing backend server..."):
            success, message = start_backend()
            if success:
                st.success("Backend initialized successfully")
                time.sleep(1)
                st.rerun()
            else:
                st.warning(f"Could not auto-start backend: {message}")
                st.info("Please click 'Start Backend' in the sidebar")
    
    st.markdown("---")
    
    # Main content tabs
    tab1, tab2 = st.tabs(["Upload & Analyze", "Analysis History"])
    
    with tab1:
        if not check_backend_connection():
            st.error("Backend server is not running.")
            st.info("Click 'Start Backend' in the sidebar to begin")
            st.stop()
        
        st.subheader("Upload Resume")
        
        uploaded_file = st.file_uploader(
            "Choose a resume file",
            type=['pdf', 'docx', 'jpg', 'jpeg', 'png'],
            help="Upload your resume in PDF, DOCX, or image format (max 10MB)"
        )
        
        if uploaded_file is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric("File Name", uploaded_file.name)
            col2.metric("File Type", uploaded_file.type.split('/')[-1].upper())
            col3.metric("File Size", f"{uploaded_file.size / 1024:.2f} KB")
            
            st.markdown("---")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                analyze_button = st.button("Analyze Resume", type="primary", use_container_width=True)
            
            if analyze_button:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Uploading file...")
                progress_bar.progress(20)
                time.sleep(0.3)
                
                status_text.text("Extracting text...")
                progress_bar.progress(40)
                time.sleep(0.3)
                
                status_text.text("Analyzing with AI...")
                progress_bar.progress(60)
                
                result, error = upload_and_analyze(uploaded_file)
                
                progress_bar.progress(100)
                status_text.text("Analysis complete")
                time.sleep(0.5)
                
                progress_bar.empty()
                status_text.empty()
                
                if error:
                    st.error(error)
                elif result:
                    st.success("Resume analyzed successfully")
                    st.markdown("---")
                    
                    resume_data = result.get('resume_data', {})
                    ai_analysis = result.get('ai_analysis', {})
                    
                    display_resume_data(resume_data)
                    st.markdown("---")
                    display_ai_analysis(ai_analysis)
                    st.markdown("---")
                    
                    st.subheader("Export Results")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        json_str = json.dumps(result, indent=2)
                        st.download_button(
                            label="Download Full Analysis (JSON)",
                            data=json_str,
                            file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                    with col2:
                        summary_text = f"""RESUME ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
File: {uploaded_file.name}

SCORE: {ai_analysis.get('score', 'N/A')}/10

SUMMARY:
{ai_analysis.get('summary', 'N/A')}

KEY WEAKNESSES:
"""
                        for i, w in enumerate(ai_analysis.get('weaknesses', []), 1):
                            summary_text += f"{i}. {w}\n"
                        
                        summary_text += "\nIMPROVEMENT TIPS:\n"
                        for i, t in enumerate(ai_analysis.get('tips', []), 1):
                            summary_text += f"{i}. {t}\n"
                        
                        st.download_button(
                            label="Download Summary (TXT)",
                            data=summary_text,
                            file_name=f"resume_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                else:
                    st.error("Analysis failed. Please try again.")
        else:
            st.info("Please upload a resume file to begin analysis")
    
    with tab2:
        st.subheader("Analysis History")
        
        if not check_backend_connection():
            st.warning("Backend offline. Cannot retrieve history.")
            st.stop()
        
        try:
            response = requests.get(f"{API_BASE_URL}/api/resumes", timeout=5)
            if response.status_code == 200:
                data = response.json()
                resumes = data.get('resumes', [])
                
                if resumes:
                    st.success(f"Total resumes analyzed: {len(resumes)}")
                    st.markdown("---")
                    
                    for idx, resume in enumerate(reversed(resumes), 1):
                        with st.expander(
                            f"Analysis {idx}: {resume.get('file_name', 'Unknown')} - "
                            f"{resume.get('processed_at', 'Unknown date')}"
                        ):
                            score = resume.get('ai_analysis', {}).get('score', 'N/A')
                            st.metric("Score", f"{score}/10")
                            
                            summary = resume.get('ai_analysis', {}).get('summary', '')
                            if summary:
                                st.markdown(f"**Summary:** {summary}")
                            
                            st.json(resume)
                else:
                    st.info("No resumes analyzed yet. Upload a resume to get started.")
            else:
                st.error("Unable to fetch analysis history")
        except Exception as e:
            st.error(f"Error fetching history: {str(e)}")

if __name__ == "__main__":
    main()