-- Room live status uses the Thailand calendar date instead of the server's UTC date.
-- Already applied to the hotel-agent Supabase project as migration v_room_live_status_thai_date.
create or replace view public.v_room_live_status as
select r.id as room_id, r.room_number, r.floor, rt.name as room_type_name,
  rt.base_price, rt.max_guests,
  case
    when r.status = 'maintenance'::room_status then 'maintenance'::text
    when b.id is not null then 'occupied'::text
    else 'available'::text
  end as current_status,
  b.id as active_booking_id, b.booking_code, b.guest_name, b.guest_phone,
  b.check_in_date, b.check_out_date, b.status as booking_status
from rooms r
join room_types rt on r.room_type_id = rt.id
left join bookings b on r.id = b.room_id
  and (now() at time zone 'Asia/Bangkok')::date >= b.check_in_date
  and (now() at time zone 'Asia/Bangkok')::date <  b.check_out_date
  and b.status = any (array['confirmed'::booking_status, 'checked_in'::booking_status])
order by r.floor, r.room_number;
