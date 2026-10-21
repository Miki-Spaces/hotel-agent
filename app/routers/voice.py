from datetime import date
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, HTTPException, Header, Request, status
from app.schemas import (
    VoiceCheckRoomsRequest,
    VoiceCheckRoomsResponse,
    VoiceBookRoomRequest,
    VoiceBookRoomResponse,
    VoiceSaveLogRequest,
    VoiceSaveLogResponse,
    VoiceCallTokenResponse
)
from app.config import settings
from app.database import db

router = APIRouter(prefix="/api/voice", tags=["AI Voice Bot Webhook"])

_CALL_TOKEN_WINDOW_SECONDS = 60
_CALL_TOKEN_LIMIT = 5
_call_token_requests: dict[str, deque[float]] = defaultdict(deque)
_call_token_lock = Lock()

def verify_voice_api_key(x_api_key: Optional[str] = Header(None)):
    """Optional validation of Voice Bot API Key for secure webhook communication."""
    expected_key = settings.VOICE_BOT_API_KEY
    if expected_key and x_api_key:
        if x_api_key != expected_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Voice Bot API Key")
    return True

@router.post("/call-token", response_model=VoiceCallTokenResponse)
async def create_call_token(request: Request):
    """Issue one short-lived browser token without exposing the Botnoi access token."""
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin or origin not in settings.FRONTEND_ALLOWED_ORIGINS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This website is not allowed to start voice calls.",
        )

    if not settings.BOTNOI_ACCESS_TOKEN or not settings.BOTNOI_AGENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice bot is not configured on the server.",
        )

    client_ip = request.client.host if request.client else "unknown"
    now = monotonic()
    with _call_token_lock:
        requests = _call_token_requests[client_ip]
        while requests and now - requests[0] >= _CALL_TOKEN_WINDOW_SECONDS:
            requests.popleft()
        if len(requests) >= _CALL_TOKEN_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many voice call attempts. Please wait and try again.",
                headers={"Retry-After": str(_CALL_TOKEN_WINDOW_SECONDS)},
            )
        requests.append(now)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://backend-voicebot-stg.botnoigroup.com/call/tokens",
                headers={
                    "Authorization": f"Bearer {settings.BOTNOI_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={"agent_id": settings.BOTNOI_AGENT_ID, "channel": "web"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the voice service. Please try again.",
        ) from exc

    if response.is_error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The voice service could not issue a call token.",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The voice service returned an invalid response.",
        ) from exc

    ephemeral_token = payload.get("ephemeral_token") if isinstance(payload, dict) else None
    if not isinstance(ephemeral_token, str) or not ephemeral_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The voice service returned no call token.",
        )

    return {"ephemeral_token": ephemeral_token}

@router.post("/check-rooms", response_model=VoiceCheckRoomsResponse)
def voice_check_rooms(req: VoiceCheckRoomsRequest):
    """
    ตรวจสอบห้องว่างและคำนวณราคาให้ AI Voice Bot นำ speech_text ไปพูดกับลูกค้าทันที
    """
    if req.check_out <= req.check_in:
        return {
            "available": False,
            "rooms": [],
            "available_rooms_count": 0,
            "speech_text": "ขออภัยค่ะ วันเช็คเอาต์ต้องอยู่หลังวันเช็คอิน รบกวนแจ้งวันที่ใหม่อีกครั้งได้ไหมคะ"
        }

    try:
        available_rooms = db.check_room_availability(req.check_in, req.check_out, req.guests)
        if not available_rooms:
            return {
                "available": False,
                "rooms": [],
                "available_rooms_count": 0,
                "speech_text": f"ขออภัยค่ะ ในช่วงวันที่ {req.check_in} ถึง {req.check_out} ห้องพักสำหรับ {req.guests} ท่าน เต็มหมดแล้วค่ะ ต้องการให้ดูวันอื่นเพิ่มเติมไหมคะ"
            }

        room_types_by_name: Dict[str, List[Dict[str, Any]]] = {}
        for room_type in db.get_room_types():
            room_types_by_name.setdefault(room_type["name"], []).append(room_type)

        options_by_type: Dict[str, Dict[str, Any]] = {}
        for room in available_rooms:
            room_type_name = room["room_type_name"]
            room_type_id = room.get("room_type_id")
            if not room_type_id:
                matching_types = room_types_by_name.get(room_type_name, [])
                if len(matching_types) == 1:
                    room_type_id = matching_types[0]["id"]

            if not room_type_id:
                raise ValueError(f"Missing room_type_id for {room_type_name}")

            option = options_by_type.setdefault(room_type_id, {
                "room_type_id": room_type_id,
                "room_type": room_type_name,
                "max_guests": room["max_guests"],
                "price_per_night": room["price_per_night"],
                "total_nights": room["total_nights"],
                "total_price": room["total_estimated_price"],
                "available_rooms_count": 0,
            })
            option["available_rooms_count"] += 1

        room_options = list(options_by_type.values())
        speech_options = [
            (
                f"{index}. {option['room_type']} พักได้ไม่เกิน {option['max_guests']} ท่าน "
                f"คืนละ {option['price_per_night']:,.0f} บาท รวม {option['total_nights']} คืน "
                f"เป็นเงิน {option['total_price']:,.0f} บาท"
            )
            for index, option in enumerate(room_options, start=1)
        ]
        speech = "มีห้องว่างให้เลือกค่ะ " + " ".join(speech_options) + " ต้องการเลือกห้องประเภทไหนคะ"

        return {
            "available": True,
            "rooms": room_options,
            "available_rooms_count": len(available_rooms),
            "speech_text": speech
        }
    except Exception as e:
        return {
            "available": False,
            "rooms": [],
            "available_rooms_count": 0,
            "speech_text": "ขออภัยค่ะ ระบบตรวจสอบห้องพักขัดข้องชั่วคราว รบกวนลองใหม่อีกครั้งค่ะ"
        }

@router.post("/book-room", response_model=VoiceBookRoomResponse)
def voice_book_room(req: VoiceBookRoomRequest):
    """
    ยืนยันการจองผ่าน AI Voice Bot และออกรหัสการจอง (HTL-XXXX)
    """
    target_room_id = req.room_id

    # Resolve the selected room type to a physical room only after checking current availability.
    if not target_room_id:
        available = db.check_room_availability(req.check_in, req.check_out, req.guests)
        if req.room_type_id:
            matched = [r for r in available if r.get("room_type_id") == req.room_type_id or r.get("room_type_name") == req.room_type_id]
            if matched:
                target_room_id = matched[0]["room_id"]
        else:
            return {
                "success": False,
                "speech_text": "กรุณาเลือกประเภทห้องก่อนยืนยันการจองค่ะ",
                "error": "room_type_id is required when room_id is not provided"
            }

    if not target_room_id:
        return {
            "success": False,
            "speech_text": "ขออภัยค่ะ ประเภทห้องที่เลือกไม่มีห้องว่างแล้ว รบกวนตรวจสอบห้องว่างอีกครั้งค่ะ",
            "error": "No available room for selected room type"
        }

    try:
        booking = db.create_booking(
            room_id=target_room_id,
            guest_name=req.guest_name,
            guest_phone=req.guest_phone,
            check_in_date=req.check_in,
            check_out_date=req.check_out,
            num_guests=req.guests,
            booking_channel="voice_bot",
            status="confirmed",
            payment_status="pending"
        )

        code = booking["booking_code"]
        total = booking["total_price"]
        speech = (
            f"จองห้องพักสำเร็จเรียบร้อยค่ะคุณ {req.guest_name}! "
            f"รหัสการจองคือ {code} ยอดชำระทั้งหมด {total:,.0f} บาท "
            f"สามารถชำระเงินที่หน้าเคาน์เตอร์ตอนเช็คอินได้เลยค่ะ ขอบคุณค่ะ"
        )

        return {
            "success": True,
            "booking_code": code,
            "booking_id": booking["id"],
            "total_price": total,
            "speech_text": speech
        }
    except Exception as e:
        return {
            "success": False,
            "speech_text": f"ขออภัยค่ะ เกิดข้อผิดพลาดในการบันทึกการจอง: {str(e)}",
            "error": str(e)
        }

@router.post("/save-log", response_model=VoiceSaveLogResponse)
def voice_save_log(req: VoiceSaveLogRequest):
    """
    บันทึกประวัติการโทร ทรานสคริปต์ และ Intent สกัดจาก Botnoi Voice Bot ลงตาราง call_logs
    """
    log = db.save_call_log(
        session_id=req.session_id,
        caller_phone=req.caller_phone,
        duration_seconds=req.duration_seconds,
        messages=req.messages,
        intent_data=req.intent_data,
        confidence_score=req.confidence_score,
        booking_id=req.booking_id
    )
    return {
        "saved": True,
        "log_id": log["id"],
        "message": "Call log saved successfully"
    }
