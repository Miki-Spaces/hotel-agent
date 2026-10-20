from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, rooms, bookings, admin, voice
from app.config import settings
from app.database import db

app = FastAPI(
    title="Hotel AI Voice Booking API",
    description="""
# 🏨 Hotel AI Voice Booking System API Backend

API Backend สำหรับระบบจองโรงแรมและ AI Voice Bot (Botnoi Integration) ด้วย **FastAPI** และ **Supabase PostgreSQL**.

### ฟีเจอร์หลักในระบบ:
- **Authentication & RBAC**: สมัครสมาชิก ล็อกอิน ดูโปรไฟล์ และแยกสิทธิ์ User/Admin
- **Room Inventory**: ระบบจัดการผังห้องพัก 10 ห้อง 4 ชั้น (View `v_room_live_status`)
- **Real-time Availability**: คำนวณห้องว่างและราคาตามจำนวนคืนอัตโนมัติ
- **Booking Management**: จองห้องผ่านเว็บ, จอง Walk-in, เช็คอิน, เช็คเอาต์, อัปเดตชำระเงิน
- **Botnoi Voice Bot Webhooks**: Endpoint ให้ Voice Bot เช็คห้องว่าง ตอบเสียงพูดภาษาไทยธรรมชาติ และบันทึก Call Logs

### เอกสารและเครื่องมือทดสอบ:
- **Interactive Swagger UI**: [/docs](/docs)
- **ReDoc UI**: [/redoc](/redoc)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Allow browser requests only from configured frontend origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include All Routers
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(admin.router)
app.include_router(voice.router)

@app.get("/", tags=["Health & Status"])
def root():
    """
    API Healthcheck and status information
    """
    return {
        "status": "online",
        "service": "Hotel AI Voice Booking API",
        "version": "1.0.0",
        "database_backend": "Supabase PostgreSQL" if db.is_supabase_connected else "Local In-Memory (Dev/Fallback)",
        "docs_url": "/docs",
        "endpoints": {
            "auth": "/api/auth/*",
            "rooms": "/api/rooms/*",
            "bookings": "/api/bookings/*",
            "admin": "/api/admin/*",
            "voice_bot": "/api/voice/*"
        }
    }
