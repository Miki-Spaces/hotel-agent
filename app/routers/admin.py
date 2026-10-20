from datetime import date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas import (
    DashboardSummaryResponse,
    RoomLiveGridItem,
    RoomStatusUpdate,
    BookingResponse,
    AdminWalkInRequest,
    AdminPaymentUpdate,
    SimpleMessageResponse
)
from app.auth import get_current_admin
from app.database import db

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"], dependencies=[Depends(get_current_admin)])

@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary():
    """
    สรุปภาพรวมโรงแรมวันนี้ (Occupancy Rate, จำนวนห้องว่าง, จำนวนห้องที่มีแขก, ยอดจอง, รายได้วันนี้)
    """
    return db.get_dashboard_summary()

@router.get("/rooms/live-grid", response_model=List[RoomLiveGridItem])
def get_live_grid():
    """
    ดึงสถานะผังห้องพัก 10 ห้อง 4 ชั้นแบบ Real-time (จาก View v_room_live_status)
    แสดงสถานะ: available / occupied / maintenance พร้อมข้อมูลผู้เข้าพักปัจจุบัน
    """
    return db.get_room_live_status()

@router.patch("/rooms/{room_id}/status", response_model=SimpleMessageResponse)
def set_room_status(room_id: str, req: RoomStatusUpdate):
    """
    สลับสถานะห้องพักระหว่าง 'available' (พร้อมใช้) และ 'maintenance' (ปิดปรับปรุง)
    """
    try:
        updated = db.update_room_status(room_id, req.status)
        return {
            "success": True,
            "message": f"เปลี่ยนสถานะห้อง {updated.get('room_number')} เป็น {req.status} เรียบร้อยแล้ว",
            "data": updated
        }
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบห้องพักดังกล่าว")

@router.get("/bookings")
def get_all_bookings(
    status: Optional[str] = Query(None, description="กรองตามสถานะ: pending, confirmed, cancelled, checked_in, checked_out"),
    channel: Optional[str] = Query(None, description="กรองตามช่องทาง: voice_bot, web"),
    target_date: Optional[date] = Query(None, description="กรองห้องที่เข้าพักในวันที่ระบุ"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    ดูรายการจองทั้งหมด พร้อม Pagination และตัวกรอง
    """
    return db.get_all_bookings(status=status, channel=channel, target_date=target_date, page=page, limit=limit)

@router.post("/bookings/walk-in", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_walk_in_booking(req: AdminWalkInRequest, admin_user: dict = Depends(get_current_admin)):
    """
    บันทึกการจองสำหรับแขก Walk-in ที่หน้าเคาน์เตอร์ Front Desk
    ตั้งสถานะเริ่มต้นเป็น 'checked_in' ทันที
    """
    try:
        booking = db.create_booking(
            room_id=req.room_id,
            guest_name=req.guest_name,
            guest_phone=req.guest_phone,
            check_in_date=req.check_in_date,
            check_out_date=req.check_out_date,
            num_guests=req.num_guests,
            user_id=None,
            booking_channel="web",
            status="checked_in",
            payment_status=req.payment_status,
            payment_method=req.payment_method
        )
        return booking
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/bookings/{booking_id}/check-in", response_model=SimpleMessageResponse)
def check_in_guest(booking_id: str):
    """
    เจ้าหน้าที่กดรับแขกเข้าพัก (Check-in) -> เปลี่ยนสถานะเป็น 'checked_in'
    """
    try:
        booking = db.update_booking_status(booking_id, "checked_in")
        return {
            "success": True,
            "message": f"เช็คอินห้อง {booking.get('room_number', '')} สำหรับ {booking.get('guest_name', '')} สำเร็จ",
            "data": booking
        }
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบข้อมูลการจอง")

@router.patch("/bookings/{booking_id}/check-out", response_model=SimpleMessageResponse)
def check_out_guest(booking_id: str):
    """
    เจ้าหน้าที่กดส่งแขกออกจากที่พัก (Check-out) -> เปลี่ยนสถานะเป็น 'checked_out'
    ห้องจะกลับมาเป็นสถานะว่าง (available) โดยอัตโนมัติ
    """
    try:
        booking = db.update_booking_status(booking_id, "checked_out")
        return {
            "success": True,
            "message": f"เช็คเอาต์ห้อง {booking.get('room_number', '')} สำเร็จ",
            "data": booking
        }
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบข้อมูลการจอง")

@router.patch("/bookings/{booking_id}/payment", response_model=SimpleMessageResponse)
def update_payment(booking_id: str, req: AdminPaymentUpdate):
    """
    บันทึกหรืออัปเดตการชำระเงิน (completed / pending / refunded) และวิธีชำระ (cash / qr / credit_card)
    """
    try:
        booking = db.update_booking_payment(booking_id, req.payment_status, req.payment_method)
        return {
            "success": True,
            "message": f"อัปเดตสถานะการชำระเงินเป็น {req.payment_status} สำเร็จ",
            "data": booking
        }
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบข้อมูลการจอง")

@router.get("/voice-logs")
def get_voice_logs(
    session_id: Optional[str] = Query(None),
    caller_phone: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """
    ดูบันทึกการสนทนาของ AI Voice Bot (Botnoi Transcripts, Duration, Intents, Confidence Score)
    """
    return db.get_call_logs(session_id=session_id, caller_phone=caller_phone, limit=limit)
