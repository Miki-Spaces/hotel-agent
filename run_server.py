import sys
import uvicorn
from app.config import settings

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    print(f">> Starting Hotel AI Voice Booking API on http://{settings.HOST}:{settings.PORT}")
    print(f">> Swagger Interactive API Docs: http://127.0.0.1:{settings.PORT}/docs")
    print(f">> ReDoc Documentation: http://127.0.0.1:{settings.PORT}/redoc")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
