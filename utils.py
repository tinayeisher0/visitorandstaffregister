from datetime import datetime, time, timedelta
from db import query_all

BUSINESS_START = time(8, 0)
BUSINESS_END = time(16, 0)
AFTER_HOURS_LIMIT_MINUTES = 15


def now_local() -> datetime:
    return datetime.now()


def is_weekday(dt: datetime | None = None) -> bool:
    dt = dt or now_local()
    return dt.weekday() < 5


def is_public_holiday(dt: datetime | None = None) -> bool:
    dt = dt or now_local()
    holiday = query_all('SELECT 1 FROM public_holidays WHERE holiday_date = ?', (dt.date().isoformat(),))
    return bool(holiday)


def is_business_hours(dt: datetime | None = None) -> bool:
    dt = dt or now_local()
    current = dt.time()
    return is_weekday(dt) and not is_public_holiday(dt) and BUSINESS_START <= current <= BUSINESS_END


def get_active_booking(staff_id: int, dt: datetime | None = None):
    dt = dt or now_local()
    rows = query_all(
        '''SELECT * FROM afterhours_bookings
           WHERE staff_id = ? AND start_at <= ? AND end_at >= ?
           ORDER BY start_at DESC LIMIT 1''',
        (staff_id, dt.isoformat(timespec='seconds'), dt.isoformat(timespec='seconds')),
    )
    return rows[0] if rows else None


def allowed_until_for_signin(staff_id: int | None = None, dt: datetime | None = None) -> tuple[datetime, str]:
    dt = dt or now_local()
    if is_business_hours(dt):
        return dt.replace(hour=BUSINESS_END.hour, minute=BUSINESS_END.minute, second=0, microsecond=0), 'NORMAL'
    if staff_id:
        booking = get_active_booking(staff_id, dt)
        if booking:
            return datetime.fromisoformat(booking['end_at']), 'BOOKED_EXTENDED'
    return dt + timedelta(minutes=AFTER_HOURS_LIMIT_MINUTES), 'AFTER_HOURS_15_MIN'


def fmt_dt(value: str | None) -> str:
    if not value:
        return '-'
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%d %b %Y %I:%M %p')
    except ValueError:
        return value


def parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def building_status(open_staff_rows) -> tuple[str, str, str]:
    if open_staff_rows:
        first = open_staff_rows[0]
        ext = first['extension'] or 'N/A'
        msg = f"Someone is still in the building. Please wait for staff response or call extension {ext}."
        return 'RED', '#b91c1c', msg
    return 'GREEN', '#15803d', 'Thank you. No one is in the building. Lock doors and arm the alarm.'
