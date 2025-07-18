import lib.timeutils as timeutils
from machine import RTC, SPI, Pin, I2C #type: ignore
import framebuf #type: ignore
import config
from lib.ssd1309 import Display
from xglcd_font import XglcdFont
import json
from components import Button
rtc = RTC()
bell_icon = bytearray([0x03, 0x0c, 0x10, 0xe1, 0xe1, 0x10, 0x0c, 0x03])
fb = framebuf.FrameBuffer(bell_icon, 8, 8, framebuf.MONO_VLSB)
#spi = SPI(config.spi_channel_disp, baudrate=10_000_000, sck=Pin(config.sck), mosi=Pin(config.sda))
#display = Display(spi, dc=Pin(config.dc), cs=Pin(config.cs), rst=Pin(config.res), offscreen_warnings=False, flip=True)
i2c = I2C(1, sda=Pin(14), scl=Pin(15), freq=400_000)
display = Display(i2c=i2c, offscreen_warnings=True)
print("Loading fonts.  Please wait.")
timefont = XglcdFont('Proxy24x31.c', 24, 31)
bally = XglcdFont('Bally7x9.c', 7, 9)
bally_mini = XglcdFont('Bally5x8.c', 5, 8)
now = rtc.datetime()

motd = 'hello world!'

motd_len = bally_mini.measure_text(motd)
scroller = 0
def home():
    global scroller

    now = rtc.datetime()
    month = now[1]
    month_day = now[2]
    day_name_int = now[3]
    hour = now[4]
    minute = now[5]
    second = now[6]
    
    hour_ampm, ampm = timeutils.convert_to_ampm(hour)
    time_text = f'{hour_ampm}:{minute:02}'
    time_height = timefont.height
    time_len = timefont.measure_text(time_text)
    #1 is tuesday, supposedely. Idk if the tuple is weird or my function is cooked, thats why theres +1 for now. Fix later.
    date_text = f'{timeutils.daynum_to_daystr(day_name_int+1)} | {timeutils.monthnum_to_monthstr(month)} {month_day}'
    date_text_len = bally.measure_text(date_text)

    #origin is in the bottom right

    #Display the time
    display.fill_rectangle(0, 0, display.width, display.height, True)
    display.draw_text((display.width+time_len) // 2, display.height // 2 - time_height // 2,
                    time_text, timefont, rotate=180)
    
    #display weekday, month, and mday
    display.draw_text((display.width + date_text_len) // 2, ((display.height // 2) - time_height // 2)-10,
                    date_text, bally, rotate=180)
    
    #display seconds bar
    len_line = int((second/60)*127 + 1)
    display.draw_hline(127-len_line, 63, len_line)
    display.draw_hline(127-len_line, 62, len_line)
    display.draw_sprite(fb, x=((display.width-time_len) // 4)-4, y=(display.height // 2) + 4, w=8, h=8)

    
    #motd
    scroller += 1
    display.draw_text(scroller, ((display.height // 2) + time_height // 2) + bally_mini.height // 2 - 2,
                    motd, bally, rotate=180)
    
    if scroller >= motd_len + display.width + 10:
        scroller = 0

    display.present()



def set_alarm(hour, minute, ampm, ringtone_index, ringtone_json, blinking, action):
    if action == 'exit':
        data = {
            "hour": hour,
            "minute": minute,
            "ampm": ampm,
            "ringtone": ringtone_index
        }
        with open('alarms.json', 'w') as f:
            json.dump(data, f)
        return hour, minute, ampm, ringtone_index, blinking, True

    elif action == 'fwd':
        if blinking == 'minute':
            if minute + 5 >= 60:
                minute = 0
            else:
                minute += 5
        elif blinking == 'hour':
            if hour + 1 > 12:
                hour = 1
            else:
                hour += 1

    elif action == 'rev':
        if blinking == 'minute':
            if minute - 5 <= 0:
                minute = 60
            else:
                minute -= 5
        elif blinking == 'hour':
            if hour - 1 <= 0:
                hour = 12
            else:
                hour -= 1

    elif action == 'ampm':
        if ampm == 'am':
            ampm = 'pm'
        else:
            ampm = 'am'

    elif action == 'alm_set':
        if ringtone_index >= len(ringtone_json):
            ringtone_index = 1
        else:
            ringtone_index += 1

    elif action == 'select':
        if blinking == 'hour':
            blinking = 'minute'
        elif blinking == 'minute':
            blinking = 'hour'

    # Return the updated state so your loop can keep track

    time_display = f"{hour}:{minute:02} {ampm}"

    time_height = timefont.height
    time_len = timefont.measure_text(time_display)

    #origin of text drawing
    x = display.width+time_len
    y = display.height // 2 - time_height // 2

    hour = str(hour)
    minute = str(minute)
    hour_len = timefont.measure_text(hour)
    colon_len = timefont.measure_text(":") 
    minute_len = timefont.measure_text(minute)

    #idk if draw_text adds a space at the end, may become offset
    seconds = rtc.datetime()[6]

    if seconds % 2 == 0 and blinking == 'hour':
        display.draw_text(x, y, hour, timefont, rotate=180, invert=True)
    else:
        display.draw_text(x, y, hour, timefont, rotate=180)

    if seconds % 2 == 0 and blinking == 'minute': 
        display.draw_text(x+hour_len, y, ":", timefont, rotate=180, invert=True)
    else:
        display.draw_text(x+hour_len, y, hour, timefont, rotate=180)

    display.draw_text(x, y, hour, timefont, rotate=180)
    display.draw_text(x+hour_len, y, hour, timefont, rotate=180)
    display.draw_text(x+hour_len+colon_len, y, minute, timefont, rotate=180)   
    display.draw_text(x+hour_len+colon_len+minute_len, y, ampm, timefont, rotate=180) 


    #display.fill_rectangle(0, 0, display.width, display.height, True)
    
    ringtone_text = f"{ringtone_index}. {ringtone_json[ringtone_index-1]['description']}"
    display.draw_text((display.width + time_len) // 2, ((display.height // 2) - time_height // 2)-10,
                ringtone_text, bally, rotate=180)
    
    display.present()
    #maybe handle callbacks and buttons outside?
#     return [
#     Button(config.alm_set, on_alm_set),
#     Button(config.fwd, on_fwd),
#     Button(config.rev, on_rev),
#     Button(config.clk_select, on_clk_select),
#     Button(config.snze, exit),
#     Button(config.snd_fx_r, on_snd_fx_r)
# ]
    return hour, minute, ampm, ringtone_index, blinking, False


