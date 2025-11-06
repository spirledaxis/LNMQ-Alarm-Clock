import gc
import io
import json
import time

import machine  # type: ignore
from machine import RTC, Pin  # type: ignore

import config
import webserver

from bigicons import *
from displaystates import (DisplayOff, Home, MessageViewer, SetAlarm, aliases,
                           mode)
from hardware import display, headlights, motor, speaker
from lib import Neotimer, settime
from utils import (batstats, connect, fetch_cache, http_get, make_icon,
                   motd_parser, tempuratures)
from alarm import Alarm


display.draw_sprite(make_icon(booticon, 128, 64), x=0, y=0, w=128, h=64)
display.present()

try:
    rtc = RTC()
    print(machine.freq())

    wifi = connect.do_connect(0)
    print(connect.check_connection())
    if connect.check_connection() == True:
        print("im good")
        settime()
        fetch_cache()
    else:
        print("im cooked")
        display.draw_sprite(make_icon(booticon_warning, 128, 64), 0, 0, 128, 64)
        display.present()
        time.sleep(5)

    s, clients = webserver.web_setup()

    alarm = Alarm(config.alarm_timeout_min * 60,
                    motor, headlights, speaker)
    # alarm testing
    # myalarm.hour = now[4]
    # myalarm.minute = now[5]

    display_manager = mode.DisplayManager(alarm)
    home = Home(display_manager, aliases.home)
    setalarm = SetAlarm(display_manager, aliases.set_alarm)
    off = DisplayOff(display_manager, aliases.display_off)
    message_reader = MessageViewer(display_manager, home, aliases.message_reader)
    display_manager.display_states = [home, setalarm, off, message_reader]
    display_manager.set_active_state(aliases.home)
    display.set_contrast(0)

    prev_dur = 0
    loopcycles = 0
    lock_ntptime = False

    now = rtc.datetime()
    print(now)

    usb_power = Pin('WL_GPIO2', Pin.IN)
    usb_prev_state = None
    if usb_power.value() == 0:
        wifi.disconnect()
        wifi.active(False)

    while True:
        start = time.ticks_ms()
        displaytimer = time.ticks_ms()
        display_manager.run_current_state()
        display_elapsed = time.ticks_diff(time.ticks_ms(), start)
        now = rtc.datetime()

        # webserver
        webservertimer = time.ticks_ms()
        status = {
            "bell": -1,
            "wifi": -1,
            "battery": -1,
            "mail": home.iconactive_mail,
            "message": home.motd,
            "queue": home.new_motds
        }
        status = json.dumps(status)
        check = webserver.web_server(s, clients, status)
        if check is not None:
            if check[0] == 'motd':
                home.new_motds.append(check[1])
            elif check[0] == 'alarm_msg' and check[1] == 'random':
                with open('alarm.json', 'r') as f:
                    data = json.load(f)

                data['alarm_message'] = motd_parser.select_random_motd(home.motds_data)[
                    'motd']

                with open('alarm.json', 'w') as f:
                    json.dump(data, f)
        webserver_elapsed = time.ticks_diff(time.ticks_ms(), webservertimer)

        # handle alarm
        if display_manager.alarm_active:
            alarm.update(now, home)

        # ntp
        hour = now[4]
        minute = now[5]
        if hour == 2 and minute == 1 and not lock_ntptime and connect.check_connection():
            lock_ntptime = True
            try:
                settime()
            except Exception:
                print("couldn't set the time via ntp")
            else:
                print("setting time via ntp and fetching cache")
            try:
                fetch_cache()
            except Exception:
                print("couldn't fetch the cache")
            else:
                print("fetched cache")

        elif minute != 1:
            lock_ntptime = False

        if usb_power.value() == 0 and usb_prev_state == 1:
            wifi.disconnect()
            wifi.active(False)
        elif usb_power.value() == 1 and usb_prev_state == 0:
            connect.do_connect()

        usb_prev_state = usb_power.value()

        loopcycles += 1
        if loopcycles >= 50:
            loopcycles = 0
            gc.collect()

        # debug stuff
        dur = display_manager.display_timer.get_remaining()
        done = display_manager.display_timer.finished()
        cycle_time = time.ticks_diff(time.ticks_ms(), start)
        print(f"cycle: {cycle_time}, display: {display_elapsed}, web: {webserver_elapsed}, clock: {machine.freq()/1_000_000}, adc: {batstats.read_bat_voltage()}, mem: {gc.mem_free()/1000} KB, internal temp: {tempuratures.get_internal_temp()}", end="\r")
        home.looptime = cycle_time

except Exception as e:
    # TODO: add emergency alarm
    speaker.cleanup()
    motor.stop()
    import sys
    sys.print_exception(e)
    print("there was an error")
    try:
        print("attempting to connect to server to log error")
        buf = io.StringIO()
        sys.print_exception(e, buf)
        tb_str = buf.getvalue()
        tb_str = tb_str.replace(" ", "+")
        buf.close()
        status = http_get(config.server_ip,
                          config.server_port, f'/?error={tb_str}')
        print(status)
        if status == 'Error recieved':
            print("server recived the error")
    except BaseException:
        print("could not log to server, it'll be saved on the pico")

    finally:
        with open('errors.txt', 'a') as f:
            sys.print_exception(e, f)
            f.write(f'\n{rtc.datetime()}\n')

        print("saved error to pico")


    display.draw_sprite(make_icon(booticon_warning, 128, 64), x=0, y=0, w=128, h=64)
    display.present()
    timer = Neotimer(config.bsod_timeout_s * 1000)
    timer.start()

    while not timer.finished():
        time.sleep_ms(100)

finally:
    print("doing cleanup")
    speaker.cleanup()
    display.cleanup()
    motor.stop()
    headlights.stop()
    stop_threads = True
    print("cleanup success!")
