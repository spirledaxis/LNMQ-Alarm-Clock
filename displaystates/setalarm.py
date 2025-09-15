from displaystates import aliases
from displaystates.mode import DisplayState, timefont, bally
from hardware import Button, RepeatButton
import config
import json
from lib import timeutils
from time import sleep_ms

class SetAlarm(DisplayState):
    def __init__(self, display_manager, alarm, name):
        self.button_map = [
            Button(config.fwd, self.on_fwd),
            Button(config.rev, self.on_rev),
            Button(config.alm_set, self.on_exit),
            Button(config.snd_fx_l, self.on_selection),
            Button(config.snze_l, self.preview),
            Button(config.clk_set, self.goto_midpoint),
            RepeatButton(config.fwd, self.on_fwd),
            RepeatButton(config.rev, self.on_rev),
        ]
        super().__init__(self.button_map, name, display_manager)
        with open('alarm.json', 'r') as f:
            alarm_json = json.load(f)
            self.hour = int(alarm_json['hour'])
            self.minute = int(alarm_json['minute'])
            self.ampm = alarm_json['ampm']
            self.ringtone_index = alarm_json['ringtone']

        with open('ringtones.json', 'r') as f:
            self.ringtone_json = json.load(f)

        self.ringtone_len = len(self.ringtone_json)
        for ringtone in self.ringtone_json:
            if ringtone['index'] == self.ringtone_index:
                self.volume = ringtone['volume']

        self.volume_y = (self.display.height // 2 - timefont.height // 2) - 15
        self.selection = 'minute'
        self.ringtone_y = self.display.height // 2 + \
            timefont.height // 2 + bally.height // 2
        self.alarm = alarm
        self.edit_options = ['hour', 'minute', 'ampm', 'ringtone', 'volume']
        self.edit_index = 0
        self.display_manager = display_manager
        self.motor = config.motor
        self.motor.ready = False
        self.offsetx = self.display.width - 10 # offset from the left edge where things are drawn
        self.ampm_offsetx = 10 #offset from the right edge, needs to be added to ampm len

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
            if self.ringtone_index + 1 > self.ringtone_len:
                self.ringtone_index = 1
            else:
                self.ringtone_index += 1

            for ringtone in self.ringtone_json:
                if ringtone['index'] == self.ringtone_index:
                    self.volume = ringtone['volume']

        elif self.selection == 'ampm':
            if self.ampm == 'am':
                print("setting to pm")
                self.ampm = 'pm'
            else:
                print("setting to am")
                self.ampm = 'am'
        elif self.selection == 'volume':
            if self.volume + 1 > 30:
                self.volume = 1
            else:
                self.volume += 1

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

            for ringtone in self.ringtone_json:
                if ringtone['index'] == self.ringtone_index:
                    self.volume = ringtone['volume']

        elif self.selection == 'ampm':
            if self.ampm == 'am':
                self.ampm = 'pm'
            else:
                self.ampm = 'am'
        elif self.selection == 'volume':
            if self.volume - 1 < 1:
                self.volume = 30
            else:
                self.volume -= 1

    def preview(self):
        if not config.speaker.queryBusy():
            self.motor.set_movement_by_ringtone(self.ringtone_index)
            config.speaker.setVolume(self.volume)
            config.speaker.playTrack(1, self.ringtone_index)
            self.motor.start()
        else:
            config.speaker.pause()
            self.motor.stop()

    def goto_midpoint(self):
        if self.selection == 'minute':
            self.minute = 30
        elif self.selection == 'hour':
            self.hour = 6
        elif self.selection == 'ringtone':
            self.ringtone_index = self.ringtone_index // 2

            for ringtone in self.ringtone_json:
                if ringtone['index'] == self.ringtone_index:
                    self.volume = ringtone['volume']

        elif self.selection == 'volume':
            self.volume = 15

    def on_exit(self):
        with open('alarm.json', 'r') as f:
            alarm_msg = json.load(f)['alarm_message']

        data = {
            "hour": self.hour,
            "minute": self.minute,
            "ampm": self.ampm,
            "ringtone": self.ringtone_index,
            "volume": self.volume,
            "alarm_message": alarm_msg,
        }

        for ringtone in self.ringtone_json:
            if ringtone['index'] == self.ringtone_index:
                ringtone['volume'] = self.volume

        with open('ringtones.json', 'w') as f:
            json.dump(self.ringtone_json, f)

        with open('alarm.json', 'w') as f:
            json.dump(data, f)

        self.alarm.hour = timeutils.to_military_time(self.hour, self.ampm)
        self.alarm.minute = self.minute
        self.alarm.ringtone = self.ringtone_index
        self.motor.set_movement_by_ringtone(self.ringtone_index)
        self.display_manager.set_active_state(aliases.home)
        self.motor.ready = False

    def on_selection(self):
        self.edit_index = (self.edit_index + 1) % len(self.edit_options)
        self.selection = self.edit_options[self.edit_index]

    def display_alarm_time(self):
        time_display = f"{self.hour}:{self.minute:02}"

        y = self.display.height // 2 - timefont.height // 2
        self.display.draw_text(self.offsetx, y, time_display, timefont, rotate=180)
        if self.hour > 9:
            self.ampm_offsetx = 0
        else:
            self.ampm_offsetx = 10
            
        self.display.draw_text(self.ampm_offsetx+timefont.measure_text(self.ampm), y, self.ampm, timefont, rotate=180)
    def display_ringtone(self):
        ringtone_text = f"{self.ringtone_index}. {self.ringtone_json[self.ringtone_index-1]['description']}"

        self.display.draw_text(self.offsetx, self.ringtone_y,
                               ringtone_text, bally, rotate=180)

        volume_percentage = round((self.volume / 30) * 100)
        volume_text = f"Volume: {volume_percentage}% ({self.volume})"
        self.display.draw_text(self.offsetx, self.volume_y, volume_text, bally, rotate=180)

    def selection_line(self):
        x = self.offsetx
        y = self.display.height // 2 - timefont.height // 2

        hour = str(self.hour)
        minute = f"{self.minute:02}"
        hour_len = timefont.measure_text(hour)
        colon_len = timefont.measure_text(":")
        minute_len = timefont.measure_text(minute)
        ampm_len = timefont.measure_text(self.ampm)
        space_len = timefont.measure_text(' ')

        if self.selection == 'hour':
            self.display.draw_hline(x - hour_len, y - 3, hour_len)

        elif self.selection == 'minute':
            self.display.draw_hline(
                x - hour_len - colon_len - minute_len, y - 3, minute_len)

        elif self.selection == 'ampm':
            self.display.draw_hline(self.ampm_offsetx, y - 3, ampm_len)

        elif self.selection == 'ringtone':
            self.display.draw_vline(
                self.offsetx, self.ringtone_y, bally.height)

        elif self.selection == 'volume':
            self.display.draw_vline(
                self.offsetx, self.volume_y, bally.height
            )

    def main(self):
        self.display_alarm_time()
        self.selection_line()
        self.display_ringtone()
        self.motor.do_movement()
