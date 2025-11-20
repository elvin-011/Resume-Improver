# Resume Analysis System

A professional resume analysis system with AI-powered feedback using FastAPI backend and Streamlit frontend.

## Features

- Multi-format resume upload (PDF, DOCX, JPG, JPEG, PNG)
- Automated information extraction (name, email, phone, skills, experience, education)
- AI-powered resume analysis using Gemini
- Weakness identification and improvement tips
- Resume scoring system
- JSON database storage
- Clean, professional interface

## Prerequisites

- Python 3.8 or higher
- Tesseract OCR installed on your system
- Gemini API key from Google AI Studio

### Install Tesseract OCR

**Windows:**
```bash
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH: C:\Program Files\Tesseract-OCR
```

**MacOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

## Installation

1. **Clone or create project directory**
```bash
mkdir resume_analysis_system
cd resume_analysis_system
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Gemini API Key**

Edit `main.py` and replace:
```python
os.environ["GEMINI_API_KEY"] = "your-gemini-api-key-here"
```

Get your API key from: https://makersuite.google.com/app/apikey

## Project Structure

```
resume_analysis_system/
├── main.py              # FastAPI backend
├── app.py               # Streamlit frontend
├── requirements.txt     # Dependencies
├── data/                # JSON storage (auto-created)
└── README.md           # This file
```

## Running the Application

### Step 1: Start Backend (Terminal 1)

```bash
python main.py
```

Backend will run on: http://localhost:8000

### Step 2: Start Frontend (Terminal 2)

```bash
streamlit run app.py
```

Frontend will open automatically in your browser at: http://localhost:8501

## Usage

1. Open the Streamlit interface in your browser
2. Upload a resume file (PDF, DOCX, or image)
3. Click "Analyze Resume"
4. View extracted information and AI analysis
5. Download the full analysis as JSON

## API Endpoints

- `POST /api/analyze-resume` - Upload and analyze resume
- `GET /api/health` - Health check
- `GET /api/resumes` - Get all analyzed resumes

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Technology Stack

**Backend:**
- FastAPI - Web framework
- PyPDF2 - PDF text extraction
- python-docx - DOCX processing
- pytesseract - OCR for images
- LiteLLM - AI model integration

**Frontend:**
- Streamlit - UI framework
- Requests - API communication

**AI:**
- Google Gemini Pro - Resume analysis

## Data Storage

Resume data is stored in JSON files in the `data/` directory with timestamps.

Example: `data/resume_20240105_143022.json`

## Future Enhancements

- Database integration (PostgreSQL/MongoDB)
- User authentication
- Multiple AI model support
- Resume template suggestions
- ATS compatibility check
- Skill gap analysis
- Job matching
- Batch processing
- Export to PDF reports

## Troubleshooting

**Backend won't start:**
- Check if port 8000 is available
- Verify all dependencies are installed
- Check Gemini API key is valid

**OCR not working:**
- Ensure Tesseract is installed and in PATH
- Try `tesseract --version` in terminal

**Frontend connection error:**
- Ensure backend is running first
- Check backend URL in app.py

**AI analysis fails:**
- Verify Gemini API key is correct
- Check internet connection
- Review API quota limits

## License

MIT License

## Support

For issues or questions, please create an issue in the project repository.