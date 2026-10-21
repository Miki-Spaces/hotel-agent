drop function if exists public.check_room_availability(date, date, integer);

create function public.check_room_availability(
    p_check_in date,
    p_check_out date,
    p_guests integer default 2
)
returns table (
    room_id uuid,
    room_type_id uuid,
    room_number text,
    floor integer,
    room_type_name text,
    max_guests integer,
    price_per_night numeric,
    total_nights integer,
    total_estimated_price numeric
) language plpgsql as $$
declare
    v_nights integer;
begin
    v_nights := p_check_out - p_check_in;
    if v_nights <= 0 then
        raise exception 'Check-out date must be after check-in date';
    end if;

    return query
    select
        r.id as room_id,
        r.room_type_id,
        r.room_number,
        r.floor,
        rt.name as room_type_name,
        rt.max_guests,
        rt.base_price as price_per_night,
        v_nights as total_nights,
        (rt.base_price * v_nights) as total_estimated_price
    from public.rooms r
    join public.room_types rt on r.room_type_id = rt.id
    where r.status = 'available'
      and rt.max_guests >= p_guests
      and r.id not in (
          select b.room_id
          from public.bookings b
          where b.status in ('confirmed', 'pending', 'checked_in')
            and not (b.check_out_date <= p_check_in or b.check_in_date >= p_check_out)
      )
    order by rt.base_price asc, r.room_number asc;
end;
$$;
