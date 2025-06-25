from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") 
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") 
    GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
    JWT_SECRET = os.getenv("JWT_SECRET")
    DATABASE_URL = os.getenv("DATABASE_URL")
    API_BASE_URL = os.getenv("API_BASE_URL")
    SLACK_CHANNEL_WEBHOOK_URL = os.getenv("SLACK_CHANNEL_WEBHOOK_URL")
    SLACK_DMS_WEBHOOK_URL = os.getenv("SLACK_DMS_WEBHOOK_URL")
    SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")
    SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")


settings = Settings()