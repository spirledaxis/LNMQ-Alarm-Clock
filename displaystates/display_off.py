from utime import sleep_ms
from displaystates import aliases
from hardware import Button
import config
import socket
from displaystates.mode import DisplayState
from lib.neotimer import Neotimer
import framebuf #type: ignore
from machine import Pin #type: ignore
import random
class DisplayOff(DisplayState):
    def __init__(self, display_manager, name):
        self.button_map = [Button(config.snd_fx_l, self.exit), Button(config.snze_l, self.toggle_light)]
        self.display_manager = display_manager
        self.sleep_lock = False
        super().__init__(self.button_map, name, display_manager)
        self.battery_icon = framebuf.FrameBuffer(bytearray([0x00, 0x3f, 0x21, 0xe1, 0xe1, 0x21, 0x3f, 0x00]), 8, 8, framebuf.MONO_VLSB)
        self.usb_power = Pin('WL_GPIO2', Pin.IN)
        self.battery_icon_timer = Neotimer(5000)
        self.draw_battery = False
        self.x = 64
        self.y = 32

    def main(self):
        if self.usb_power.value() == 0:
             if not self.display.on:
                self.display.wake()
             self.display.draw_sprite(self.battery_icon, self.x, self.y, w=8, h=8)
        else:
             if self.display.on:
                self.display.sleep()

        if self.battery_icon_timer.repeat_execution():
            self.x = random.randint(0, 120)
            self.y = random.randint(0, 56)

        sleep_ms(50)
        
    def toggle_light(self):
            host = config.server_ip
            path = '/toggle_light'
            addr = socket.getaddrinfo(host, config.server_port)[0][-1]
            s = socket.socket()
            s.connect(addr)
            s.send(b"GET " + path.encode() + b" HTTP/1.1\r\nHost: " +
                   host.encode() + b"\r\nConnection: close\r\n\r\n")
            s.close()

    def exit(self):
        print("on exit")
        self.display.wake()
        self.first_time = True
        # self.display_manager.display_timer.reset() # buttons already do this
        self.display_manager.set_active_state(aliases.home)

