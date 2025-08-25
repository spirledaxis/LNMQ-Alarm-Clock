
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
    
    def run_current_state(self):
        self.current_state_obj.main()
        self.display.present()
        if self.display_timer.finished():
            self.activate_state("display_off")

class DisplayState:
    def __init__(self, buttonmap, name, display_manager):
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
            Button(config.snd_fx_l, self.toggle_display)
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
        if len(self.new_motds) == 0:
            return
        
        with open('motds.json', 'r') as f:
            all_motds = json.load(f)

        for motd in all_motds:
            #find a new motd
            if motd['id'] == self.new_motds[0]['id']:
                motd['new'] = False
                break
            else:
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
            host = config.ip
            path = '/toggle_light'
            addr = socket.getaddrinfo(host, 80)[0][-1]
            s = socket.socket()
            s.connect(addr)
            s.send(b"GET " + path.encode() + b" HTTP/1.1\r\nHost: " + host.encode() + b"\r\nConnection: close\r\n\r\n")
            s.close()
        

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

    display_manager = DisplayManager()
    home = Home(display_manager, 'home')
    alarm = SetAlarm(display_manager, 'set_alarm')
    off = DisplayOff(display_manager, 'display_off')
    display_manager.display_states = [home, alarm, off]
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
