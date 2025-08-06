import lib.timeutils as timeutils
from machine import RTC, SPI, Pin, I2C #type: ignore
import framebuf #type: ignore
import config
from lib.ssd1309 import Display
from lib.xglcd_font import XglcdFont
import json

rtc = RTC()
bell_icon = bytearray([0x03, 0x0c, 0x10, 0xe1, 0xe1, 0x10, 0x0c, 0x03])
plug_icon = bytearray([0x00, 0x10, 0xf8, 0x1f, 0x1f, 0xf8, 0x10, 0x00])
battery_icon = bytearray([0x00, 0x3f, 0x21, 0xe1, 0xe1, 0x21, 0x3f, 0x00])
wifi_icon = bytearray([0x00, 0xff, 0x00, 0x3f, 0x00, 0x0f, 0x00, 0x03])
no_wifi_icon = bytearray([0x00, 0xff, 0x00, 0x3f, 0x00, 0xaf, 0x40, 0xa3])
mail_icon = bytearray([0xff, 0xa1, 0x91, 0x8d, 0x8d, 0x91, 0xa1, 0xff])

bell_icon_fb = framebuf.FrameBuffer(bell_icon, 8, 8, framebuf.MONO_VLSB)
plug_icon = framebuf.FrameBuffer(plug_icon, 8, 8, framebuf.MONO_VLSB)
battery_icon = framebuf.FrameBuffer(battery_icon, 8, 8, framebuf.MONO_VLSB)
wifi_icon = framebuf.FrameBuffer(wifi_icon, 8, 8, framebuf.MONO_VLSB)
no_wifi_icon = framebuf.FrameBuffer(no_wifi_icon, 8, 8, framebuf.MONO_VLSB)
mail_icon = framebuf.FrameBuffer(mail_icon, 8, 8, framebuf.MONO_VLSB)

#origin in bottom right
spi = SPI(config.spi_channel_disp, baudrate=10_000_000, sck=Pin(config.sck), mosi=Pin(config.sda))
display = Display(spi, dc=Pin(config.dc), cs=Pin(config.cs), rst=Pin(config.res), offscreen_warnings=False, flip=True)
# i2c = I2C(1, sda=Pin(14), scl=Pin(15), freq=400_000)
# display = Display(i2c=i2c, offscreen_warnings=True)
print("Loading fonts.  Please wait.")
timefont = XglcdFont('Proxy24x31.c', 24, 31)
bally = XglcdFont('Bally7x9.c', 7, 9)
now = rtc.datetime()

motd = 'hello world!'

motd_len = bally.measure_text(motd)
scroller = 0
display.set_contrast(0)

def home(usb_power, switch_state, wifi_state, display_mail, motd, motd_pos, now):
    assert type(motd) is str
  
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

    #icons
    if switch_state:
        display.draw_sprite(bell_icon_fb, x=((display.width-time_len) // 4)+4, y=(display.height // 2) + 4, w=8, h=8)
    else:
        display.fill_rectangle(x=((display.width-time_len) // 4)-4, y=(display.height // 2) + 4, w=8, h=8, invert=True)
    
    if usb_power:
        display.draw_sprite(plug_icon, x=((display.width-time_len) // 4) + 4, y=(display.height // 2) - 8, w=8, h=8)
    else:
        display.draw_sprite(battery_icon, x=((display.width-time_len) // 4) + 4, y=(display.height // 2) - 8 , w=8, h=8)
    
    if wifi_state:
        display.draw_sprite(wifi_icon, x=((display.width-time_len) // 4) - 8, y=(display.height // 2) + 4, w=8, h=8)
    else:
        display.draw_sprite(no_wifi_icon, x=((display.width-time_len) // 4) - 8, y=(display.height // 2) + 4, w=8, h=8)
    
    if display_mail:
        display.draw_sprite(mail_icon, x=((display.width-time_len) // 4) - 8, y=(display.height // 2) - 8, w=8, h=8)
    else:
        display.fill_rectangle(x=((display.width-time_len) // 4) - 8, y=(display.height // 2) - 8, w=8, h=8, invert=True)

    #motd
    display.draw_text(motd_pos, ((display.height // 2) + time_height // 2) + bally.height // 2 - 2,
                    motd, bally, rotate=180)
    
    display.present()
    
   
edit_options = ['hour', 'minute', 'ampm', 'ringtone']
edit_index = 0
    
def set_alarm(hour, minute, ampm, ringtone_index, ringtone_json, selection, action):
    global edit_index
    assert type(minute) is int
    assert type(hour) is int
    if action == 'exit':
        data = [{
            "hour": hour,
            "minute": minute,
            "ampm": ampm,
            "ringtone": ringtone_index
        }]
        with open('alarms.json', 'w') as f:
            json.dump(data, f)
        return hour, minute, ampm, ringtone_index, selection, True

    elif action == 'fwd':
        if selection == 'minute':
            if minute + 5 >= 60:
                minute = 0
            else:
                minute += 5
        elif selection == 'hour':
            if hour + 1 > 12:
                hour = 1
            else:
                hour += 1
        elif selection == 'ringtone':
            ringtone_index += 1
            with open('ringtones.json', 'r') as f:
                data = json.load(f)
                    
            for i in data:
                if int(i['index']) == ringtone_index:
                    ringtone_text = i['description']
                    break
            else:
                ringtone_index = 1

    elif action == 'rev':
        if selection == 'minute':
            if minute - 5 <= 0:
                minute = 55
            else:
                minute -= 5
        elif selection == 'hour':
            if hour - 1 <= 0:
                hour = 12
            else:
                hour -= 1

        elif selection == 'ringtone':
            ringtone_index -= 1
            with open('ringtones.json', 'r') as f:
                data = json.load(f)
                
            highest_index = data[-1]['index']

            for i in data:
                if int(i['index']) == ringtone_index:
                    ringtone_text = i['description']
                    break
            else:
                ringtone_index = highest_index
    
    elif action == 'selection':

        print("selecting")
        edit_index = (edit_index + 1) % len(edit_options)
        selection = edit_options[edit_index]
    
    if action == 'fwd' or action == 'rev':
        if selection == 'ampm':
            if ampm == 'am':
                ampm = 'pm'
            elif ampm == 'pm':
                ampm = 'am'

    time_display = f"{hour}:{minute:02} {ampm}"

    time_height = timefont.height
    time_len = timefont.measure_text(time_display)

    #origin of text drawing
    x = (display.width+time_len) // 2
    y = display.height // 2 - time_height // 2

    hour = str(hour)
    minute = f"{minute:02}"
    hour_len = timefont.measure_text(hour)
    colon_len = timefont.measure_text(":") 
    minute_len = timefont.measure_text(minute)
    ampm_len = timefont.measure_text(ampm)
    space_len = timefont.measure_text(' ')
    #idk if draw_text adds a space at the end, may become offset
  
    display.fill_rectangle(0, 0, display.width, display.height, True)
    display.draw_text(x, y, time_display, timefont, rotate=180)
    
    ringtone_text = f"{ringtone_index}. {ringtone_json[ringtone_index-1]['description']}"
    ringtone_y = display.height // 2 + time_height // 2 + bally.height // 2
    display.draw_text((display.width + time_len) // 2, ringtone_y,
                ringtone_text, bally, rotate=180)
    
    if selection == 'hour':
        display.draw_hline(x - hour_len, y-3, hour_len)
        display.draw_hline(x - hour_len - colon_len - minute_len, y-3, minute_len, invert=True)
    elif selection == 'minute':
        display.draw_hline(x - hour_len - colon_len - minute_len, y-3, minute_len)
        display.draw_hline(x - hour_len, y-3, hour_len, invert=True)
    elif selection == 'ampm':
        display.draw_hline(x - hour_len - colon_len - minute_len - space_len -ampm_len, y-3, ampm_len)
        display.draw_hline(x - hour_len - colon_len - minute_len, y-3, minute_len, invert=True)
    elif selection == 'ringtone':
        display.draw_vline((display.width + time_len) // 2, ringtone_y, bally.height)
        display.draw_hline(x - hour_len - colon_len - minute_len - space_len -ampm_len, y-3, ampm_len, invert=True)

    display.present()
    return int(hour), int(minute), ampm, ringtone_index, selection, False

if __name__ == '__main__':
    firsttime_alm = True
    try:
        while True:
            if firsttime_alm:
                with open('alarms.json', 'r') as f:
                    alarm = json.load(f)
                with open('ringtones.json', 'r') as f:
                    ringtone_json = json.load(f)

                alarm = alarm[0] 
                alarm_hour = alarm['hour']
                alarm_minute = alarm['minute']
                alarm_ampm = alarm['ampm']
                ringtone_index = alarm['ringtone']
                select_hm = 'minute'
                alm_cmd = None
                firsttime_alm = False
                
            alarm_hour, alarm_minute, alarm_ampm, ringtone_index, select_hm, exit_alm = set_alarm(
                alarm_hour, alarm_minute, alarm_ampm, ringtone_index, ringtone_json, select_hm, alm_cmd)

            alm_cmd = None
            if exit_alm:
                mode = 'home'
                firsttime_alm = True
    finally:
        print("doing cleanup")
        display.cleanup()
 