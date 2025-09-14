from displaystates.mode import DisplayState, timefont, bally
from components import Button
import config
import motd_parser
from machine import Pin  # type: ignore
import framebuf  # type: ignore
import network  # type: ignore
from lib.neotimer import Neotimer
import json
from displaystates import aliases


class MessageViewer(DisplayState):
    def __init__(self, display_manager, home, name):

        self.button_map = [
            Button(config.fwd, self.on_fwd),
            Button(config.clk_set, self.on_exit),
        ]
        super().__init__(self.button_map, name, display_manager)

        with open('motds.json', 'r') as f:
            motds_data = json.load(f)
        self.motds_data = motds_data
        self.new_motds = []
        for motd_json in motds_data:
            if motd_json['new'] is True:
                print('found an new motd')
                print('appending', motd_json)
                self.new_motds.append(motd_json)
                print('new motds', self.new_motds)

        self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
        self.switch = self.display_manager.switch
        self.home = home
        self.usb_power = Pin('WL_GPIO2', Pin.IN)
        self.spacing = 4 + 8  # add 8 to compensate for the icons
        self.display_manager = display_manager
        self.swap_icons = Neotimer(config.messenger_icon_invert_time_s * 1000)
        self.change_motd = Neotimer(config.messenger_cycle_time_s * 1000)
        self.swap_icons.start()
        self.change_motd.start()

        self.invert = True

        def make_icon(data):
            return framebuf.FrameBuffer(
                bytearray(data), 8, 8, framebuf.MONO_VLSB)
        self.inverted_battery = make_icon(
            [0xff, 0x80, 0xbe, 0x3e, 0x3e, 0xbe, 0x80, 0xff])
        self.inverted_plug = make_icon(
            [0xff, 0xef, 0x07, 0xe0, 0xe0, 0x07, 0xef, 0xff])
        self.inverted_no_wifi = make_icon(
            [0xff, 0x00, 0xff, 0xc0, 0xff, 0x50, 0xbf, 0x5c])
        self.inverted_wifi = make_icon(
            [0xff, 0x00, 0xff, 0xc0, 0xff, 0xf0, 0xff, 0xfc])
        self.inverted_bell = make_icon(
            [0xfc, 0xf3, 0xef, 0x1e, 0x1e, 0xef, 0xf3, 0xfc])
        self.inverted_mail = make_icon(
            [0x00, 0x5e, 0x6e, 0x72, 0x72, 0x6e, 0x5e, 0x00])

        self.drift_range = 5
        self.drift_positive = True
        self.drift_offset = 0
        self.drift_timer = Neotimer(config.messenger_drift_inverval_ms)
        self.drift_timer.start()

    def on_fwd(self):
        self.home.read_msg()
        self.motd = self.home.motd
        self.change_motd.restart()

    def on_exit(self):
        print("exiting the messenger")
        self.display_manager.set_active_state(aliases.home)

    def drift(self):
        if self.drift_positive:
            self.drift_offset += 1

        else:
            self.drift_offset -= 1

        if abs(self.drift_offset) >= self.drift_range:
            self.drift_positive = not self.drift_positive

    def draw_motd(self):
        motd_parts = self.motd.split(' ')
        split_motd = []
        len_text_line = 0
        partial_motd = ''

        for part in motd_parts:
            word_width = bally.measure_text(part + ' ')  # include space
            if len_text_line + word_width <= self.display.width:
                partial_motd += part + ' '
                len_text_line += word_width
            else:
                # save current line before adding the new word
                split_motd.append(partial_motd.rstrip())
                # start new line with current word
                partial_motd = part + ' '
                len_text_line = word_width

        if partial_motd:
            split_motd.append(partial_motd.rstrip())

        biggest_part = ''
        for part in split_motd:
            if len(part) > len(biggest_part):
                biggest_part = part

        num_lines = len(split_motd)
        text_y = (self.display.height // 2 - bally.height // 2) + \
            bally.height // 2 * (num_lines - 1) + self.drift_offset

        for part in split_motd:
            part_len = bally.measure_text(part)
            text_x = self.display.width // 2 + part_len // 2 + self.drift_offset
            self.display.draw_text(text_x, text_y, part, bally, rotate=180)
            text_y -= bally.height

    def draw_icons(self):
        now = self.home.rtc.datetime()
        num_icons = 2
        if self.display_manager.switch.get_state():
            num_icons += 1
        if len(self.home.new_motds) != 0:
            num_icons += 1

        total_width = (num_icons * 8) + ((num_icons - 1) * (self.spacing - 8))
        start_x = (self.display.width - total_width) // 2
        x = start_x + self.drift_offset
        # abs because negatives would make the icons too low
        y = 1 + abs(self.drift_offset)
        padding = 3
        if self.invert:
            self.display.fill_rectangle(self.display.width-start_x+self.drift_offset -
                                        total_width-padding, y, total_width+2*padding, 8, invert=False)
            if self.display_manager.switch.get_state():
                self.display.draw_sprite(
                    self.inverted_bell, x=x, y=y, w=8, h=8)
                x += self.spacing

            if self.usb_power.value() == 1:
                self.display.draw_sprite(
                    self.inverted_plug, x=x, y=y, w=8, h=8)

            elif now[6] % 2 == 0:
                self.display.draw_sprite(
                    self.inverted_battery, x=x, y=y, w=8, h=8)
            x += self.spacing

            if network.WLAN(network.WLAN.IF_STA).isconnected():
                self.display.draw_sprite(
                    self.inverted_wifi, x=x, y=y, w=8, h=8)
                x += self.spacing
            else:
                self.display.draw_sprite(
                    self.inverted_no_wifi, x=x, y=y, w=8, h=8)
                x += self.spacing

            if len(self.home.new_motds) != 0:
                self.display.draw_sprite(
                    self.inverted_mail, x=x, y=y, w=8, h=8)
                x += self.spacing
        else:
            self.display.fill_rectangle(
                0, y, self.display.width, y + 8, invert=True)
            if self.display_manager.switch.get_state():
                self.display.draw_sprite(
                    self.home.bell_icon_fb, x=x, y=y, w=8, h=8)
                x += self.spacing

            if self.usb_power.value() == 1:
                self.display.draw_sprite(
                    self.home.plug_icon, x=x, y=y, w=8, h=8)

            elif now[6] % 2 == 0:
                self.display.draw_sprite(
                    self.home.battery_icon, x=x, y=y, w=8, h=8)
            x += self.spacing

            if network.WLAN(network.WLAN.IF_STA).isconnected():
                self.display.draw_sprite(
                    self.home.wifi_icon, x=x, y=y, w=8, h=8)
                x += self.spacing
            else:
                self.display.draw_sprite(
                    self.home.no_wifi_icon, x=x, y=y, w=8, h=8)
                x += self.spacing

            if len(self.home.new_motds) != 0:
                self.display.draw_sprite(
                    self.home.mail_icon, x=x, y=y, w=8, h=8)
                x += self.spacing

    def main(self):
        self.draw_motd()
        self.draw_icons()
        if self.swap_icons.finished():
            self.invert = not self.invert
            self.swap_icons.restart()
        if self.change_motd.finished():
            self.change_motd
            self.change_motd.restart()
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
        if self.drift_timer.finished():
            print("drifting icons")
            self.drift_timer.restart()
            self.drift()
