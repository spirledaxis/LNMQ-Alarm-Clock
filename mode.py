
from components import Button, Switch
import config
from lib import timeutils
from lib.xglcd_font import XglcdFont
from motds import motd_parser
import socket
import json
import framebuf #type: ignore
from machine import Pin, RTC #type: ignore
import network #type: ignore
from lib.neotimer import Neotimer
import random
timefont = XglcdFont('Proxy24x31.c', 24, 31)
bally = XglcdFont('Bally7x9.c', 7, 9)

class DisplayManager:
    def __init__(self):
        self.display_states: list[DisplayState] = None
        self.display = config.display
        self.display_timer = config.display_timer
        self.display_timer.start()
    def activate_state(self, name):
        for display_state in self.display_states:
            if display_state.name == name:
                display_state.active
                self.current_state = name
                self.current_state_obj = display_state
            else:
                display_state.active = False

        if self.current_state_obj.name == 'message_reader':
            self.display_timer = Neotimer(config.display_messenger_timeout_min*60_000)
        else:
            self.display_timer = config.display_timer

    def run_current_state(self):
        self.current_state_obj.main()
        self.display.present()
        if self.display_timer.finished():
            self.activate_state("display_off")

class DisplayState:
    def __init__(self, buttonmap, name, display_manager: DisplayManager):
        self.display = config.display
        self.name = name
        self.active = False
        self.button_map = buttonmap
        self.display_manager = display_manager
    def button_logic(self):
        for button in self.button_map:
            button.update()
            if button.pressed:
                print("resetting display time via button press")
                self.display_manager.display_timer.reset()
                self.display_manager.display_timer.start()

class Home(DisplayState):
    def __init__(self, display_manager, alarm, name):
        self.button_map = [
            Button(config.alm_set, self.goto_alarm),
            Button(config.snze_l, self.on_snze),
            Button(config.fwd, self.read_msg),
            Button(config.snd_fx_l, self.toggle_display),
            Button(config.clk_set, self.on_clk)
        ]
        super().__init__(self.button_map, name, display_manager)
        
        self.display_manager = display_manager
        self.switch = Switch(config.switch)
        self.motd_pos = 0
        self.motd = 'hello world'
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
        def make_icon(data):
            return framebuf.FrameBuffer(bytearray(data), 8, 8, framebuf.MONO_VLSB)

        self.bell_icon_fb = make_icon([0x03, 0x0c, 0x10, 0xe1, 0xe1, 0x10, 0x0c, 0x03])
        self.plug_icon = make_icon([0x00, 0x10, 0xf8, 0x1f, 0x1f, 0xf8, 0x10, 0x00])
        self.battery_icon = make_icon([0x00, 0x3f, 0x21, 0xe1, 0xe1, 0x21, 0x3f, 0x00])
        self.wifi_icon = make_icon([0x00, 0xff, 0x00, 0x3f, 0x00, 0x0f, 0x00, 0x03])
        self.no_wifi_icon = make_icon([0x00, 0xff, 0x00, 0x3f, 0x00, 0xaf, 0x40, 0xa3])
        self.mail_icon = make_icon([0xff, 0xa1, 0x91, 0x8d, 0x8d, 0x91, 0xa1, 0xff])

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
        #TODO: 1 is tuesday, supposedely. Idk if the tuple is weird or my function is cooked, thats why theres +1 for now. Fix later.
        date_text = f'{timeutils.daynum_to_daystr(day_name_int+1)} | {timeutils.monthnum_to_monthstr(month)} {month_day}'
        date_text_len = bally.measure_text(date_text)
        if date_text_len >= 128:
            date_text = f'{timeutils.daynum_to_daystr(day_name_int+1)} | {timeutils.monthnum_to_monthabbr(month)} {month_day}'
            date_text_len = bally.measure_text(date_text)

        #origin is in the bottom right

        #Display the time
        self.display.fill_rectangle(0, 0, self.display.width, self.display.height, True)
        self.display.draw_text((self.display.width+time_len) // 2, self.display.height // 2 - timefont.height // 2,
            time_text, timefont, rotate=180)
        
        #display weekday, month, and mday
        self.display.draw_text((self.display.width + date_text_len) // 2, ((self.display.height // 2) - timefont.height // 2)-10,
            date_text, bally, rotate=180)
        
        #display seconds bar
        len_line = int((second/60)*127 + 1)
        self.display.draw_hline(127-len_line, 63, len_line)
        self.display.draw_hline(127-len_line, 62, len_line)

    def scroll_motd(self):
        motd_len = bally.measure_text(self.motd)
        if self.motd_pos >= motd_len + self.display.width + 10:
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']
            self.motd_pos = 0
        else:
            self.motd_pos += 1


        self.display.draw_text(self.motd_pos, ((self.display.height // 2) + timefont.height // 2) + bally.height // 2 - 2,
            self.motd, bally, rotate=180)

    def draw_icons(self):
        if self.switch.get_state():
            self.display.draw_sprite(self.bell_icon_fb, x=((self.display.width-self.time_len) // 4)+4, y=(self.display.height // 2) + 4, w=8, h=8)
        else:
            self.display.fill_rectangle(x=((self.display.width-self.time_len) // 4)-4, y=(self.display.height // 2) + 4, w=8, h=8, invert=True)
        
        if self.usb_power.value() == 1:
            self.display.draw_sprite(self.plug_icon, x=((self.display.width-self.time_len) // 4) + 4, y=(self.display.height // 2) - 8, w=8, h=8)
        else:
            self.display.draw_sprite(self.battery_icon, x=((self.display.width-self.time_len) // 4) + 4, y=(self.display.height // 2) - 8 , w=8, h=8)
        
        if network.WLAN(network.WLAN.IF_STA).isconnected():
            self.display.draw_sprite(self.wifi_icon, x=((self.display.width-self.time_len) // 4) - 8, y=(self.display.height // 2) + 4, w=8, h=8)
        else:
            self.display.draw_sprite(self.no_wifi_icon, x=((self.display.width-self.time_len) // 4) - 8, y=(self.display.height // 2) + 4, w=8, h=8)
        
        if len(self.new_motds) != 0:
            self.display.draw_sprite(self.mail_icon, x=((self.display.width-self.time_len) // 4) - 8, y=(self.display.height // 2) - 8, w=8, h=8)
        else:
            self.display.fill_rectangle(x=((self.display.width-self.time_len) // 4) - 8, y=(self.display.height // 2) - 8, w=8, h=8, invert=True)
    
    def goto_alarm(self):
        self.display_manager.activate_state("set_alarm")
    
    def toggle_display(self):
        if not self.display.on:
            self.display.wake()
        else:
            config.display.sleep()
            
    def read_msg(self):
        print("reading message")
        if len(self.new_motds) == 0:
            print("there are no new motds")
            return
        
        with open('motds.json', 'r') as f:
            all_motds = json.load(f)

        for motd in all_motds:
            #set the read motd to new: false
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

        #then, reload the data
        with open('motds.json', 'r') as f:
            self.motds_data = json.load(f)
    
    def on_snze(self):
        if self.alarm.is_active:
            self.alarm.stop()
        else:
            #TODO: switch to urequests
            print("turning off light")
            host = config.server_ip
            path = '/toggle_light'
            addr = socket.getaddrinfo(host, config.server_port)[0][-1]
            s = socket.socket()
            s.connect(addr)
            s.send(b"GET " + path.encode() + b" HTTP/1.1\r\nHost: " + host.encode() + b"\r\nConnection: close\r\n\r\n")
            s.close()
    def on_clk(self):
        print("switching state")
        self.display_manager.activate_state("message_reader")
    def main(self):
        self.switch.update()
        self.clock()
        self.scroll_motd()
        self.button_logic()
        self.draw_icons()

class SetAlarm(DisplayState):
    def __init__(self, display_manager, alarm, name):
        self.button_map  = [
            Button(config.fwd, self.on_fwd),
            Button(config.rev, self.on_rev),
            Button(config.alm_set, self.on_exit),
            Button(config.snd_fx_l, self.on_selection)
        ]
        super().__init__(self.button_map, name, display_manager)
        with open('alarms.json', 'r') as f:
            alarm_json = json.load(f)
            alarm_json = alarm_json[0]
            self.hour = int(alarm_json['hour'])
            self.minute = int(alarm_json['minute'])
            self.ampm = alarm_json['ampm']
            self.ringtone_index = alarm_json['ringtone']

        with open('ringtones.json', 'r') as f:
            self.ringtone_json = json.load(f)

        self.ringtone_len = len(self.ringtone_json)
        self.selection = 'minute'
        self.ringtone_y = self.display.height // 2 + timefont.height // 2 + bally.height // 2
        self.alarm = alarm
        self.edit_options = ['hour', 'minute', 'ampm', 'ringtone']
        self.edit_index = 0
        self.display_manager = display_manager

    def on_fwd(self):
        if self.selection == 'minute':
            if self.minute + 5 >= 60:
                self.minute = 0
            else:
                self.minute += 5
        elif self.selection == 'hour':
            if self.hour + 1 > 12:
                self.hour = 1
            else:
                self.hour += 1
        elif self.selection == 'ringtone':
            if self.ringtone_index +1 > self.ringtone_len:
                self.ringtone_index = 1
            else:
                self.ringtone_index += 1
        elif self.selection == 'ampm':
            print("gurawsedf")
            if self.ampm == 'am':
                print("setting to pm")
                self.ampm = 'pm'
            else:
                print("setting to am")
                self.ampm = 'am'

    def on_rev(self):
        if self.selection == 'minute':
            if self.minute - 5 < 0:
                self.minute = 55
            else:
                self.minute -= 5
        elif self.selection == 'hour':
            if self.hour - 1 <= 0:
                self.hour = 12
            else:
                self.hour -= 1
        elif self.selection == 'ringtone':
            if self.ringtone_index - 1 < 1:
                self.ringtone_index = self.ringtone_len
            else:
                self.ringtone_index -= 1
        elif self.selection == 'ampm':
            if self.ampm == 'am':
                self.ampm = 'pm'
            else:
                self.ampm = 'am'

    def on_exit(self):
        data = [{
            "hour": self.hour,
            "minute": self.minute,
            "ampm": self.ampm,
            "ringtone": self.ringtone_index
        }]
        with open('alarms.json', 'w') as f:
            json.dump(data, f)
        
        self.alarm.hour = timeutils.to_military_time(self.hour, self.ampm)
        self.alarm.minute = self.minute
        self.alarm.ringtone = self.ringtone_index
        self.alarm.set_movement_by_ringtone()
        self.display_manager.activate_state("home")
          
    def on_selection(self):
        self.edit_index = (self.edit_index + 1) % len(self.edit_options)
        self.selection = self.edit_options[self.edit_index]

    def display_alarm_time(self):
        time_display = f"{self.hour}:{self.minute:02} {self.ampm}"
        self.time_len = timefont.measure_text(time_display)
        x = (self.display.width+self.time_len) // 2
        y = self.display.height // 2 - timefont.height // 2
        self.display.fill_rectangle(0, 0, self.display.width, self.display.height, True)
        self.display.draw_text(x, y, time_display, timefont, rotate=180)

    def display_ringtone(self):
        ringtone_text = f"{self.ringtone_index}. {self.ringtone_json[self.ringtone_index-1]['description']}"
        
        self.display.draw_text((self.display.width + self.time_len) // 2, self.ringtone_y,
        ringtone_text, bally, rotate=180)

    def selection_line(self):
        x = (self.display.width+self.time_len) // 2
        y = self.display.height // 2 - timefont.height // 2

        hour = str(self.hour)
        minute = f"{self.minute:02}"
        hour_len = timefont.measure_text(hour)
        colon_len = timefont.measure_text(":") 
        minute_len = timefont.measure_text(minute)
        ampm_len = timefont.measure_text(self.ampm)
        space_len = timefont.measure_text(' ')

        if self.selection == 'hour':
            self.display.draw_hline(x - hour_len, y-3, hour_len)
            self.display.draw_hline(x - hour_len - colon_len - minute_len, y-3, minute_len, invert=True)
        elif self.selection == 'minute':
            self.display.draw_hline(x - hour_len - colon_len - minute_len, y-3, minute_len)
            self.display.draw_hline(x - hour_len, y-3, hour_len, invert=True)
        elif self.selection == 'ampm':
            self.display.draw_hline(x - hour_len - colon_len - minute_len - space_len -ampm_len, y-3, ampm_len)
            self.display.draw_hline(x - hour_len - colon_len - minute_len, y-3, minute_len, invert=True)
        elif self.selection == 'ringtone':
            self.display.draw_vline((self.display.width + self.time_len) // 2, self.ringtone_y, bally.height)
            self.display.draw_hline(x - hour_len - colon_len - minute_len - space_len -ampm_len, y-3, ampm_len, invert=True)

    def main(self):
        self.display_alarm_time()
        self.selection_line()
        self.display_ringtone()
        self.button_logic()

class MessageViewer(DisplayState):
    #TODO: add drift to stop burn in
    def __init__(self, display_manager, name, home: Home):
        
        self.button_map  = [
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
        self.switch = Switch(config.switch)
        self.home = home
        self.usb_power = Pin('WL_GPIO2', Pin.IN)
        self.spacing = 4 + 8
        self.display_manager = display_manager
        self.invert_icons = Neotimer
        self.swap_icons = Neotimer(config.messenger_icon_cycle_time_s*1000)
        self.swap_icons.start()
        self.change_motd = Neotimer(config.messenger_cycle_time_s*1000)
        self.change_motd.start()
        self.invert = True
        def make_icon(data):
            return framebuf.FrameBuffer(bytearray(data), 8, 8, framebuf.MONO_VLSB)
        self.inverted_battery = make_icon([0xff, 0x80, 0xbe, 0x3e, 0x3e, 0xbe, 0x80, 0xff])
        self.inverted_plug = make_icon([0xff, 0xef, 0x07, 0xe0, 0xe0, 0x07, 0xef, 0xff])
        self.inverted_no_wifi = make_icon([0xff, 0x00, 0xff, 0xc0, 0xff, 0x50, 0xbf, 0x5c])
        self.inverted_wifi = make_icon([0xff, 0x00, 0xff, 0xc0, 0xff, 0xf0, 0xff, 0xfc])
        self.inverted_bell = make_icon([0xfc, 0xf3, 0xef, 0x1e, 0x1e, 0xef, 0xf3, 0xfc])
        self.inverted_mail = make_icon([0x00, 0x5e, 0x6e, 0x72, 0x72, 0x6e, 0x5e, 0x00])

    def on_fwd(self):
        self.home.read_msg()
        self.motd = self.home.motd

    def on_exit(self):
        print("exiting thje messaenger")
        self.display_manager.activate_state("home")
    
    def drift(self, min, max):
        idk = range(min, max+1)
        offsets = [coord for coord in idk]
        return random.choice(offsets)

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
        text_y = (self.display.height // 2 - bally.height // 2) + bally.height // 2 * (num_lines - 1)
        
        for part in split_motd:
            part_len = bally.measure_text(part)
            text_x = self.display.width // 2 + part_len // 2
            self.display.draw_text(text_x, text_y, part, bally, rotate=180)
            text_y -= bally.height

    def draw_icons(self):
        num_icons = 2
        if self.switch.get_state():
            num_icons += 1
        if len(self.home.new_motds) != 0:
            num_icons += 1

        total_width = (num_icons * 8) + ((num_icons - 1) * (self.spacing-8))
        start_x = (self.display.width - total_width) // 2
   
        x = start_x
        y = 1

        if self.invert:
            #self.display.fill_rectangle(self.display.width-start_x-total_width-padding, y, total_width+2*padding, y+7, invert=False)
            if self.switch.get_state():
                self.display.draw_sprite(self.inverted_bell, x=x, y=y, w=8, h=8)
                x += self.spacing
        
            if self.usb_power.value() == 1:
                self.display.draw_sprite(self.inverted_plug, x=x, y=y, w=8, h=8)
                x += self.spacing
            else:
                self.display.draw_sprite(self.inverted_battery, x=x, y=y, w=8, h=8)
                x += self.spacing

            if network.WLAN(network.WLAN.IF_STA).isconnected():
                self.display.draw_sprite(self.inverted_wifi, x=x, y=y, w=8, h=8)
                x += self.spacing
            else:
                self.display.draw_sprite(self.inverted_no_wifi, x=x, y=y, w=8, h=8)
                x += self.spacing

            if len(self.home.new_motds) != 0 :
                self.display.draw_sprite(self.inverted_mail, x=x, y=y, w=8, h=8)
                x += self.spacing
        else:
            self.display.fill_rectangle(0, y, self.display.width, y+8, invert=True)
            if self.switch.get_state():
                self.display.draw_sprite(self.home.bell_icon_fb, x=x, y=y, w=8, h=8)
                x += self.spacing
        
            if self.usb_power.value() == 1:
                self.display.draw_sprite(self.home.plug_icon, x=x, y=y, w=8, h=8)
                x += self.spacing
            else:
                self.display.draw_sprite(self.home.battery_icon, x=x, y=y, w=8, h=8)
                x += self.spacing

            if network.WLAN(network.WLAN.IF_STA).isconnected():
                self.display.draw_sprite(self.home.wifi_icon, x=x, y=y, w=8, h=8)
                x += self.spacing
            else:
                self.display.draw_sprite(self.home.no_wifi_icon, x=x, y=y, w=8, h=8)
                x += self.spacing

            if len(self.home.new_motds) != 0:
                self.display.draw_sprite(self.home.mail_icon, x=x, y=y, w=8, h=8)
                x += self.spacing
       
        #self.display.draw_vline(self.display.width//2, 0, self.display.height-1)
        
    def main(self):
        self.switch.update()
        self.display.fill_rectangle(0, 0, self.display.width, self.display.height, True)
        self.draw_motd()
        self.draw_icons()
        self.button_logic()
        if self.swap_icons.finished():
            self.invert = not self.invert
            self.swap_icons = Neotimer(config.messenger_icon_cycle_time_s)
            self.swap_icons.start()
        if self.change_motd.finished():
            self.change_motd = Neotimer(config.messenger_cycle_time_s)
            self.change_motd.start()
            self.motd = motd_parser.select_random_motd(self.motds_data)['motd']

        
class DisplayOff(DisplayState):
    def __init__(self, display_manager, name):
        self.button_map  = [Button(config.snd_fx_l, self.exit)]
        self.display_manager = display_manager
        super().__init__(self.button_map, name, display_manager)
        
    def main(self):
        self.display.sleep()
        self.button_logic()

    def exit(self):
        print("on exit")
        self.display.wake()
        #self.display_manager.display_timer.reset() # buttons already do this
        self.display_manager.activate_state("home")

if __name__ == '__main__':
    with open('motds.json', 'r') as f:
        motds_data = json.load(f)
    import config
    from components import Alarm, Switch, Motor

    motor = Motor(config.motor_l, config.motor_r, config.motor_pwm_freq, config.motor_min_pwm)
    switch = Switch(config.switch)
    myalarm = Alarm(config.alarm_timeout_min * 60, motor, config.speaker, switch)
    display_manager = DisplayManager()
    home = Home(display_manager, myalarm, 'home')
    alarm = SetAlarm(display_manager, myalarm, 'set_alarm')
    off = DisplayOff(display_manager, 'display_off')
    messenger = MessageViewer(display_manager, 'message_reader', home)
    display_manager.display_states = [home, alarm, off, messenger]
    display_manager.activate_state("home")
    print("running mode")
    prev_dur = 0
    while True:
        display_manager.run_current_state()
        dur = display_manager.display_timer.get_elapsed()
        done = display_manager.display_timer.finished()
        cycle_time = dur - prev_dur
        prev_dur = dur
        print(config.display_timeout_min*60_000-dur, done, cycle_time)
