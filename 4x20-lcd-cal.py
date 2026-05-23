import requests
import os
from RPLCD.i2c import CharLCD
from time import sleep
from icalendar import Calendar
from recurring_ical_events import of as recurring_of
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from tzlocal import get_localzone

ICSURL = os.environ["LCD_CAL_ICS"]
CLOCK1_TZ = os.getenv("LCD_CAL_CLOCK1_TZ", get_localzone().key)
CLOCK2_TZ = os.getenv("LCD_CAL_CLOCK2_TZ")

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    port=1,
    cols=20,
    rows=4,
    dotsize=8
)

##### Functions #####
def lcd_write_limited_line(str, limit, lineIdx):
    lcd.cursor_pos = (lineIdx, 0)
    lcd.write_string(str[0:limit])

def lcd_write_20(lineIdx, str):
    lcd_write_limited_line(str, 20, lineIdx)

def lcd_write_time_at_zone(lineIdx, zone):
    lcd_write_20(lineIdx, datetime.now(ZoneInfo(zone)).strftime("%H:%M %Z"))

def fetch_calendar():
    response = requests.get(ICSURL)
    response.raise_for_status()
    return Calendar.from_ical(response.text)

def get_next_event(cal):
    now = datetime.now(timezone.utc)
    windowEnd = now + timedelta(days=7)

    events = recurring_of(cal).between(now, windowEnd)
    upcomingEvents = []

    for event in events:
        startRaw = event.get("dtstart").dt
        start = normalize_to_datetime(startRaw)

        if start > now:
            summary = str(event.get("summary"))
            upcomingEvents.append((start, summary))

    if not upcomingEvents:
        return None, None

    upcomingEvents.sort(key=lambda x: x[0])
    return upcomingEvents[0]

def compute_countdown(start_time):
    now = datetime.now(timezone.utc)
    delta = start_time - now

    total_minutes = int(delta.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    countdownMsg = f"{hours}H:{minutes}"
    if len(countdownMsg) < 6 :
        countdownMsg = countdownMsg + "m" # Don't add 'm' if it would rollover to next line

    return countdownMsg

def normalize_to_datetime(dt):
    # dt can be date or datetime
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    elif isinstance(dt, date):
        # Treat all-day events as starting at midnight UTC
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    else:
        raise TypeError(f"Unsupported dt type: {type(dt)}")

def write_whole_lcd(time1, time2, countdown, meetingTitle):
    lcd.cursor_pos = (0,0)
    t2str = f"{time2:<20}" if time2 else ""
    countdownstr = f"Next meeting: {countdown}"
    lcd.write_string(f"{time1:<20}{t2str:<20}{countdownstr:<20}{meetingTitle[:20]}")

##### Functions #####


##### Main #####
prevMinute = -1
while True:
    # Check if minute has changed, skip display update if not
    currentMinute = datetime.now().minute
    if currentMinute == prevMinute:
        continue
    else:
        prevMinute = currentMinute

    # Gather all data before writing to LCD, making the display update cleaner/faster
    time1 = datetime.now(ZoneInfo(CLOCK1_TZ)).strftime("%H:%M %Z")
    time2 = None
    if CLOCK2_TZ:
        time2 = datetime.now(ZoneInfo(CLOCK2_TZ)).strftime("%H:%M %Z")
    startTime, title = get_next_event(fetch_calendar())
    countdown = compute_countdown(startTime)
    if title.startswith("FW: "):
        title = title[4:]

    lcd.clear()
    write_whole_lcd(time1, time2, countdown, title)

    # Finished. Sleep to avoid excessive updates/load/requests
    sleep(.5)
