import errno
import json

import config
import utils.motd_parser as motd_parser
from bigicons import *
from hardware import display
from .http_get import http_get
from utils import make_icon
import time

def fetch_cache():
    booticon_warning = make_icon(booticon_warning, 128, 64)
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
            display.draw_sprite(booticon_warning, x=0, y=0, w=128, h=64)
            display.present(time.sleep(5))
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
            display.draw_sprite(booticon_warning, x=0, y=0, w=128, h=64)
            display.present()
            time.sleep(5)
            print("timed out while getting alarm message")
        else:
            raise
