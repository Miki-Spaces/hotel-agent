from datetime import date, datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, EmailStr

# ------------------------------------------------------------------------------
# 1. AUTH SCHEMAS
# ------------------------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Minimum 6 characters")
    full_name: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=9)

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Literal["user", "admin"] = "user"
    created_at: Optional[datetime] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    profile: UserProfile

# ------------------------------------------------------------------------------
# 2. ROOM & CATALOG SCHEMAS
# ------------------------------------------------------------------------------
class RoomTypeResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    max_guests: int
    base_price: float
    created_at: Optional[datetime] = None

class RoomAvailabilityItem(BaseModel):
    room_id: str
    room_number: str
    floor: int
    room_type_name: str
    max_guests: int
    price_per_night: float
    total_nights: int
    total_estimated_price: float

class RoomStatusUpdate(BaseModel):
    status: Literal["available", "maintenance"]

class RoomLiveGridItem(BaseModel):
    room_id: str
    room_number: str
    floor: int
    room_type_name: str
    base_price: float
    max_guests: int
    current_status: Literal["available", "occupied", "maintenance"]
    active_booking_id: Optional[str] = None
    booking_code: Optional[str] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    booking_status: Optional[str] = None

# ------------------------------------------------------------------------------
# 3. BOOKING SCHEMAS
# ------------------------------------------------------------------------------
class CreateBookingRequest(BaseModel):
    room_id: str
    guest_name: str
    guest_phone: str
    check_in_date: date
    check_out_date: date
    num_guests: int = Field(default=1, ge=1)

class AdminWalkInRequest(BaseModel):
    room_id: str
    guest_name: str
    guest_phone: str
    check_in_date: date
    check_out_date: date
    num_guests: int = Field(default=1, ge=1)
    payment_status: Literal["pending", "completed"] = "pending"
    payment_method: Optional[str] = "cash"

class AdminPaymentUpdate(BaseModel):
    payment_status: Literal["pending", "completed", "refunded"]
    payment_method: Optional[str] = "cash"

class BookingResponse(BaseModel):
    id: str
    booking_code: str
    user_id: Optional[str] = None
    room_id: str
    room_number: Optional[str] = None
    room_type_name: Optional[str] = None
    guest_name: str
    guest_phone: str
    check_in_date: date
    check_out_date: date
    num_guests: int
    total_price: float
    status: Literal["pending", "confirmed", "cancelled", "checked_in", "checked_out"]
    booking_channel: Literal["voice_bot", "web"]
    payment_status: Literal["pending", "completed", "refunded"]
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ------------------------------------------------------------------------------
# 4. ADMIN DASHBOARD SCHEMAS
# ------------------------------------------------------------------------------
class DashboardSummaryResponse(BaseModel):
    total_rooms: int
    occupied: int
    available: int
    maintenance: int
    occupancy_rate_percent: float
    revenue_today: float
    total_bookings_today: int
    active_bookings_count: int

# ------------------------------------------------------------------------------
# 5. VOICE BOT WEBHOOK SCHEMAS
# ------------------------------------------------------------------------------
class VoiceCheckRoomsRequest(BaseModel):
    check_in: date
    check_out: date
    guests: int = Field(default=2, ge=1)

class VoiceCheckRoomsResponse(BaseModel):
    available: bool
    room_type: Optional[str] = None
    room_id: Optional[str] = None
    price_per_night: Optional[float] = None
    total_nights: Optional[int] = None
    total_price: Optional[float] = None
    available_rooms_count: int = 0
    speech_text: str

class VoiceBookRoomRequest(BaseModel):
    room_id: Optional[str] = None
    room_type_id: Optional[str] = None
    guest_name: str
    guest_phone: str
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1)

class VoiceBookRoomResponse(BaseModel):
    success: bool
    booking_code: Optional[str] = None
    booking_id: Optional[str] = None
    total_price: Optional[float] = None
    speech_text: str
    error: Optional[str] = None

class VoiceSaveLogRequest(BaseModel):
    session_id: str
    caller_phone: Optional[str] = None
    duration_seconds: int = 0
    messages: List[Dict[str, Any]] = []
    intent_data: Dict[str, Any] = {}
    confidence_score: Optional[float] = None
    booking_id: Optional[str] = None

class VoiceSaveLogResponse(BaseModel):
    saved: bool
    log_id: Optional[str] = None
    message: str = "Voice log saved successfully"

# Generic Success/Message Response
class SimpleMessageResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
