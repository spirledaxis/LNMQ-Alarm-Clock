import errno
import random
from time import sleep_ms

import framebuf  # type: ignore
from machine import Pin  # type: ignore

import config
from hardware import Button
from lib import Neotimer
from utils import batstats, toggle_smartswitch

from . import aliases
from .mode import DisplayState


class DisplayOff(DisplayState):
    def __init__(self, display_manager, name):
        self.button_map = [
            Button(config.snd_fx_l, self.exit),
            Button(config.snze_l, self.toggle_light),
        ]

        self.display_manager = display_manager
        self.sleep_lock = False
        super().__init__(self.button_map, name, display_manager)
        self.battery_icon = framebuf.FrameBuffer(bytearray(
            [0x00, 0x3f, 0x21, 0xe1, 0xe1, 0x21, 0x3f, 0x00]), 8, 8, framebuf.MONO_VLSB)
        self.no_wifi_icon = framebuf.FrameBuffer(bytearray(
            [0x00, 0xff, 0x00, 0x3f, 0x00, 0xaf, 0x40, 0xa3]), 8, 8, framebuf.MONO_VLSB)
        self.usb_power = Pin('WL_GPIO2', Pin.IN)
        self.battery_icon_timer = Neotimer(5000)
        self.draw_battery = False
        self.bat_x = 64
        self.bat_y = 32

        self.blink_wifi_max = config.blink_wifi_max
        self.blink_wifi = False
        self.blinked_wifi = 0
        self.blink_wifi_inverval = Neotimer(config.blink_nowifi_ms)

    def main(self):
        if self.usb_power.value() == 0:
            if not self.display.on:
                self.display.wake()
            self.display.draw_sprite(
                batstats.get_bat_sprite(), self.bat_x, self.bat_y, w=8, h=8)
        else:
            if self.display.on and not self.blink_wifi:
                self.display.sleep()

        if self.battery_icon_timer.repeat_execution():
            if self.blink_wifi:
                while self.bat_x > 64 and self.bat_y > 32:  # keep out of q1
                    self.bat_x = random.randint(0, 120)
                    self.bat_y = random.randint(0, 56)
            else:
                self.bat_x = random.randint(0, 120)
                self.bat_y = random.randint(0, 56)

        if self.blink_wifi and self.blink_wifi_inverval.repeat_execution():
            self.blinked_wifi += 1
            if self.blinked_wifi > self.blink_wifi_max - 1:  # idk this fixes a bug
                self.blink_wifi = False
                self.blinked_wifi = 0
        elif self.blink_wifi:
            self.display.draw_sprite(self.no_wifi_icon, 0, 64 - 8, w=8, h=8)

        sleep_ms(50)

    def toggle_light(self):
        try:
            toggle_smartswitch()
        except OSError as e:
            if e.errno == errno.EHOSTUNREACH:
                self.blink_wifi = True
                self.display.wake()
                self.bat_x = 10
                self.bat_y = 64 - 8
            else:
                raise

    def exit(self):
        print("on exit")
        self.display.wake()
        self.first_time = True
        self.blinked_wifi = 0
        self.blink_wifi = False
        # self.display_manager.display_timer.reset() # buttons already do this
        self.display_manager.set_active_state(aliases.home)



