import errno
import json
import time

import framebuf  # type: ignore
import network  # type: ignore
from machine import RTC, Pin  # type: ignore

import config
from hardware import Button
from lib import Neotimer, ntptime
from utils import (batstats, make_icon, motd_parser, tempuratures, timeutils,
                   toggle_smartswitch)

from . import aliases
from .fonts import bally, bally_mini, timefont
from .mode import DisplayState


class Home(DisplayState):
    def __init__(self, display_manager, name):
        self.button_map = [
            Button(config.alm_set, self.on_alm_set),
            Button(config.snze_l, self.on_snze),
            Button(config.fwd, self.on_fwd),
            Button(config.rev, self.on_rev),
            Button(config.snd_fx_l, self.on_snd_sfx),
            Button(config.clk_set, self.on_clk)
        ]
        super().__init__(self.button_map, name, display_manager)
        self.display_manager = display_manager
        self.motd = ''
        self.motd_queue = []
        self.prev_motd = ''
        self.motd_dir = 'l'
        self.motd_mode = 'scroll'
        self.bounce_firstime = True

        with open('motds.json', 'r') as f:
            motds_data = json.load(f)
        self.motds_data = motds_data
        self.motd_queue = motds_data[:]
        print("id(motds_data) =", id(self.motds_data))
        print("id(motd_queue) =", id(self.motd_queue))

        self.new_motds = []
        self.reset_motd()
        for motd_json in motds_data:
            if motd_json['new'] is True:
                print('found an new motd')
                print('appending', motd_json)
                self.new_motds.append(motd_json)
                print('new motds', self.new_motds)

        self.usb_power = Pin('WL_GPIO2', Pin.IN)
        self.rtc = RTC()
        self.alarm = display_manager.alarm
        self.time_len = 0

        self.bell_icon_fb = make_icon(
            [0x03, 0x0c, 0x10, 0xe1, 0xe1, 0x10, 0x0c, 0x03])
        self.bell_icon_off = make_icon(
            [0x03, 0x0d, 0x13, 0xe6, 0xec, 0x18, 0x3c, 0x23])
        self.snooze_icon = make_icon(
            [0xc1, 0xe1, 0xf1, 0xb9, 0x9d, 0x8f, 0x87, 0x83])
        self.plug_icon = make_icon(
            [0x00, 0x10, 0xf8, 0x1f, 0x1f, 0xf8, 0x10, 0x00])
        self.battery_icon = make_icon(
            [0x00, 0x3f, 0x21, 0xe1, 0xe1, 0x21, 0x3f, 0x00])
        self.wifi_icon = make_icon(
            [0x00, 0xff, 0x00, 0x3f, 0x00, 0x0f, 0x00, 0x03])
        self.no_wifi_icon = make_icon(
            [0x00, 0xff, 0x00, 0x3f, 0x00, 0xaf, 0x40, 0xa3])
        self.mail_icon = make_icon(
            [0xff, 0xa1, 0x91, 0x8d, 0x8d, 0x91, 0xa1, 0xff])
        self.sleep_icon = make_icon(
            [0x40, 0x20, 0x42, 0x05, 0x42, 0x20, 0x40], 7, 7)
        self.degree_symbol = make_icon([0x02, 0x05, 0x02], 3, 3)

        self.blink_wifi_max = config.blink_wifi_max
        self.blinked_wifi = 0
        self.blink_wifi = False
        self.blink_wifi_inverval = Neotimer(config.blink_nowifi_ms)

        self.looptime = 0
        self.offset_val = -6
        self.offset = 0
        self.apply_offset = False

        self.iconactive_bell = False
        self.iconactive_wifi = False
        self.iconactive_battery = False
        self.iconactive_mail = False
        self.v_battery = 0

    def on_rev(self):
        if self.motd_mode == 'scroll':
            with open('alarm.json', 'r') as f:
                data = json.load(f)
                self.motd = data['alarm_message']
                self.motd_mode = 'bounce'
        elif self.motd_mode == 'bounce':
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
            self.motd_mode = 'scroll'

    def on_alm_set(self):
        self.blink_wifi = False
        self.blinked_wifi = 0
        self.display_manager.set_active_state(aliases.set_alarm)

    def on_snd_sfx(self):
        if self.alarm.is_active:
            self.alarm.stop()
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
            self.motd_mode = 'scroll'
        else:
            self.blink_wifi = False
            self.blinked_wifi = 0
            self.display_manager.set_active_state(aliases.display_off)

    def on_fwd(self):

        if len(self.new_motds) == 0:
            self.motd_pos += config.scroll_on_fwd
            self.motd_pos_noadj += config.scroll_on_fwd
        else:
            print("reading message")
            with open('motds.json', 'r') as f:
                all_motds = json.load(f)

            for motd in all_motds:
                # set the read motd to new: false
                if motd['id'] == self.new_motds[0]['id']:
                    print(motd, motd['id'], self.new_motds[0])
                    print("marked motd as read")
                    motd['new'] = False
                    break
            else:
                raise ValueError(
                    "something went wrong when reading the message")

            motd = self.new_motds[0]
            motd = f"{motd['motd']} @{motd['author']}"

            self.reset_motd(motd)
            self.motd_queue.append(self.new_motds[0])
            self.new_motds.pop(0)

            # update the json file so it says new: false
            with open('motds.json', 'w') as f:
                json.dump(all_motds, f)

            # then, reload the data
            with open('motds.json', 'r') as f:
                self.motds_data = json.load(f)

            
    def on_snze(self):
        if self.alarm.is_active:
            self.alarm.stop(False)
            self.alarm.snooze()
            self.blink_wifi = False
            self.blinked_wifi = 0
            self.display_manager.set_active_state(aliases.display_off)

        else:
            print("turning off light")
            try:
                toggle_smartswitch()
            except OSError as e:
                if e.errno == errno.EHOSTUNREACH:
                    self.blink_wifi = True
                else:
                    raise

    def on_clk(self):
        print("switching state")
        self.blink_wifi = False
        self.blinked_wifi = 0
        self.display_manager.set_active_state(aliases.message_reader)

    def clock(self):
        now = self.rtc.datetime()
        month = now[1]
        month_day = now[2]
        day_name_int = now[3]
        hour = now[4]
        minute = now[5]
        second = now[6]

        hour_ampm, _ = timeutils.convert_to_ampm(hour)
        time_text = f'{hour_ampm}:{minute:02}'
        self.time_len = timefont.measure_text(time_text)

        self.time_len = timefont.measure_text(time_text)
        date_text = f'{timeutils.daynum_to_daystr(day_name_int)} | {timeutils.monthnum_to_monthstr(month)} {month_day}'
        date_text_len = bally.measure_text(date_text)
        if date_text_len >= 128:
            date_text = f'{timeutils.daynum_to_daystr(day_name_int)} | {timeutils.monthnum_to_monthabbr(month)} {month_day}'
            date_text_len = bally.measure_text(date_text)

        # origin is in the bottom right

        # Display the time
        self.display.draw_text((self.display.width + self.time_len) // 2 + self.offset, self.display.height // 2 - timefont.height // 2,
                               time_text, timefont, rotate=180)

        # display weekday, month, and mday
        self.display.draw_text((self.display.width + date_text_len) // 2, ((self.display.height // 2) - timefont.height // 2) - 10,
                               date_text, bally, rotate=180)

        # display seconds bar
        len_line = int((second / 60) * 127 + 1)
        self.display.draw_hline(127 - len_line, 63, len_line)
        self.display.draw_hline(127 - len_line, 62, len_line)

    def draw_looptime(self):
        # A constant is used in the x so it doesn't jitter
        self.display.draw_text((self.display.width + self.time_len) // 2 + 18 + self.offset, (self.display.height + timefont.height) // 2 - bally_mini.height - 3,
                               f'{self.looptime}', bally_mini, rotate=180)

    def draw_temp(self):
        x = (self.display.width + self.time_len) // 2 + 18 + 10 + self.offset
        y = (self.display.height + timefont.height) // 2 - \
            timefont.height + bally_mini.height
        tempurature = tempuratures.get_ambient_temp()
        tempurature = round(tempurature, 1)
        self.display.draw_text(x, y, f'{tempurature}', bally_mini, rotate=180)
        self.display.draw_sprite(self.degree_symbol,
                                 x -
                                 bally_mini.measure_text(f'{tempurature}') - 5,
                                 y + bally_mini.height // 2,
                                 3, 3)

    def draw_sleep_temp(self):
        now = self.rtc.datetime()
        curr_hour = now[4]
        curr_minute = now[5]

        alarm_hour = self.alarm.hour
        alarm_minute = self.alarm.minute

        # Calculate hours and minutes until alarm
        hours = alarm_hour - curr_hour
        minutes = alarm_minute - curr_minute - config.sleep_offset_min

        # Adjust if minutes are negative
        if minutes < 0:
            minutes += 60
            hours -= 1

        # Adjust if hours are negative (alarm is on the next day)
        if hours < 0:
            hours += 24

        disp_str = f'{hours}:{minutes:02}'
        x = (self.display.width + self.time_len) // 2 + \
            bally_mini.measure_text(disp_str) + self.offset
        y = self.display.height // 2 - timefont.height // 2 + bally_mini.height // 2 + 2
        if (hours <= 8 and minutes <= 30) or hours <= 7:
            self.apply_offset = True
            self.display.draw_text(x, y, disp_str, bally_mini, rotate=180)
            self.display.draw_sprite(self.sleep_icon, x + 2, y + 1, 7, 7)
        else:
            self.draw_temp()

    def reset_motd(self, motd=None):
        if len(self.motd_queue) == 0:
            print("refilling queue")
            self.motd_queue = self.motds_data[:]

        print("motd ququq", self.motd_queue)
        print("motds data", self.motds_data)
        self.motd, self.motd_queue = motd_parser.select_random_motd_queue(self.motd_queue)
        self.motd = self.motd['motd']

                
        if motd:
            self.motd = motd
        self.prev_motd = self.motd
        self.motd_len = bally.measure_text(self.motd)
        self.motd_pos = 0
        self.motd_pos_noadj = 0  # doesn't get subtracted for adjustments
        self.split_motd_add = iter(list(self.motd))
        self.split_motd_remove = iter(list(self.motd))
        self.partial_motd = ''
        self.overshoot_motd = ''
        self.overshot_motd_prev = ''

    def scroll_motd(self):
        """scroll self.motd across the screen.
        Only renders visibible text."""
        # TODO: make it work with the forward button
        if self.motd_pos_noadj >= self.motd_len + self.display.width + 10:
            self.reset_motd()
        else:
            self.motd_pos += config.msg_scroll_speed
            self.motd_pos_noadj += config.msg_scroll_speed
        # builds the motd as it comes from the right
        while bally.measure_text(self.partial_motd) < self.motd_pos:
            try:
                self.partial_motd += next(self.split_motd_add)
            except StopIteration:
                break
        # removes motd past the left edge
        while self.motd_pos_noadj - bally.measure_text(self.overshoot_motd) >= 128 + 10 and self.motd_pos > 128:
            try:
                self.overshoot_motd += next(self.split_motd_remove)

            except StopIteration:
                break
        # apply overshoot
        # if self.overshoot_motd != '':
        #     self.partial_motd = self.motd.replace(self.overshoot_motd, '')
        # subtract motd_pos based on characters removed to keep it smooth
        if self.overshoot_motd != self.overshot_motd_prev:

            self.partial_motd = self.partial_motd[1:]
            overshot_diff = self.overshoot_motd.replace(
                self.overshot_motd_prev, '', 1)
            self.motd_pos -= bally.measure_text(overshot_diff)

        self.display.draw_text(self.motd_pos, ((self.display.height // 2) + timefont.height // 2) + bally.height // 2 - 2,
                               self.partial_motd, bally, rotate=180)

       # print(f"rending '{self.partial_motd}' at {self.motd_pos} overshot = '{self.overshoot_motd}'", end='\r')
        self.overshot_motd_prev = self.overshoot_motd

    def bounce_motd(self):
        if self.bounce_firstime:
            self.motd_pos = 120
            self.bounce_firstime = False
        motd_len = bally.measure_text(self.motd)
        if motd_len <= self.display.width:
            self.motd_pos = self.display.width // 2 + motd_len // 2

        elif motd_len > self.display.width:
            if self.motd_pos - motd_len > 0:
                # we saw the entire message going to the left
                self.motd_dir = 'r'
            elif self.motd_pos < 128:
                # we saw the entire message going to the right
                self.motd_dir = 'l'

            if self.motd_dir == 'r':
                self.motd_pos -= config.msg_scroll_speed
            elif self.motd_dir == 'l':
                self.motd_pos += config.msg_scroll_speed

        self.display.draw_text(self.motd_pos, ((self.display.height // 2) + timefont.height // 2) + bally.height // 2 - 2,
                               self.motd, bally, rotate=180)

    def draw_icons(self):
        now = self.rtc.datetime()
        x1 = ((self.display.width - self.time_len) // 4) + 4 + self.offset
        x2 = ((self.display.width - self.time_len) // 4) - 8 + self.offset

        # define vertical positions
        y1 = (self.display.height // 2) - 8  # top row (battery, mail)
        y2 = (self.display.height // 2) + 4  # bottom row (bell, wifi)

        # Alarm bell icon
        if self.display_manager.alarm_active and self.alarm.snoozed == False:
            self.iconactive_bell = True
            self.display.draw_sprite(self.bell_icon_fb, x=x1, y=y2, w=8, h=8)
        elif self.display_manager.alarm_active and self.alarm.snoozed:
            self.iconactive_bell = True
            self.display.draw_sprite(self.snooze_icon, x=x1, y=y2, w=8, h=8)
        else:
            self.iconactive_bell = False
            self.display.draw_sprite(self.bell_icon_off, x=x1, y=y2, w=8, h=8)

        # Power and battery icons
        if self.usb_power.value() == 1:
            self.iconactive_battery = False
            self.display.draw_sprite(self.plug_icon, x=x1, y=y1, w=8, h=8)
        elif now[6] % 2 == 0:
            self.iconactive_battery = True
            self.display.draw_sprite(
                batstats.get_bat_sprite(), x=x1, y=y1, w=8, h=8)

        # WiFi icons
        if network.WLAN(network.WLAN.IF_STA).isconnected():
            self.iconactive_wifi = True
            self.display.draw_sprite(self.wifi_icon, x=x2, y=y2, w=8, h=8)
        elif self.blink_wifi_inverval.repeat_execution() and self.blink_wifi:
            self.blinked_wifi += 1
            if self.blinked_wifi >= self.blink_wifi_max:
                self.blinked_wifi = 0
                self.blink_wifi = False
        else:
            self.iconactive_wifi = False
            self.display.draw_sprite(self.no_wifi_icon, x=x2, y=y2, w=8, h=8)

        # Mail icon
        if len(self.new_motds) != 0:
            self.iconactive_mail = True
            self.display.draw_sprite(self.mail_icon, x=x2, y=y1, w=8, h=8)
        else:
            self.iconactive_mail = False
            self.display.fill_rectangle(x=x2, y=y1, w=8, h=8, invert=True)

    def dst_warning(self):
        hour = self.rtc.datetime()[4]
        hour, _ = timeutils.convert_to_ampm(hour)
        arrow_len = timefont.measure_text(str(hour))
        arrow_x = ((self.display.width + self.time_len) // 2) - \
            arrow_len + self.offset
        arrow_y = self.display.height // 2 - timefont.height // 2
        if ntptime.dst_change_soon_pacific(self.rtc.datetime()) == 1:
            self.display.draw_hline(arrow_x, arrow_y, arrow_len)
            self.display.draw_pixel(arrow_x - 3, arrow_y)
            self.display.draw_pixel(arrow_x - 2, arrow_y + 1)
            self.display.draw_pixel(arrow_x - 2, arrow_y - 1)
            self.display.draw_pixel(arrow_x - 1, arrow_y + 2)
            self.display.draw_pixel(arrow_x - 1, arrow_y - 2)
        elif ntptime.dst_change_soon_pacific(self.rtc.datetime()) == -1:
            self.display.draw_hline(arrow_x, arrow_y, arrow_len)
            arrow_x = ((self.display.width + self.time_len) // 2)
            self.display.draw_pixel(arrow_x + 3, arrow_y)
            self.display.draw_pixel(arrow_x + 2, arrow_y + 1)
            self.display.draw_pixel(arrow_x + 2, arrow_y - 1)
            self.display.draw_pixel(arrow_x + 1, arrow_y + 2)
            self.display.draw_pixel(arrow_x + 1, arrow_y - 2)

    def main(self):

        self.clock()
        self.draw_sleep_temp()
        self.draw_icons()
        self.draw_looptime()
        self.dst_warning()
        if self.motd_mode == 'scroll':
            self.scroll_motd()
            self.bounce_firstime = True

        elif self.motd_mode == 'bounce':
            self.bounce_motd()

        if self.apply_offset:
            self.offset = self.offset_val
        else:
            self.offset = 0



