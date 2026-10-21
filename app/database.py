import uuid
import secrets
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import settings

# ------------------------------------------------------------------------------
# DEFAULT SEED DATA (PHYSICAL INVENTORY: 10 ROOMS ACROSS 4 FLOORS)
# Matches setup.sql exactly
# ------------------------------------------------------------------------------
DEFAULT_ROOM_TYPES = [
    {
        "id": "d1111111-1111-1111-1111-111111111111",
        "name": "Standard Deluxe Room",
        "description": "ห้องพักชั้น 1 ตกแต่งสไตล์โมเดิร์น เตียงควีนไซส์ วิวสวน พร้อมสิ่งอำนวยความสะดวกครบครัน",
        "max_guests": 2,
        "base_price": 1200.00,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "d2222222-2222-2222-2222-222222222222",
        "name": "Executive Suite",
        "description": "ห้องสวีทชั้น 2 เตียงคิงไซส์ ระเบียงส่วนตัว โต๊ะทำงาน และเครื่องชงกาแฟแคปซูล",
        "max_guests": 2,
        "base_price": 2500.00,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "d3333333-3333-3333-3333-333333333333",
        "name": "Family Grand Suite",
        "description": "ห้องครอบครัวชั้น 3 ประกอบด้วย 2 เตียงคิงไซส์ โซนนั่งเล่นกว้างขวาง และอ่างอาบน้ำ",
        "max_guests": 4,
        "base_price": 3800.00,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "d4444444-4444-4444-4444-444444444444",
        "name": "Presidential Penthouse",
        "description": "เพนต์เฮาส์หรูเหมาทั้งชั้น 4 วิวพาโนรามา อ่างจากุซซี่ส่วนตัว และโซนรับประทานอาหาร",
        "max_guests": 6,
        "base_price": 6500.00,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
]

DEFAULT_ROOMS = [
    # Floor 1 (4 rooms)
    {"id": "r101-0000-0000-0000-000000000101", "room_number": "101", "floor": 1, "room_type_id": "d1111111-1111-1111-1111-111111111111", "status": "available"},
    {"id": "r102-0000-0000-0000-000000000102", "room_number": "102", "floor": 1, "room_type_id": "d1111111-1111-1111-1111-111111111111", "status": "available"},
    {"id": "r103-0000-0000-0000-000000000103", "room_number": "103", "floor": 1, "room_type_id": "d1111111-1111-1111-1111-111111111111", "status": "available"},
    {"id": "r104-0000-0000-0000-000000000104", "room_number": "104", "floor": 1, "room_type_id": "d1111111-1111-1111-1111-111111111111", "status": "available"},
    # Floor 2 (3 rooms)
    {"id": "r201-0000-0000-0000-000000000201", "room_number": "201", "floor": 2, "room_type_id": "d2222222-2222-2222-2222-222222222222", "status": "available"},
    {"id": "r202-0000-0000-0000-000000000202", "room_number": "202", "floor": 2, "room_type_id": "d2222222-2222-2222-2222-222222222222", "status": "available"},
    {"id": "r203-0000-0000-0000-000000000203", "room_number": "203", "floor": 2, "room_type_id": "d2222222-2222-2222-2222-222222222222", "status": "available"},
    # Floor 3 (2 rooms)
    {"id": "r301-0000-0000-0000-000000000301", "room_number": "301", "floor": 3, "room_type_id": "d3333333-3333-3333-3333-333333333333", "status": "available"},
    {"id": "r302-0000-0000-0000-000000000302", "room_number": "302", "floor": 3, "room_type_id": "d3333333-3333-3333-3333-333333333333", "status": "available"},
    # Floor 4 (1 room)
    {"id": "r401-0000-0000-0000-000000000401", "room_number": "401", "floor": 4, "room_type_id": "d4444444-4444-4444-4444-444444444444", "status": "available"}
]

# ------------------------------------------------------------------------------
# DATABASE CLIENT WRAPPER (SUPABASE + SEAMLESS IN-MEMORY FALLBACK)
# ------------------------------------------------------------------------------
class DatabaseService:
    def __init__(self):
        self.client = None
        self.is_supabase_connected = False
        
        # In-memory storage for fallback/dev/test mode
        self._room_types: List[Dict[str, Any]] = [dict(rt) for rt in DEFAULT_ROOM_TYPES]
        self._rooms: List[Dict[str, Any]] = [dict(r) for r in DEFAULT_ROOMS]
        self._bookings: List[Dict[str, Any]] = []
        self._call_logs: List[Dict[str, Any]] = []
        self._profiles: Dict[str, Dict[str, Any]] = {
            "admin-user-id-0001": {
                "id": "admin-user-id-0001",
                "email": "admin@hotel.com",
                "full_name": "Hotel Admin",
                "phone_number": "0819999999",
                "role": "admin",
                "password_hash": "admin123",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "demo-user-id-0001": {
                "id": "demo-user-id-0001",
                "email": "user@gmail.com",
                "full_name": "Guest Somchai",
                "phone_number": "0891234567",
                "role": "user",
                "password_hash": "user123",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        self._init_supabase()

    def _init_supabase(self):
        """Attempts to initialize Supabase client if valid credentials exist."""
        if settings.has_supabase_config:
            try:
                from supabase import create_client
                key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
                self.client = create_client(settings.SUPABASE_URL, key)
                self.is_supabase_connected = True
                print(f"[Database] Connected to live Supabase: {settings.SUPABASE_URL}")
                self.seed_admin_user()
            except Exception as e:
                print(f"[Database] Warning: Failed to connect to Supabase ({e}). Using local mock storage.")
                self.is_supabase_connected = False
        else:
            print("[Database] Supabase URL not provided. Running with in-memory database (10 rooms initialized).")

    def seed_admin_user(self):
        """Ensures default admin user exists in Supabase Auth and profiles table."""
        if not self.is_supabase_connected or not self.client:
            return
        try:
            res = self.client.auth.admin.list_users()
            admin_user = next((u for u in res if u.email == "admin@hotel.com"), None)
            if not admin_user:
                created = self.client.auth.admin.create_user({
                    "email": "admin@hotel.com",
                    "password": "admin123",
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": "Hotel Admin",
                        "phone_number": "0819999999",
                        "role": "admin"
                    }
                })
                admin_uid = created.user.id if hasattr(created, "user") else created.id
                print(f"[Database] Seeded admin user: admin@hotel.com ({admin_uid})")
            else:
                admin_uid = admin_user.id

            self.client.table("profiles").upsert({
                "id": admin_uid,
                "full_name": "Hotel Admin",
                "phone_number": "0819999999",
                "role": "admin"
            }).execute()
        except Exception as e:
            # Silently catch until trigger is updated in Supabase
            pass

    # --------------------------------------------------------------------------
    # ROOMS & CATALOG
    # --------------------------------------------------------------------------
    def get_room_types(self) -> List[Dict[str, Any]]:
        if self.is_supabase_connected:
            try:
                res = self.client.table("room_types").select("*").order("base_price").execute()
                return res.data
            except Exception as e:
                print(f"[DB Error: get_room_types] {e}")
        return sorted(self._room_types, key=lambda x: x["base_price"])

    def check_room_availability(self, check_in: date, check_out: date, guests: int = 2) -> List[Dict[str, Any]]:
        """Finds all available rooms matching criteria between check_in and check_out."""
        if check_out <= check_in:
            raise ValueError("Check-out date must be after check-in date")

        nights = (check_out - check_in).days

        if self.is_supabase_connected:
            try:
                # Call PostgreSQL stored procedure check_room_availability
                res = self.client.rpc("check_room_availability", {
                    "p_check_in": str(check_in),
                    "p_check_out": str(check_out),
                    "p_guests": guests
                }).execute()
                return res.data
            except Exception as e:
                print(f"[DB RPC Error: check_room_availability] {e}. Falling back to Python logic.")

        # Local fallback availability query logic
        available_rooms = []
        type_map = {rt["id"]: rt for rt in self._room_types}

        for room in self._rooms:
            if room["status"] != "available":
                continue
            
            rt = type_map.get(room["room_type_id"])
            if not rt or rt["max_guests"] < guests:
                continue

            # Check booking overlap
            is_booked = False
            for b in self._bookings:
                if b["room_id"] == room["id"] and b["status"] in ("confirmed", "pending", "checked_in"):
                    b_in = date.fromisoformat(str(b["check_in_date"]))
                    b_out = date.fromisoformat(str(b["check_out_date"]))
                    # Dates overlap if NOT (b_out <= check_in or b_in >= check_out)
                    if not (b_out <= check_in or b_in >= check_out):
                        is_booked = True
                        break

            if not is_booked:
                available_rooms.append({
                    "room_id": room["id"],
                    "room_number": room["room_number"],
                    "floor": room["floor"],
                    "room_type_id": rt["id"],
                    "room_type_name": rt["name"],
                    "max_guests": rt["max_guests"],
                    "price_per_night": float(rt["base_price"]),
                    "total_nights": nights,
                    "total_estimated_price": float(rt["base_price"] * nights)
                })

        return sorted(available_rooms, key=lambda x: (x["price_per_night"], x["room_number"]))

    def get_room_live_status(self) -> List[Dict[str, Any]]:
        """Returns live status of all 10 rooms across 4 floors (view v_room_live_status)."""
        if self.is_supabase_connected:
            try:
                res = self.client.table("v_room_live_status").select("*").order("floor").order("room_number").execute()
                return res.data
            except Exception as e:
                print(f"[DB Error: get_room_live_status] {e}")

        # Local view simulation
        today = date.today()
        type_map = {rt["id"]: rt for rt in self._room_types}
        result = []

        for room in sorted(self._rooms, key=lambda r: (r["floor"], r["room_number"])):
            rt = type_map.get(room["room_type_id"], {})
            status = "available"
            active_b = None

            if room["status"] == "maintenance":
                status = "maintenance"
            else:
                for b in self._bookings:
                    if b["room_id"] == room["id"] and b["status"] in ("confirmed", "checked_in"):
                        b_in = date.fromisoformat(str(b["check_in_date"]))
                        b_out = date.fromisoformat(str(b["check_out_date"]))
                        if b_in <= today < b_out:
                            status = "occupied"
                            active_b = b
                            break

            result.append({
                "room_id": room["id"],
                "room_number": room["room_number"],
                "floor": room["floor"],
                "room_type_name": rt.get("name", ""),
                "base_price": float(rt.get("base_price", 0)),
                "max_guests": rt.get("max_guests", 2),
                "current_status": status,
                "active_booking_id": active_b["id"] if active_b else None,
                "booking_code": active_b["booking_code"] if active_b else None,
                "guest_name": active_b["guest_name"] if active_b else None,
                "guest_phone": active_b["guest_phone"] if active_b else None,
                "check_in_date": active_b["check_in_date"] if active_b else None,
                "check_out_date": active_b["check_out_date"] if active_b else None,
                "booking_status": active_b["status"] if active_b else None
            })

        return result

    def update_room_status(self, room_id: str, new_status: str) -> Dict[str, Any]:
        """Toggles or sets room status between 'available' and 'maintenance'."""
        if self.is_supabase_connected:
            try:
                res = self.client.table("rooms").update({"status": new_status}).eq("id", room_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"[DB Error: update_room_status] {e}")

        for room in self._rooms:
            if room["id"] == room_id:
                room["status"] = new_status
                return room
        raise KeyError(f"Room not found with ID {room_id}")

    def get_room_by_id(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Fetches room and joined room_type details by ID."""
        if self.is_supabase_connected:
            try:
                res = self.client.table("rooms").select("*, room_types(*)").eq("id", room_id).execute()
                if res.data:
                    r = res.data[0]
                    rt = r.get("room_types") or {}
                    return {
                        "id": r["id"],
                        "room_number": r["room_number"],
                        "floor": r["floor"],
                        "room_type_id": r["room_type_id"],
                        "status": r["status"],
                        "room_type_name": rt.get("name", ""),
                        "base_price": float(rt.get("base_price", 0)),
                        "max_guests": rt.get("max_guests", 2)
                    }
            except Exception as e:
                print(f"[DB Error: get_room_by_id] {e}")

        room = next((r for r in self._rooms if r["id"] == room_id), None)
        if room:
            type_map = {rt["id"]: rt for rt in self._room_types}
            rt = type_map.get(room["room_type_id"], {})
            return {
                "id": room["id"],
                "room_number": room["room_number"],
                "floor": room["floor"],
                "room_type_id": room["room_type_id"],
                "status": room["status"],
                "room_type_name": rt.get("name", ""),
                "base_price": float(rt.get("base_price", 0)),
                "max_guests": rt.get("max_guests", 2)
            }
        return None

    def _format_booking_row(self, b: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not b:
            return None
        out = dict(b)
        rooms_rel = out.pop("rooms", None)
        if isinstance(rooms_rel, dict):
            if not out.get("room_number"):
                out["room_number"] = rooms_rel.get("room_number")
            rt = rooms_rel.get("room_types") or {}
            if isinstance(rt, dict) and not out.get("room_type_name"):
                out["room_type_name"] = rt.get("name")
        return out

    # --------------------------------------------------------------------------
    # BOOKINGS
    # --------------------------------------------------------------------------
    def create_booking(
        self,
        room_id: str,
        guest_name: str,
        guest_phone: str,
        check_in_date: date,
        check_out_date: date,
        num_guests: int = 1,
        user_id: Optional[str] = None,
        booking_channel: str = "web",
        status: str = "confirmed",
        payment_status: str = "pending",
        payment_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a booking with room availability verification and price calculation."""
        if check_out_date <= check_in_date:
            raise ValueError("Check-out date must be after check-in date")

        # Find room & price
        room = self.get_room_by_id(room_id)
        if not room:
            raise KeyError("Room not found")

        # Check availability
        if self.is_supabase_connected:
            try:
                overlap = self.client.table("bookings").select("id").eq("room_id", room_id).in_("status", ["confirmed", "pending", "checked_in"]).lt("check_in_date", str(check_out_date)).gt("check_out_date", str(check_in_date)).execute()
                if overlap.data and len(overlap.data) > 0:
                    raise ValueError("ห้องพักนี้มีผู้จองแล้วในช่วงเวลาดังกล่าว")
            except ValueError:
                raise
            except Exception as e:
                print(f"[DB Check Warning: create_booking] {e}")
        else:
            for b in self._bookings:
                if b["room_id"] == room_id and b["status"] in ("confirmed", "pending", "checked_in"):
                    b_in = date.fromisoformat(str(b["check_in_date"]))
                    b_out = date.fromisoformat(str(b["check_out_date"]))
                    if not (b_out <= check_in_date or b_in >= check_out_date):
                        raise ValueError("ห้องพักนี้มีผู้จองแล้วในช่วงเวลาดังกล่าว")

        nights = (check_out_date - check_in_date).days
        total_price = float(room["base_price"]) * nights
        booking_code = f"HTL-{secrets.token_hex(3).upper()}"
        booking_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        db_record = {
            "id": booking_id,
            "booking_code": booking_code,
            "user_id": user_id,
            "room_id": room_id,
            "guest_name": guest_name,
            "guest_phone": guest_phone,
            "check_in_date": str(check_in_date),
            "check_out_date": str(check_out_date),
            "num_guests": num_guests,
            "total_price": total_price,
            "status": status,
            "booking_channel": booking_channel,
            "payment_status": payment_status,
            "payment_method": payment_method,
            "paid_at": now_iso if payment_status == "completed" else None
        }

        full_record = {
            **db_record,
            "room_number": room["room_number"],
            "room_type_name": room["room_type_name"],
            "created_at": now_iso,
            "updated_at": now_iso
        }

        if self.is_supabase_connected:
            try:
                res = self.client.table("bookings").insert(db_record).execute()
                if res.data:
                    return full_record
            except Exception as e:
                print(f"[DB Error: create_booking] {e}")
                raise ValueError(f"Failed to save booking to database: {str(e)}")

        self._bookings.insert(0, full_record)
        return full_record

    def get_booking_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        if self.is_supabase_connected:
            try:
                res = self.client.table("bookings").select("*, rooms(room_number, floor, room_types(name))").eq("id", booking_id).execute()
                if res.data:
                    return self._format_booking_row(res.data[0])
            except Exception as e:
                print(f"[DB Error: get_booking_by_id] {e}")

        return next((b for b in self._bookings if b["id"] == booking_id), None)

    def get_booking_by_code_and_phone(self, booking_code: str, phone: str) -> Optional[Dict[str, Any]]:
        code_clean = booking_code.strip().upper()
        phone_clean = phone.strip()

        if self.is_supabase_connected:
            try:
                res = self.client.table("bookings").select("*, rooms(room_number, floor, room_types(name))").eq("booking_code", code_clean).eq("guest_phone", phone_clean).execute()
                if res.data:
                    return self._format_booking_row(res.data[0])
            except Exception as e:
                print(f"[DB Error: get_booking_by_code_and_phone] {e}")

        for b in self._bookings:
            if b["booking_code"].upper() == code_clean and b["guest_phone"] == phone_clean:
                return b
        return None

    def get_user_bookings(self, user_id: str) -> List[Dict[str, Any]]:
        if self.is_supabase_connected:
            try:
                res = self.client.table("bookings").select("*, rooms(room_number, room_types(name))").eq("user_id", user_id).order("created_at", desc=True).execute()
                return [self._format_booking_row(b) for b in res.data]
            except Exception as e:
                print(f"[DB Error: get_user_bookings] {e}")

        return [b for b in self._bookings if b.get("user_id") == user_id]

    def get_all_bookings(
        self,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        target_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Lists bookings with optional filters for admin view."""
        if self.is_supabase_connected:
            try:
                query = self.client.table("bookings").select("*, rooms(room_number, floor, room_types(name))", count="exact")
                if status:
                    query = query.eq("status", status)
                if channel:
                    query = query.eq("booking_channel", channel)
                if target_date:
                    date_str = str(target_date)
                    query = query.lte("check_in_date", date_str).gt("check_out_date", date_str)

                start_idx = (page - 1) * limit
                end_idx = start_idx + limit - 1
                res = query.order("created_at", desc=True).range(start_idx, end_idx).execute()
                total = res.count if res.count is not None else len(res.data)
                formatted = [self._format_booking_row(b) for b in res.data]
                return {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "bookings": formatted
                }
            except Exception as e:
                print(f"[DB Error: get_all_bookings] {e}")

        filtered = self._bookings
        if status:
            filtered = [b for b in filtered if b["status"] == status]
        if channel:
            filtered = [b for b in filtered if b["booking_channel"] == channel]
        if target_date:
            date_str = str(target_date)
            filtered = [b for b in filtered if b["check_in_date"] <= date_str < b["check_out_date"]]

        total = len(filtered)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated = filtered[start_idx:end_idx]

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "bookings": paginated
        }

    def update_booking_status(self, booking_id: str, new_status: str) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.is_supabase_connected:
            try:
                res = self.client.table("bookings").update({"status": new_status, "updated_at": now_iso}).eq("id", booking_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"[DB Error: update_booking_status] {e}")

        for b in self._bookings:
            if b["id"] == booking_id:
                b["status"] = new_status
                b["updated_at"] = now_iso
                return b
        raise KeyError(f"Booking {booking_id} not found")

    def update_booking_payment(self, booking_id: str, payment_status: str, payment_method: Optional[str] = "cash") -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        updates = {
            "payment_status": payment_status,
            "payment_method": payment_method,
            "updated_at": now_iso,
            "paid_at": now_iso if payment_status == "completed" else None
        }

        if self.is_supabase_connected:
            try:
                res = self.client.table("bookings").update(updates).eq("id", booking_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"[DB Error: update_booking_payment] {e}")

        for b in self._bookings:
            if b["id"] == booking_id:
                b.update(updates)
                return b
        raise KeyError(f"Booking {booking_id} not found")

    # --------------------------------------------------------------------------
    # CALL LOGS (AI VOICE BOT)
    # --------------------------------------------------------------------------
    def save_call_log(
        self,
        session_id: str,
        caller_phone: Optional[str] = None,
        duration_seconds: int = 0,
        messages: List[Dict[str, Any]] = None,
        intent_data: Dict[str, Any] = None,
        confidence_score: Optional[float] = None,
        booking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        log_id = str(uuid.uuid4())
        record = {
            "id": log_id,
            "session_id": session_id,
            "caller_phone": caller_phone,
            "duration_seconds": duration_seconds,
            "messages": messages or [],
            "intent_data": intent_data or {},
            "confidence_score": confidence_score,
            "booking_id": booking_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.is_supabase_connected:
            try:
                res = self.client.table("call_logs").insert(record).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"[DB Error: save_call_log] {e}")

        self._call_logs.insert(0, record)
        return record

    def get_call_logs(self, session_id: Optional[str] = None, caller_phone: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if self.is_supabase_connected:
            try:
                q = self.client.table("call_logs").select("*")
                if session_id:
                    q = q.eq("session_id", session_id)
                if caller_phone:
                    q = q.eq("caller_phone", caller_phone)
                res = q.order("created_at", desc=True).limit(limit).execute()
                return res.data
            except Exception as e:
                print(f"[DB Error: get_call_logs] {e}")

        filtered = self._call_logs
        if session_id:
            filtered = [l for l in filtered if l["session_id"] == session_id]
        if caller_phone:
            filtered = [l for l in filtered if l.get("caller_phone") == caller_phone]
        return filtered[:limit]

    # --------------------------------------------------------------------------
    # DASHBOARD SUMMARY
    # --------------------------------------------------------------------------
    def get_dashboard_summary(self) -> Dict[str, Any]:
        live_grid = self.get_room_live_status()
        total_rooms = len(live_grid)
        occupied = sum(1 for r in live_grid if r["current_status"] == "occupied")
        available = sum(1 for r in live_grid if r["current_status"] == "available")
        maintenance = sum(1 for r in live_grid if r["current_status"] == "maintenance")
        occupancy_rate = round((occupied / total_rooms * 100), 1) if total_rooms > 0 else 0.0

        today_str = str(date.today())

        if self.is_supabase_connected:
            try:
                b_res = self.client.table("bookings").select("total_price, payment_status, paid_at, created_at").execute()
                all_b = b_res.data or []
                today_bookings = [
                    b for b in all_b 
                    if str(b.get("created_at", "")).startswith(today_str)
                ]
                revenue_today = sum(
                    float(b["total_price"]) 
                    for b in all_b 
                    if b.get("payment_status") == "completed" and str(b.get("paid_at") or "").startswith(today_str)
                )
                return {
                    "total_rooms": total_rooms,
                    "occupied": occupied,
                    "available": available,
                    "maintenance": maintenance,
                    "occupancy_rate_percent": occupancy_rate,
                    "revenue_today": revenue_today,
                    "total_bookings_today": len(today_bookings),
                    "active_bookings_count": occupied
                }
            except Exception as e:
                print(f"[DB Error: get_dashboard_summary] {e}")

        today_bookings = [
            b for b in self._bookings 
            if b.get("created_at", "").startswith(today_str)
        ]
        
        revenue_today = sum(
            float(b["total_price"]) 
            for b in self._bookings 
            if b.get("payment_status") == "completed" and (b.get("paid_at") or "").startswith(today_str)
        )

        return {
            "total_rooms": total_rooms,
            "occupied": occupied,
            "available": available,
            "maintenance": maintenance,
            "occupancy_rate_percent": occupancy_rate,
            "revenue_today": revenue_today,
            "total_bookings_today": len(today_bookings),
            "active_bookings_count": occupied
        }

db = DatabaseService()
