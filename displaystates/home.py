import config
from hardware import Button
import json
from lib.neotimer import Neotimer
from machine import Pin, RTC  # type: ignore
import framebuf  # type: ignore
import network  # type: ignore
import lib.timeutils as timeutils
import math
import random
import motd_parser
from displaystates.mode import DisplayState, timefont, bally, bally_mini
import socket
from displaystates import aliases
import errno
import time
from lib import tmp117_temp, batvoltage


class Home(DisplayState):
    def __init__(self, display_manager, alarm, name):
        self.button_map = [
            Button(config.alm_set, self.goto_alarm),
            Button(config.snze_l, self.on_snze),
            Button(config.fwd, self.read_msg),
            Button(config.rev, self.on_rev),
            Button(config.snd_fx_l, self.on_snd_sfx),
            Button(config.clk_set, self.on_clk)
        ]
        super().__init__(self.button_map, name, display_manager)

        self.display_manager = display_manager
        self.motd_pos = 0
        self.motd_dir = 'l'
        self.motd = 'hello world'
        self.motd_mode = 'scroll'
        self.bounce_firstime = True

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

        self.usb_power = Pin('WL_GPIO2', Pin.IN)
        self.rtc = RTC()
        self.alarm = alarm
        self.angle = 0
        self.rotate_speed = 6
        self.size = 15
        self.time_len = 0

        def make_icon(data, x=8, y=8):
            return framebuf.FrameBuffer(
                bytearray(data), x, y, framebuf.MONO_VLSB)

        self.bell_icon_fb = make_icon(
            [0x03, 0x0c, 0x10, 0xe1, 0xe1, 0x10, 0x0c, 0x03])
        self.bell_icon_off = make_icon(
            [0x03, 0x0d, 0x13, 0xe6, 0xec, 0x18, 0x3c, 0x23])
        self.snooze_icon = make_icon(
            [0xff, 0x07, 0x0e, 0x1c, 0x38, 0x70, 0xe0, 0xff])
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

        # Battery level icons (8x8)
        self.battery_critical = make_icon(
            [0x00, 0x7f, 0x40, 0xfb, 0xfb, 0x40, 0x7f, 0x00])
        self.battery_full = make_icon(
            [0x00, 0x7f, 0x7f, 0xff, 0xff, 0x7f, 0x7f, 0x00])
        self.battery_L1 = make_icon(
            [0x00, 0x7f, 0x47, 0xc7, 0xc7, 0x47, 0x7f, 0x00])
        self.battery_L2 = make_icon(
            [0x00, 0x7f, 0x47, 0xc7, 0xc7, 0x47, 0x7f, 0x00])
        self.battery_L3 = make_icon(
            [0x00, 0x7f, 0x4f, 0xcf, 0xcf, 0x4f, 0x7f, 0x00])
        self.battery_L4 = make_icon(
            [0x00, 0x7f, 0x5f, 0xdf, 0xdf, 0x5f, 0x7f, 0x00])


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
        time_len = timefont.measure_text(time_text)

        self.time_len = timefont.measure_text(time_text)
        date_text = f'{timeutils.daynum_to_daystr(day_name_int)} | {timeutils.monthnum_to_monthstr(month)} {month_day}'
        date_text_len = bally.measure_text(date_text)
        if date_text_len >= 128:
            date_text = f'{timeutils.daynum_to_daystr(day_name_int)} | {timeutils.monthnum_to_monthabbr(month)} {month_day}'
            date_text_len = bally.measure_text(date_text)

        # origin is in the bottom right

        # Display the time
        self.display.draw_text((self.display.width + time_len) // 2 + self.offset, self.display.height // 2 - timefont.height // 2,
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
        tempurature = tmp117_temp.read_tmp117_temp()
        tempurature = round(tempurature, 1)
        self.display.draw_text(x, y, f'{tempurature}', bally_mini, rotate=180)
        self.display.draw_sprite(
            self.degree_symbol,
            x -
            bally_mini.measure_text(f'{tempurature}') -
            5,
            y +
            bally_mini.height //
            2,
            3,
            3)

    def draw_estimated_sleep(self):
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
            self.apply_offset = False

    def on_rev(self):
        if self.motd_mode == 'scroll':
            with open('alarm.json', 'r') as f:
                data = json.load(f)
                self.motd = data['alarm_message']
                self.motd_mode = 'bounce'
        elif self.motd_mode == 'bounce':
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
            self.motd_mode = 'scroll'

    def scroll_motd(self):
        motd_len = bally.measure_text(self.motd)
        if self.motd_pos >= motd_len + self.display.width + 10:
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
            self.motd_pos = 0
        else:
            self.motd_pos += config.msg_scroll_speed

        self.display.draw_text(self.motd_pos, ((self.display.height // 2) + timefont.height // 2) + bally.height // 2 - 2,
                               self.motd, bally, rotate=180)

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
        elif self.display_manager.alarm_active and self.alarm.snoozed == True:
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
            
            if self.v_battery >= 4.17:
                self.display.draw_sprite(self.battery_full, x=x1, y=y1, w=8, h=8)
            elif self.v_battery >= 4.08:
                self.display.draw_sprite(self.battery_L4, x=x1, y=y1, w=8, h=8)
            elif self.v_battery >= 4.00:
                self.display.draw_sprite(self.battery_L3, x=x1, y=y1, w=8, h=8)
            elif self.v_battery >= 3.92:
                self.display.draw_sprite(self.battery_L2, x=x1, y=y1, w=8, h=8)
            elif self.v_battery >= 3.83:
                self.display.draw_sprite(self.battery_L1, x=x1, y=y1, w=8, h=8)
            else:
                self.display.draw_sprite(self.battery_critical, x=x1, y=y1, w=8, h=8)
        else:
            self.v_battery = batvoltage.read_bat_voltage()
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


    def draw_cube(self):
        # Function to multiply two matrices
        def MatrixMul(matrixA, matrixB):
            # Create a result matrix filled with zeros
            result = [[0 for _ in range(len(matrixB[0]))]
                      for _ in range(len(matrixA))]

            # Perform matrix multiplication
            for row in range(len(matrixA)):
                for col in range(len(matrixB[0])):
                    for k in range(len(matrixB)):
                        result[row][col] += matrixA[row][k] * matrixB[k][col]

            return result

        # Define the cube's vertices
        points = [
            [[-self.size / 2], [self.size / 2], [self.size / 2]],
            [[self.size / 2], [self.size / 2], [self.size / 2]],
            [[self.size / 2], [-self.size / 2], [self.size / 2]],
            [[-self.size / 2], [-self.size / 2], [self.size / 2]],

            [[-self.size / 2], [self.size / 2], [-self.size / 2]],
            [[self.size / 2], [self.size / 2], [-self.size / 2]],
            [[self.size / 2], [-self.size / 2], [-self.size / 2]],
            [[-self.size / 2], [-self.size / 2], [-self.size / 2]],
        ]

        # Function to calculate the X-axis rotation matrix
        def Xrotation(angle):
            radDegree = angle * math.pi / 180  # Convert angle to radians
            return [
                [1, 0, 0],
                [0, math.cos(radDegree), -math.sin(radDegree)],
                [0, math.sin(radDegree), math.cos(radDegree)]
            ]

        # Function to calculate the Z-axis rotation matrix
        def Zrotation(angle):
            radDegree = angle * math.pi / 180  # Convert angle to radians
            return [
                [math.cos(radDegree), -math.sin(radDegree), 0],
                [math.sin(radDegree), math.cos(radDegree), 0],
                [0, 0, 1]
            ]

        # Function to calculate the Y-axis rotation matrix
        def Yrotation(angle):
            radDegree = angle * math.pi / 180  # Convert angle to radians
            return [
                [math.cos(radDegree), 0, math.sin(radDegree)],
                [0, 1, 0],
                [-math.sin(radDegree), 0, math.cos(radDegree)]
            ]

        # Define the connections (edges) between vertices
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # Front face
            (4, 5), (5, 6), (6, 7), (7, 4),  # Back face
            (0, 4), (1, 5), (2, 6), (3, 7),  # Edges connecting front and back
        ]

        # List to store the rotated and projected points
        rotatedPoints = []

        # Rotate and project each point (vertex) in 3D space
        for point in points:
            # Apply X, Y, and Z rotations
            rotated = MatrixMul(Xrotation(self.angle), point)
            rotated = MatrixMul(Yrotation(self.angle), rotated)
            rotated = MatrixMul(Zrotation(self.angle), rotated)

            # Calculate perspective projection
            z = 200 / (200 - rotated[2][0])
            perspective = [
                [z, 0, 0],
                [0, z, 0],
            ]
            # Apply perspective projection
            projected = MatrixMul(perspective, rotated)
            rotatedPoints.append(projected)  # Save the projected point

        # Draw edges between the points
        pointX = int(self.display.width -
                     ((self.display.width - self.time_len) // 4))
        pointY = int(self.display.height // 2 + 2)
        for start, end in connections:
            startPoint = rotatedPoints[start]  # Start vertex
            endPoint = rotatedPoints[end]  # End vertex

            # Displace points to be in the middle of the screen
            startX = int(startPoint[0][0] + pointX)
            startY = int(startPoint[1][0] + pointY)
            endX = int(endPoint[0][0] + pointX)
            endY = int(endPoint[1][0] + pointY)

            # Draw the edge as a line
            self.display.draw_line(startX, startY, endX, endY)
            # Increment the rotation angle for continuous rotation

        self.angle += self.rotate_speed * random.random()
        if self.angle > 360:
            self.angle = 0

    def goto_alarm(self):
        self.blink_wifi = False
        self.blinked_wifi = 0
        self.display_manager.set_active_state(aliases.set_alarm)

    def on_snd_sfx(self):
        if self.alarm.is_active:
            self.alarm.stop()
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
            self.motd_mode = 'scroll'

        self.blink_wifi = False
        self.blinked_wifi = 0
        self.display_manager.set_active_state(aliases.display_off)

    def read_msg(self):
        print("reading message")
        if len(self.new_motds) == 0:
            print("there are no new motds")
            return

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
            print("there are no new motds (2)")
            return

        motd = self.new_motds[0]
        self.motd = f"{motd['motd']} @{motd['author']}"
        self.motd_pos = 0
        self.new_motds.pop(0)

        # update the json file so it says new: false
        with open('motds.json', 'w') as f:
            json.dump(all_motds, f)

        # then, reload the data
        with open('motds.json', 'r') as f:
            self.motds_data = json.load(f)

    def on_snze(self):
        if self.alarm.is_active:
            self.alarm.snooze()


        else:
            print("turning off light")
            try:
                host = config.server_ip
                path = '/toggle_light'
                addr = socket.getaddrinfo(host, config.server_port)[0][-1]
                s = socket.socket()
                s.connect(addr)
                s.send(b"GET " + path.encode() + b" HTTP/1.1\r\nHost: " +
                       host.encode() + b"\r\nConnection: close\r\n\r\n")
                s.close()
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

    def main(self):
        # self.draw_cube()
        self.clock()
        self.draw_estimated_sleep()
        self.draw_icons()
        self.draw_looptime()
        self.draw_temp()

        if self.motd_mode == 'scroll':
            self.scroll_motd()
            self.bounce_firstime = True
            
        elif self.motd_mode == 'bounce':
            self.bounce_motd()

        if self.apply_offset:
            self.offset = self.offset_val
        else:
            self.offset = 0



if __name__ == '__main__':
    from displaystates import mode

    from alarm import Alarm
    displaymanager = mode.DisplayManager()
    from config import motor, speaker, switch
    from hardware import Switch
    switch = Switch(switch)
    alarm = Alarm(60, motor, 12, speaker, switch)
    home = Home(displaymanager, alarm, "test")
    displaymanager.display_states = [home]
    displaymanager.set_active_state("test")
    while True:
        displaymanager.run_current_state()
