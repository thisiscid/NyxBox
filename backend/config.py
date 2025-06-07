from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") 
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
    JWT_SECRET = os.getenv("JWT_SECRET")
    DATABASE_URL = os.getenv("DATABASE_URL")
    API_BASE_URL = os.getenv("API_BASE_URL")

settings = Settings()