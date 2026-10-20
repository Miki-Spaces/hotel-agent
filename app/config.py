import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-key-hotel-voice-2026")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    VOICE_BOT_API_KEY: str = os.getenv("VOICE_BOT_API_KEY", "botnoi-hotel-agent-secret-key-2026")
    BOTNOI_ACCESS_TOKEN: str = os.getenv("BOTNOI_ACCESS_TOKEN", "").strip()
    BOTNOI_AGENT_ID: str = os.getenv("BOTNOI_AGENT_ID", "").strip()
    FRONTEND_ALLOWED_ORIGINS: list[str] = [
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "FRONTEND_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]

    @property
    def has_supabase_config(self) -> bool:
        """Check if real Supabase credentials are configured."""
        url = self.SUPABASE_URL.strip()
        key = (self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_ANON_KEY).strip()
        return bool(url and key and "your-project" not in url)

settings = Settings()
