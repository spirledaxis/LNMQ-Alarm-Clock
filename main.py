import io
from machine import Pin  # type: ignore
import gc
import framebuf  # type: ignore
from displaystates import Home, DisplayOff, MessageViewer, SetAlarm, aliases
import errno
from config import display
import json
from hardware import Switch, Motor
from alarm import Alarm
import webserver
import motd_parser
from lib.neotimer import Neotimer
from lib.ntptime import settime
import lib.connect as connect
import displaystates.mode as mode
import socket
import _thread
import time
from machine import RTC  # type: ignore
import framebuf
import config
from bigicons import *
from utime import sleep_ms  # type: ignore

booticon = framebuf.FrameBuffer(
    booticon, 128, 64, framebuf.MONO_VLSB)
config.display.draw_sprite(booticon, x=0, y=0, w=128, h=64)
config.display.present()

stop_threads = False
booticon_warning = framebuf.FrameBuffer(
    booticon_warning, 128, 64, framebuf.MONO_VLSB)

usb_power = Pin('WL_GPIO2', Pin.IN)
usb_prev_state = None

rtc = RTC()


def http_get(host, port, path):
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect(addr)
        # HTTP/1.0 + Host header
        s.send(b"GET %s HTTP/1.0\r\nHost: %s\r\n\r\n" %
               (path.encode(), host.encode()))
        data = b""
        while True:
            chunk = s.recv(128)
            if not chunk:
                break
            data += chunk
        header_end = data.find(b"\r\n\r\n")
        if header_end != -1:
            return data[header_end + 4:].decode()
        return data.decode()
    finally:
        s.close()


def cache_stuff():
    with open('motds.json', 'r') as f:
        motds = json.load(f)
    try:
        cached_motds = http_get(
            config.server_ip, config.server_port, "/fetch_cache")
        cached_motds = json.loads(cached_motds)
        print("Found cached motds!", cached_motds)
        highest_id = motds[-1]["id"]
        new_id = highest_id + 1
        for motd in cached_motds:
            motd['id'] = new_id
            new_id += 1
            motds.append(motd)
        with open('motds.json', 'w') as f:
            json.dump(motds, f)
        http_get(config.server_ip, config.server_port, "/clear_cache")
    except OSError as e:
        if e.errno == errno.ETIMEDOUT or e.errno == errno.ECONNRESET:
            config.display.draw_sprite(booticon_warning, x=0, y=0, w=128, h=64)
            config.display.present()
            print("timed out while getting cached motds")
        else:
            raise

        print("slime me out")
    try:
        new_alarm_msg = http_get(
            config.server_ip, config.server_port, "/fetch_alarm_msg")
        print(new_alarm_msg)
        if new_alarm_msg != '' and new_alarm_msg != '404 Not Found':
            print("got new alarm message")
            with open(f'alarm.json', 'r') as f:
                # print(f.read())
                data = json.load(f)
            data['alarm_message'] = new_alarm_msg

            with open(f'alarm.json', 'w') as f:
                json.dump(data, f)

            http_get(config.server_ip, config.server_port, "/clear_alarm_msg")

        elif new_alarm_msg == 'random':
            with open('alarm.json', 'r') as f:
                data = json.load(f)

            data['alarm_message'] = motd_parser.select_random_motd(motds)[
                'motd']

            with open('alarm.json', 'w') as f:
                json.dump(data, f)
        else:
            print("did not find an alarm message in the cache", new_alarm_msg)
    except OSError as e:
        if e.errno == errno.ETIMEDOUT or e.errno == errno.ECONNRESET:
            config.display.draw_sprite(booticon_warning, x=0, y=0, w=128, h=64)
            config.display.present()
            print("timed out while getting alarm message")
        else:
            raise


try:
    # wifi = connect.do_connect()
    # settime()
    # cache_stuff()
    s, clients = webserver.web_setup()

    switch = Switch(config.switch)

    myalarm = Alarm(config.alarm_timeout_min * 60,
                    config.motor, config.headlights, config.speaker, switch)

    def threads():
        while not stop_threads:
            config.motor.motor_thread_step()
            config.headlights.headlight_thread_step()
            time.sleep_us(1500)

    _thread.start_new_thread(threads, ())
    display_manager = mode.DisplayManager()
    home = Home(display_manager, myalarm, aliases.home)
    alarm = SetAlarm(display_manager, myalarm, aliases.set_alarm)
    off = DisplayOff(display_manager, aliases.display_off)
    message_reader = MessageViewer(
        display_manager, home, aliases.message_reader)
    display_manager.display_states = [home, alarm, off, message_reader]
    display_manager.set_active_state(aliases.home)

    prev_dur = 0
    lock_ntptime = False
    config.display.set_contrast(0)

    # # alarm testing

    # myalarm.hour = now[4]
    # myalarm.minute = now[5]
    now = rtc.datetime()
    print(now)

    if usb_power.value() == 0:
        wifi.disconnect()
        wifi.active(False)

    loopcycles = 0
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
            myalarm.update(now, home)

        # ntp
        hour = now[4]
        minute = now[5]
        if hour == 2 + 12 and minute == 5 and not lock_ntptime:
            lock_ntptime = True
            try:
                settime()
                cache_stuff()
            except Exception:
                print("couldn't set the time and/or fetch cache")
            else:
                print("setting time via ntp and fetching cache")

        elif minute != 5:
            lock_ntptime = False

        if usb_power.value() == 0 and usb_prev_state == 1:
            wifi.disconnect()
            wifi.active(False)
        elif usb_power.value() == 1 and usb_prev_state == 0:
            connect.do_connect()

        usb_prev_state = usb_power.value()
        loopcycles += 1

        gc.collect()

        # debug stuff
        dur = display_manager.display_timer.get_remaining()
        done = display_manager.display_timer.finished()
        cycle_time = time.ticks_diff(time.ticks_ms(), start)
        #print(dur, done, f'{gc.mem_free()/1000} KB')
        #print(
            #f"cycle: {cycle_time}, display: {display_elapsed}, web: {webserver_elapsed}")
        home.looptime = cycle_time

except Exception as e:
    # TODO: add emergency alarm
    config.speaker.cleanup()
    config.motor.stop()
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

    booticon_warning = framebuf.FrameBuffer(
        failicon, 128, 64, framebuf.MONO_VLSB)
    display.draw_sprite(booticon_warning, x=0, y=0, w=128, h=64)
    display.present()
    timer = Neotimer(config.bsod_timeout_s * 1000)
    timer.start()

    while not timer.finished():
        sleep_ms(100)

finally:
    print("doing cleanup")
    config.speaker.cleanup()
    display.cleanup()
    config.motor.stop()
    config.headlights.stop()
    stop_threads = True
    print("cleanup success!")
