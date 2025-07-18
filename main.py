"""the main file. Controls all componets of this project:
Motor
Display
Internet
Input
Speaker
"""
#imports
from machine import Pin, RTC, SPI #type: ignore
from lib.neotimer import Neotimer
from components import Motor
import lib.timeutils as timeutils
from lib.picodfplayer import DFPlayer
from xglcd_font import XglcdFont
from lib.ssd1309 import Display
from utime import sleep_ms #type: ignore
import framebuf #type: ignore
import config
from components import Alarm
from displaystates import *
import json
#init
#remove ntp time calls for testing
#from lib.ntptime import settime
#settime()
rtc = RTC()

#motor setup
motor = Motor(config.motor_l, config.motor_r, 2000)
custom_movement = [
    ('r', 500, 90),   # move right for 0.5s at 90% speed
    ('w', 200, 0),    # wait for 0.2s
    ('l', 700, 100),  # move left for 0.7s at full speed
    ('w', 300, 0),    # wait for 0.3s
    ('r', 300, 85),   # move right for 0.3s at 85%
    ('l', 300, 85),   # move left for 0.3s at 85%
    ('w', 100, 0),    # short wait
    ('r', 1000, 95),  # long move right for 1s at 95%
    ('l', 1000, 95),  # long move left for 1s at 95%
    ('w', 500, 0),    # wait half a second
    ('r', 400, 80),   # final right move for 0.4s at 80%
]
run_motor = Neotimer(5000+motor.movement_len_ms(custom_movement))

#speaker setup
run_speaker = Neotimer(15000)
speaker = DFPlayer(config.uarto_channel_df, config.tx, config.rx, config.busy, config.transistor)

#alarm setup
def alarm_callback():
    print("the alarm went off!")
    speaker.playTrack(1, 1)

alarm = Alarm(12, 19, alarm_callback)
run_alarm = Neotimer(2000)
mode = 'set_alarm'

#region alm setup

global alm_cmd
alm_cmd = None
def on_alm_set():
    alm_cmd = 'alm_set'
def on_fwd():
    alm_cmd = 'fwd'
def on_rev():
    alm_cmd = 'rev'
def on_clk_select():
    alm_cmd = 'ampm'
def on_exit():
    alm_cmd = 'exit'
def on_snd_fx_r():
    alm_cmd = 'select'
alm_buttons = [
    Button(config.alm_set, on_alm_set),
    Button(config.fwd, on_fwd),
    Button(config.rev, on_rev),
    Button(config.clk_set, on_clk_select),
    Button(config.snze, on_exit),
    Button(config.snd_fx_r, on_snd_fx_r)
]
firsttime_alm = True
#endregion


try:
    while True:
        if mode == 'home':

            home()
        elif mode == 'set_alarm':
            if firsttime_alm:
                with open('alarms.json', 'r') as f:
                    alarms = json.load(f)
                with open('ringtones.json', 'r') as f:
                    ringtone_json = json.load(f)

                alarms = alarms[0] 
                alarm_hour = alarms['hour']
                alarm_minute = alarms['minute']
                alarm_ampm = alarms['ampm']
                ringtone_index = alarms['ringtone']
                firsttime_alm = False
            
            for btn in alm_buttons:
                btn.update()

            hour, minute, ampm, ringtone_index, blinking, exit_alm = set_alarm(
                alarm_hour, alarm_minute, alarm_ampm, ringtone_index, ringtone_json, "minute", alm_cmd)

            alm_cmd = None
            if exit_alm:
                mode = 'home'
                firsttime_alm = True
finally:
    print("doing cleanup")
    speaker.cleanup()
    display.cleanup()
    motor.stop()

