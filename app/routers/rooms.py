from datetime import date
from typing import List
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas import RoomTypeResponse, RoomAvailabilityItem
from app.database import db

router = APIRouter(prefix="/api/rooms", tags=["Rooms & Availability"])

@router.get("/catalog", response_model=List[RoomTypeResponse])
def get_room_catalog():
    """
    ดูรายการประเภทห้องพักทั้ง 4 แบบ พร้อมราคาเริ่มต้นและรายละเอียด
    - Standard Deluxe Room (1,200 THB)
    - Executive Suite (2,500 THB)
    - Family Grand Suite (3,800 THB)
    - Presidential Penthouse (6,500 THB)
    """
    return db.get_room_types()

@router.get("/check-availability", response_model=List[RoomAvailabilityItem])
def check_availability(
    check_in: date = Query(..., description="วันเข้าพัก (YYYY-MM-DD)"),
    check_out: date = Query(..., description="วันเช็คเอาต์ (YYYY-MM-DD)"),
    guests: int = Query(default=2, ge=1, le=10, description="จำนวนผู้เข้าพัก")
):
    """
    ค้นหาห้องพักที่ว่างตามช่วงวันและจำนวนผู้เข้าพัก
    คำนวณจำนวนคืนและยอดรวมราคาโดยอัตโนมัติ
    """
    if check_out <= check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="วันเช็คเอาต์ต้องอยู่หลังวันเช็คอินอย่างน้อย 1 วัน"
        )
    
    try:
        available_rooms = db.check_room_availability(check_in, check_out, guests)
        return available_rooms
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
