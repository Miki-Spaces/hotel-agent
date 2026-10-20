from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, status
from app.schemas import (
    VoiceCheckRoomsRequest,
    VoiceCheckRoomsResponse,
    VoiceBookRoomRequest,
    VoiceBookRoomResponse,
    VoiceSaveLogRequest,
    VoiceSaveLogResponse
)
from app.config import settings
from app.database import db

router = APIRouter(prefix="/api/voice", tags=["AI Voice Bot Webhook"])

def verify_voice_api_key(x_api_key: Optional[str] = Header(None)):
    """Optional validation of Voice Bot API Key for secure webhook communication."""
    expected_key = settings.VOICE_BOT_API_KEY
    if expected_key and x_api_key:
        if x_api_key != expected_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Voice Bot API Key")
    return True

@router.post("/check-rooms", response_model=VoiceCheckRoomsResponse)
def voice_check_rooms(req: VoiceCheckRoomsRequest):
    """
    ตรวจสอบห้องว่างและคำนวณราคาให้ AI Voice Bot นำ speech_text ไปพูดกับลูกค้าทันที
    """
    if req.check_out <= req.check_in:
        return {
            "available": False,
            "speech_text": "ขออภัยค่ะ วันเช็คเอาต์ต้องอยู่หลังวันเช็คอิน รบกวนแจ้งวันที่ใหม่อีกครั้งได้ไหมคะ"
        }

    try:
        available_rooms = db.check_room_availability(req.check_in, req.check_out, req.guests)
        if not available_rooms:
            return {
                "available": False,
                "available_rooms_count": 0,
                "speech_text": f"ขออภัยค่ะ ในช่วงวันที่ {req.check_in} ถึง {req.check_out} ห้องพักสำหรับ {req.guests} ท่าน เต็มหมดแล้วค่ะ ต้องการให้ดูวันอื่นเพิ่มเติมไหมคะ"
            }

        # Select best matching/lowest price room
        best = available_rooms[0]
        nights = best["total_nights"]
        price_total = best["total_estimated_price"]
        room_name = best["room_type_name"]

        speech = (
            f"มีห้อง {room_name} ว่างค่ะ พักได้ {best['max_guests']} ท่าน "
            f"รวม {nights} คืน ยอดสุทธิ {price_total:,.0f} บาท ต้องการให้จองเลยไหมคะ"
        )

        return {
            "available": True,
            "room_type": room_name,
            "room_id": best["room_id"],
            "price_per_night": best["price_per_night"],
            "total_nights": nights,
            "total_price": price_total,
            "available_rooms_count": len(available_rooms),
            "speech_text": speech
        }
    except Exception as e:
        return {
            "available": False,
            "speech_text": "ขออภัยค่ะ ระบบตรวจสอบห้องพักขัดข้องชั่วคราว รบกวนลองใหม่อีกครั้งค่ะ"
        }

@router.post("/book-room", response_model=VoiceBookRoomResponse)
def voice_book_room(req: VoiceBookRoomRequest):
    """
    ยืนยันการจองผ่าน AI Voice Bot และออกรหัสการจอง (HTL-XXXX)
    """
    target_room_id = req.room_id

    # If specific room_id not provided, find first available room matching room_type_id or any room
    if not target_room_id:
        available = db.check_room_availability(req.check_in, req.check_out, req.guests)
        if req.room_type_id:
            matched = [r for r in available if r.get("room_type_id") == req.room_type_id or r.get("room_type_name") == req.room_type_id]
            if matched:
                target_room_id = matched[0]["room_id"]
        if not target_room_id and available:
            target_room_id = available[0]["room_id"]

    if not target_room_id:
        return {
            "success": False,
            "speech_text": "ขออภัยค่ะ ห้องพักเต็มแล้ว ไม่สามารถทำรายการจองได้ในขณะนี้ค่ะ",
            "error": "No available room"
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
