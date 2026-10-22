from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas import CreateBookingRequest, BookingResponse, SimpleMessageResponse
from app.auth import get_current_user, get_optional_user
from app.database import db

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    req: CreateBookingRequest,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    สร้างการจองห้องพักผ่านระบบเว็บ (สามารถจองได้ทั้งแขกทั่วไปและสมาชิกที่ล็อกอิน)
    """
    try:
        booking = db.create_booking(
            room_id=req.room_id,
            guest_name=req.guest_name,
            guest_phone=req.guest_phone,
            check_in_date=req.check_in_date,
            check_out_date=req.check_out_date,
            num_guests=req.num_guests,
            user_id=current_user["id"] if current_user else None,
            booking_channel="web",
            status="confirmed",
            payment_status="pending"
        )
        return booking
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/my", response_model=List[BookingResponse])
def get_my_bookings(current_user: dict = Depends(get_current_user)):
    """
    ดูประวัติการจองทั้งหมดของตนเอง (ต้องล็อกอิน)
    """
    user_id = current_user["id"]
    return db.get_user_bookings(user_id)

@router.get("/track", response_model=BookingResponse)
def track_booking(
    phone: str = Query(..., description="เบอร์โทรศัพท์ที่ใช้ตอนจอง"),
    booking_code: str = Query(..., description="รหัสการจอง เช่น HTL-A8C91")
):
    """
    ตรวจสอบข้อมูลการจองด้วย 'รหัสการจอง' + 'เบอร์โทรศัพท์' โดยไม่ต้องล็อกอิน
    """
    booking = db.get_booking_by_code_and_phone(booking_code, phone)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบข้อมูลการจองที่ตรงกับรหัสการจองและเบอร์โทรศัพท์นี้"
        )
    return booking

@router.patch("/{booking_id}/cancel", response_model=SimpleMessageResponse)
def cancel_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    ลูกค้ายกเลิกการจองของตนเอง หรือ Admin ยกเลิกการจอง
    """
    booking = db.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบข้อมูลการจอง")

    # Check permission: must be owner or admin
    is_owner = booking.get("user_id") == current_user["id"]
    is_admin = current_user.get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ท่านไม่มีสิทธิ์ยกเลิกการจองนี้"
        )

    if booking["status"] in ("checked_in", "checked_out"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ไม่สามารถยกเลิกการจองที่อยู่ในสถานะ {booking['status']} ได้"
        )

    updated = db.update_booking_status(booking_id, "cancelled")
    return {
        "success": True,
        "message": f"ยกเลิกการจอง {booking.get('booking_code')} เรียบร้อยแล้ว",
        "data": {"booking_id": booking_id, "status": "cancelled"}
    }
