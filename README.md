# Hotel AI Voice Booking API

FastAPI backend for hotel reservations and Botnoi AI Voice Bot integration. Built with Python 3.9, Pydantic, JWT authentication, and Supabase PostgreSQL.

---

## Architecture Overview

```text
d:\Hotel Agent\
├── app/
│   ├── main.py              # FastAPI app, CORS middleware, and router mounts
│   ├── config.py            # Environment configuration (.env loader)
│   ├── database.py          # Supabase client wrapper with in-memory fallback
│   ├── auth.py              # JWT generator, decoder, and RBAC dependencies
│   ├── schemas.py           # Pydantic request and response models
│   └── routers/
│       ├── auth.py          # /api/auth/*
│       ├── rooms.py         # /api/rooms/*
│       ├── bookings.py      # /api/bookings/*
│       ├── admin.py         # /api/admin/*
│       └── voice.py         # /api/voice/*
├── test_api.py              # Automated test suite covering all 21 test scenarios
├── run_server.py            # Development server runner
├── requirements.txt         # Python dependencies
├── .env                     # Local environment settings
└── README.md                # Usage guide and API reference
```

---

## Getting Started

### 1. Prerequisites
- Python 3.9 or higher
- pip package manager

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
python run_server.py
```
The server starts on `http://127.0.0.1:8000`.

### 4. Interactive Documentation
Open your browser to test endpoints directly:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Database Configuration

The application features a Dual-Mode database architecture:

1. **In-Memory Fallback (Active by default)**:
   Pre-seeds all 10 physical rooms across 4 floors, 4 room categories, and default test accounts. Works without external internet access or database setup.
2. **Supabase PostgreSQL (Production)**:
   Set your project credentials in `.env`:
   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
   SUPABASE_JWT_SECRET=your-supabase-jwt-secret
   ```
   When credentials are supplied, the backend automatically directs queries to your live Supabase database and PostgreSQL stored procedures.

---

## Pre-seeded Accounts

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Admin** | `admin@hotel.com` | `admin123` | Full access to `/api/admin/*` dashboard, live grid, check-in, check-out, and logs |
| **User** | `user@gmail.com` | `user123` | Guest access to create reservations, check `/api/bookings/my`, and manage own profile |

---

## API Reference & Examples

### 1. Authentication (`/api/auth`)

#### Register (`POST /api/auth/register`)
Create a new guest account.
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "guest@example.com",
    "password": "Password123!",
    "full_name": "สมชาย ใจดี",
    "phone_number": "0812345678"
  }'
```

#### Login (`POST /api/auth/login`)
Authenticate and receive a Bearer JWT token.
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@hotel.com",
    "password": "admin123"
  }'
```
Response:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": { "id": "...", "email": "admin@hotel.com" },
  "profile": { "role": "admin", "full_name": "Hotel Admin" }
}
```

#### Profile (`GET /api/auth/me`)
```bash
curl http://127.0.0.1:8000/api/auth/me \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 2. Rooms & Availability (`/api/rooms`)

#### Catalog (`GET /api/rooms/catalog`)
Returns the 4 room categories with pricing:
- Standard Deluxe Room (1,200 THB)
- Executive Suite (2,500 THB)
- Family Grand Suite (3,800 THB)
- Presidential Penthouse (6,500 THB)

```bash
curl http://127.0.0.1:8000/api/rooms/catalog
```

#### Check Availability (`GET /api/rooms/check-availability`)
Calculates available rooms, nights, and total estimated price.
```bash
curl "http://127.0.0.1:8000/api/rooms/check-availability?check_in=2026-11-01&check_out=2026-11-03&guests=2"
```

---

### 3. Bookings (`/api/bookings`)

#### Create Reservation (`POST /api/bookings`)
Creates a new reservation from the web interface.
```bash
curl -X POST http://127.0.0.1:8000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": "r101-0000-0000-0000-000000000101",
    "guest_name": "สมชาย ใจดี",
    "guest_phone": "0812345678",
    "check_in_date": "2026-11-01",
    "check_out_date": "2026-11-03",
    "num_guests": 2
  }'
```
Returns a unique `booking_code` (e.g. `HTL-8DF10A`).

#### Track Reservation (`GET /api/bookings/track`)
Check reservation details using `booking_code` and `phone` without logging in.
```bash
curl "http://127.0.0.1:8000/api/bookings/track?booking_code=HTL-8DF10A&phone=0812345678"
```

#### My Bookings (`GET /api/bookings/my`)
Requires user authentication header.
```bash
curl http://127.0.0.1:8000/api/bookings/my \
  -H "Authorization: Bearer <USER_TOKEN>"
```

#### Cancel Reservation (`PATCH /api/bookings/{id}/cancel`)
Owner or Admin can cancel a pending or confirmed booking.
```bash
curl -X PATCH http://127.0.0.1:8000/api/bookings/<BOOKING_ID>/cancel \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 4. Admin Operations (`/api/admin`)
All endpoints in this group require an Admin Bearer token (`role: "admin"`). Regular user tokens receive `403 Forbidden`.

#### Dashboard Summary (`GET /api/admin/dashboard/summary`)
Returns today's occupancy rate, count of available/occupied/maintenance rooms, and revenue.
```bash
curl http://127.0.0.1:8000/api/admin/dashboard/summary \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

#### Live Room Grid (`GET /api/admin/rooms/live-grid`)
Returns real-time status of all 10 physical rooms across 4 floors.
```bash
curl http://127.0.0.1:8000/api/admin/rooms/live-grid \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

#### Toggle Room Maintenance (`PATCH /api/admin/rooms/{id}/status`)
```bash
curl -X PATCH http://127.0.0.1:8000/api/admin/rooms/<ROOM_ID>/status \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"status": "maintenance"}'
```

#### Check-In Guest (`PATCH /api/admin/bookings/{id}/check-in`)
Sets booking status to `checked_in`. The room becomes occupied on the live grid.
```bash
curl -X PATCH http://127.0.0.1:8000/api/admin/bookings/<BOOKING_ID>/check-in \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

#### Check-Out Guest (`PATCH /api/admin/bookings/{id}/check-out`)
Sets booking status to `checked_out`. The room returns to `available` status.
```bash
curl -X PATCH http://127.0.0.1:8000/api/admin/bookings/<BOOKING_ID>/check-out \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

#### Record Payment (`PATCH /api/admin/bookings/{id}/payment`)
```bash
curl -X PATCH http://127.0.0.1:8000/api/admin/bookings/<BOOKING_ID>/payment \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"payment_status": "completed", "payment_method": "qr"}'
```

#### Voice Call Logs (`GET /api/admin/voice-logs`)
Inspect Botnoi call transcripts, duration, and extracted intent data.
```bash
curl http://127.0.0.1:8000/api/admin/voice-logs \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

---

### 5. Botnoi AI Voice Bot Webhooks (`/api/voice`)

These endpoints connect to the Botnoi dialog flow to automate voice reservations.

#### Check Rooms for Speech (`POST /api/voice/check-rooms`)
Calculates room availability and returns Thai natural language speech for TTS playback.
```bash
curl -X POST http://127.0.0.1:8000/api/voice/check-rooms \
  -H "Content-Type: application/json" \
  -d '{
    "check_in": "2026-11-01",
    "check_out": "2026-11-03",
    "guests": 2
  }'
```
Response:
```json
{
  "available": true,
  "rooms": [
    {
      "room_type_id": "d1111111-1111-1111-1111-111111111111",
      "room_type": "Standard Deluxe Room",
      "max_guests": 2,
      "price_per_night": 1200.0,
      "total_nights": 2,
      "total_price": 2400.0,
      "available_rooms_count": 4
    },
    {
      "room_type_id": "d2222222-2222-2222-2222-222222222222",
      "room_type": "Executive Suite",
      "max_guests": 2,
      "price_per_night": 2500.0,
      "total_nights": 2,
      "total_price": 5000.0,
      "available_rooms_count": 3
    },
    {
      "room_type_id": "d3333333-3333-3333-3333-333333333333",
      "room_type": "Family Grand Suite",
      "max_guests": 4,
      "price_per_night": 3800.0,
      "total_nights": 2,
      "total_price": 7600.0,
      "available_rooms_count": 2
    },
    {
      "room_type_id": "d4444444-4444-4444-4444-444444444444",
      "room_type": "Presidential Penthouse",
      "max_guests": 6,
      "price_per_night": 6500.0,
      "total_nights": 2,
      "total_price": 13000.0,
      "available_rooms_count": 1
    }
  ],
  "available_rooms_count": 10,
  "speech_text": "มีห้องว่างให้เลือกค่ะ 1. Standard Deluxe Room พักได้ไม่เกิน 2 ท่าน คืนละ 1,200 บาท รวม 2 คืน เป็นเงิน 2,400 บาท 2. Executive Suite พักได้ไม่เกิน 2 ท่าน คืนละ 2,500 บาท รวม 2 คืน เป็นเงิน 5,000 บาท 3. Family Grand Suite พักได้ไม่เกิน 4 ท่าน คืนละ 3,800 บาท รวม 2 คืน เป็นเงิน 7,600 บาท 4. Presidential Penthouse พักได้ไม่เกิน 6 ท่าน คืนละ 6,500 บาท รวม 2 คืน เป็นเงิน 13,000 บาท ต้องการเลือกห้องประเภทไหนคะ"
}
```

Each `rooms` item represents one room type, not a physical room. Send the selected `room_type_id` to `POST /api/voice/book-room`; the booking endpoint assigns an available physical room at booking time. The availability function must return `room_type_id`. Apply `migrations/20261021_voice_room_type_availability.sql` to an existing Supabase database before deploying this response change.

#### Book Room via Voice (`POST /api/voice/book-room`)
Completes reservation during a phone conversation.
```bash
curl -X POST http://127.0.0.1:8000/api/voice/book-room \
  -H "Content-Type: application/json" \
  -d '{
    "room_type_id": "d1111111-1111-1111-1111-111111111111",
    "guest_name": "คุณวิชัย ชัยชนะ",
    "guest_phone": "0897654321",
    "check_in": "2026-11-01",
    "check_out": "2026-11-03",
    "guests": 2
  }'
```
Response:
```json
{
  "success": true,
  "booking_code": "HTL-A91F2B",
  "booking_id": "b3e04130-...",
  "total_price": 2400.0,
  "speech_text": "จองห้องพักสำเร็จเรียบร้อยค่ะคุณ คุณวิชัย ชัยชนะ! รหัสการจองคือ HTL-A91F2B ยอดชำระทั้งหมด 2,400 บาท สามารถชำระเงินที่หน้าเคาน์เตอร์ตอนเช็คอินได้เลยค่ะ ขอบคุณค่ะ"
}
```

#### Save Conversation Log (`POST /api/voice/save-log`)
Saves the post-call payload including duration, transcript array, and confidence score.
```bash
curl -X POST http://127.0.0.1:8000/api/voice/save-log \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-botnoi-1001",
    "caller_phone": "0897654321",
    "duration_seconds": 54,
    "messages": [
      {"speaker": "bot", "text": "สวัสดีค่ะ โรงแรมยินดีต้อนรับค่ะ"},
      {"speaker": "user", "text": "อยากจองห้องพัก 2 คืนครับ"}
    ],
    "intent_data": {"action": "book_room", "nights": 2},
    "confidence_score": 0.98
  }'
```

---

## Running Automated Tests

A test script verifies all 21 functional scenarios across public, authenticated user, admin, and voice bot endpoints:

```bash
python test_api.py
```
Output:
```text
[Database] Supabase URL not provided. Running with in-memory database (10 rooms initialized).

--- [1] Testing Healthcheck ---
[PASS] Healthcheck passed: Hotel AI Voice Booking API

--- [2] Testing Room Catalog ---
[PASS] Catalog loaded 4 room types: ['Standard Deluxe Room', 'Executive Suite', 'Family Grand Suite', 'Presidential Penthouse']

--- [3] Testing Room Availability ---
[PASS] Availability query returned 10 available rooms for 2 nights

--- [4] Testing User Registration & Login ---
[PASS] Registered test user successfully
[PASS] Logged in as user: สมชาย ใจดี
[PASS] /api/auth/me verified

--- [5] Testing Web Booking Creation ---
[PASS] Created booking: code=HTL-FFB87C, total=2400.0 THB
[PASS] Tracked booking successfully without login
[PASS] /api/bookings/my returned 1 bookings

--- [6] Testing Admin RBAC Guard ---
[PASS] RBAC confirmed: regular user got 403 Forbidden on /api/admin/*
[PASS] Logged in as Admin

--- [7] Testing Admin Operations ---
[PASS] Admin Dashboard: total_rooms=10, available=10, occupied=0
[PASS] Admin Live Grid: 10 rooms returned across floors [1, 1, 1, 1, 2, 2, 2, 3, 3, 4]
[PASS] Admin room maintenance toggle verified
[PASS] Admin Check-in passed
[PASS] Admin Payment completed passed
[PASS] Admin Check-out passed

--- [8] Testing Voice Bot Webhook Endpoints ---
[PASS] Voice Bot check-rooms response
[PASS] Voice Bot booking response
[PASS] Voice Bot save-log passed
[PASS] Admin verified voice log with session: sess-botnoi-test-9999, messages: 5

=======================================================
>>> ALL 21 TEST SCENARIOS PASSED WITH 100% SUCCESS! <<<
=======================================================
```
