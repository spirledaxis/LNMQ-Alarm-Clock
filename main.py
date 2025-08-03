"""the main file. Controls all componets of this project:
Motor
Display
Internet
Input
Speaker
"""
#imports
from machine import Pin, RTC, SPI #type: ignore
from utime import sleep_ms #type: ignore
import urequests #type: ignore
import errno
from components import Motor, Alarm, Switch, Button
from lib.neotimer import Neotimer
import lib.timeutils as timeutils
from lib.picodfplayer import DFPlayer
from lib.ntptime import settime
from motds import motd_parser
from connect import check_connection
from displaystates import bally_mini, display
from motds import motd_reciever_copy_2
import connect
import config
import displaystates
import json

#motor setup
motor = Motor(config.motor_l, config.motor_r, 2000)
custom_movement = [
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
    ('r', 1000, 90),   # move right for 0.5s at 90% speed
    ('w', 500, 0),    # wait for 0.2s
    ('l', 1000, 90),  # move left for 0.7s at full speed
]

speaker = DFPlayer(config.uarto_channel_df, config.tx, config.rx, config.busy, config.transistor)


alm_cmd = None
def make_set_alm_cmd(val):
    def handler():
        global alm_cmd
        alm_cmd = val
    return handler

home_cmd = None
def make_set_home_cmd(val):
    def handler():
        global home_cmd
        home_cmd = val
    return handler

alm_buttons = [
    Button(config.fwd, make_set_alm_cmd('fwd')),
    Button(config.rev, make_set_alm_cmd('rev')),
    Button(config.alm_set, make_set_alm_cmd('exit')),
    Button(config.snd_fx_l, make_set_alm_cmd('selection'))
]
home_buttons = [
    Button(config.alm_set, make_set_home_cmd('goto_alarm')),
    Button(config.snze_l, make_set_home_cmd('toggle_light')),
    Button(config.fwd, make_set_home_cmd('read_msg')),
    Button(config.snd_fx_l, make_set_home_cmd('toggle_display'))
]
firsttime_alm = True

with open('motds.json', 'r') as f:
    motds_data = json.load(f)

with open('alarms.json', 'r') as f:
    alarm = json.load(f)
    alarm = alarm[0]
    alarm_hour = int(alarm['hour'])
    alarm_minute = int(alarm['minute'])
    alarm_ampm = alarm['ampm']
    alarm_ringtone = alarm['ringtone']

mode = 'home'
display_on = True
scroller = 0
usb_power = Pin('WL_GPIO2', Pin.IN)
switch = Switch(config.switch)

myalarm = Alarm(alarm_hour, alarm_minute, custom_movement, alarm_ringtone, motor, speaker)
refresh_time_cooldown_timer = Neotimer(0)
refresh_time_cooldown_timer.start()

motd_done = False
motd = motd_parser.select_random_motd(motds_data)
motd = motd['motd']
motd_len = bally_mini.measure_text(motd)
s, clients = motd_reciever_copy_2.web_setup()
new_motds = []
for motd_json in motds_data:
    if motd_json['new'] is True:
        print('found an new motd')
        print('appending', motd_json)
        new_motds.append(motd_json)
        print('new motds', new_motds)

rtc = RTC()
connect.do_connect()
settime()

try:    
    while True:
        now = rtc.datetime()
        #webserver
        new_motd = motd_reciever_copy_2.web_server(s, clients)
        if new_motd is not None:
            new_motds.append(new_motd)

        #handle alarm
        if switch.get_state() and mode == 'home':
            myalarm.update(now)

        if myalarm.is_active:
            display_on = True

        #ntp
        hour = now[4]
        minute = now[5]
        if hour == 2+12 and minute == 5 and refresh_time_cooldown_timer.finished():
            print("setting time via ntp...")
            settime()
            refresh_time_cooldown_timer = Neotimer(70_000)
            refresh_time_cooldown_timer.start()

        switch.update()
        if mode == 'home':
            for btn in home_buttons:
                btn.update()

            if home_cmd == 'toggle_light' and myalarm.is_active:
                myalarm.stop()
                home_cmd = None
                continue

            elif home_cmd == 'toggle_light':
                print("toggling light...")
                try:
                    response = urequests.get('http://192.168.1.45/toggle_light')
                except OSError as e:
                    print("sending GET request failed")
                try:
                    response = response.text()
                except OSError as e:
                    if e.errno == errno.ECONNRESET:
                        print("reading response failed")
                else:
                    response.close()  

            elif home_cmd == 'goto_alarm':
                mode = 'set_alarm'
                display_on = True

            elif home_cmd == 'toggle_display':
                display_on = not display_on
                if display_on == True:
                    display.wake()
                else:
                    display.sleep()
                
            if home_cmd == 'read_msg' and len(new_motds) != 0:
                with open('motds.json', 'r') as f:
                    all_motds = json.load(f)

                for motd in all_motds:
                    print(new_motds)
                    if motd['id'] == new_motds[0]['id']:
                        motd['new'] = False
                        break

                motd = new_motds[0]
                new_motds.pop(0)
                motd = motd['motd']
                motd_len = bally_mini.measure_text(motd)
                scroller = 0
                
                with open('motds.json', 'w') as f:
                    json.dump(all_motds, f)

            if motd_done:
                print("motd done, selecting random one")
                motd = motd_parser.select_random_motd(motds_data)
                motd = motd['motd']
                motd_len = bally_mini.measure_text(motd)

            scroller += 1
            if scroller >= motd_len + display.width + 10:
                motd_done = True
                scroller = 0
            else:
                motd_done = False

            if len(new_motds) != 0:
                display_mail = True
            else:
                display_mail = False

            displaystates.home(usb_power(), switch.get_state(), check_connection(), display_mail, motd, scroller, now)
        
            home_cmd = None

        elif mode == 'set_alarm':
            if firsttime_alm:
                with open('alarms.json', 'r') as f:
                    alarm = json.load(f)
                with open('ringtones.json', 'r') as f:
                    ringtone_json = json.load(f)
                alarm = alarm[0]
                alarm_hour = int(alarm['hour'])
                alarm_minute = int(alarm['minute'])
                alarm_ampm = alarm['ampm']
                ringtone_index = alarm['ringtone']
                select_hm = 'minute'
                firsttime_alm = False

            for btn in alm_buttons:
                btn.update()

            alarm_hour, alarm_minute, alarm_ampm, ringtone_index, select_hm, exit_alm = displaystates.set_alarm(
                alarm_hour, alarm_minute, alarm_ampm, ringtone_index, ringtone_json, select_hm, alm_cmd)

            alm_cmd = None
            if exit_alm:
                mode = 'home'
                firsttime_alm = True
                alarm_hour = timeutils.to_military_time(alarm_hour, alarm_ampm)
                myalarm.edit_time(alarm_hour, alarm_minute)
                myalarm.edit_ringtone(ringtone_index)

finally:
    print("doing cleanup")
    speaker.cleanup()
    displaystates.display.cleanup()
    motor.stop()
    print("cleanup success!")
