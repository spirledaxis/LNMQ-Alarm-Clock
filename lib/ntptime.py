import time
import socket
import struct
import machine #type: ignore

# The NTP host can be configured at runtime by doing: ntptime.host = 'myhost.org'
host = "time.windows.com"
# The NTP socket timeout can be configured at runtime by doing: ntptime.timeout = 2

timeout = 1

def get_time():
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    finally:
        s.close()
    val = struct.unpack("!I", msg[40:44])[0]

    # 2024-01-01 00:00:00 converted to an NTP timestamp
    MIN_NTP_TIMESTAMP = 3913056000

    # Y2036 fix
    #
    # The NTP timestamp has a 32-bit count of seconds, which will wrap back
    # to zero on 7 Feb 2036 at 06:28:16.
    #
    # We know that this software was written during 2024 (or later).
    # So we know that timestamps less than MIN_NTP_TIMESTAMP are impossible.
    # So if the timestamp is less than MIN_NTP_TIMESTAMP, that probably means
    # that the NTP time wrapped at 2^32 seconds.  (Or someone set the wrong
    # time on their NTP server, but we can't really do anything about that).
    #
    # So in that case, we need to add in those extra 2^32 seconds, to get the
    # correct timestamp.
    #
    # This means that this code will work until the year 2160.  More precisely,
    # this code will not work after 7th Feb 2160 at 06:28:15.
    #
    if val < MIN_NTP_TIMESTAMP:
        val += 0x100000000

    # Convert timestamp from NTP format to our internal format

    EPOCH_YEAR = time.gmtime(0)[0]
    if EPOCH_YEAR == 2000:
        # (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
        NTP_DELTA = 3155673600
    elif EPOCH_YEAR == 1970:
        # (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
        NTP_DELTA = 2208988800
    else:
        raise Exception("Unsupported epoch: {}".format(EPOCH_YEAR))

    return val - NTP_DELTA


def second_sunday_in_march(year):
    weekday = time.gmtime(time.mktime((year, 3, 1, 0, 0, 0, 0, 0)))[6]
    days_to_second_sunday = (6 - weekday + 7) % 7 + 7
    return 1 + days_to_second_sunday

def first_sunday_in_november(year):
    weekday = time.gmtime(time.mktime((year, 11, 1, 0, 0, 0, 0, 0)))[6]
    days_to_first_sunday = (6 - weekday) % 7
    return 1 + days_to_first_sunday

def is_dst_pacific(t):
    """Detect if DST is active for Pacific Time using UTC time tuple."""
    year = t[0]
    utc_sec = time.mktime(t)

    # DST starts: Second Sunday of March at 2:00 AM local time = 10:00 UTC
    dst_start_day = second_sunday_in_march(year)
    dst_start_utc = time.mktime((year, 3, dst_start_day, 10, 0, 0, 0, 0))

    # DST ends: First Sunday of November at 2:00 AM local = 9:00 UTC
    dst_end_day = first_sunday_in_november(year)
    dst_end_utc = time.mktime((year, 11, dst_end_day, 9, 0, 0, 0, 0))

    return dst_start_utc <= utc_sec < dst_end_utc

def settime():
    t = get_time()  # UTC time in seconds
    utc_tuple = time.gmtime(t)

    # Auto-detect DST for Pacific Time
    if is_dst_pacific(utc_tuple):
        offset_hours = -7
    else:
        offset_hours = -8

    # Apply UTC offset
    local_sec = t + offset_hours * 3600
    local_tm = time.gmtime(local_sec)

    # Set RTC (year, month, mday, weekday, hour, minute, second, subsecond)
    rtc_tuple = (
    local_tm[0],  # year
    local_tm[1],  # month
    local_tm[2],  # day
    local_tm[6],  # weekday (0=Mon)
    local_tm[3],  # hour
    local_tm[4],  # minute
    local_tm[5],  # second
    0             # subseconds (usually 0)
)
    
    machine.RTC().datetime(rtc_tuple)

