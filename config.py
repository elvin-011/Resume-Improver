import os
from typing import Optional

class Settings:
    """Application configuration settings"""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # AI Model Configuration
    DEFAULT_AI_MODEL: str = "gemini/gemini-2.5-flash"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2000
    
    # Gemini API Key
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "AIzaSyCts2PFc5huq2hC8-lxY-aFQpigQtWOCUU")
    
    # File Processing
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list = ['.pdf', '.docx', '.jpg', '.jpeg', '.png']
    
    # Data Storage
    DATA_DIR: str = "data"
    
    # Resume Parsing
    MIN_TEXT_LENGTH: int = 50
    SKILLS_KEYWORDS: list = [
        'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
        'node.js', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
        'machine learning', 'deep learning', 'data science', 'ai',
        'data analysis', 'statistics', 'excel', 'tableau', 'power bi',
        'project management', 'agile', 'scrum', 'jira',
        'communication', 'leadership', 'teamwork', 'problem solving',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes',
        'git', 'ci/cd', 'devops', 'testing', 'selenium'
    ]
    
    # AI Prompts
    RESUME_ANALYSIS_PROMPT_TEMPLATE: str = """You are a professional resume analyst with expertise in recruitment and career development. Analyze the following resume comprehensively.

Resume Text:
{resume_text}

Provide a detailed analysis in the following JSON format:
{{
    "score": <number between 1-10>,
    "summary": "<brief 2-3 sentence summary of the candidate's profile>",
    "weaknesses": [
        "<specific weakness 1>",
        "<specific weakness 2>",
        "<specific weakness 3>",
        "<specific weakness 4>",
        "<specific weakness 5>"
    ],
    "tips": [
        "<actionable improvement tip 1>",
        "<actionable improvement tip 2>",
        "<actionable improvement tip 3>",
        "<actionable improvement tip 4>",
        "<actionable improvement tip 5>"
    ]
}}

Focus on:
- Content quality and relevance
- Structure and formatting
- Achievement quantification
- Keyword optimization for ATS
- Professional presentation
- Skill-experience alignment"""

    @classmethod
    def get_ai_model_config(cls) -> dict:
        """Get AI model configuration"""
        return {
            "model": cls.DEFAULT_AI_MODEL,
            "temperature": cls.AI_TEMPERATURE,
            "max_tokens": cls.AI_MAX_TOKENS
        }
    
    @classmethod
    def validate_settings(cls) -> bool:
        """Validate critical settings"""
        if cls.GEMINI_API_KEY == "your-gemini-api-key-here":
            print("WARNING: Gemini API key not configured")
            return False
        
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        return True

settings = Settings()