from displaystates import aliases
from hardware import Switch
import config
from lib.xglcd_font import XglcdFont
import json
from lib.neotimer import Neotimer
from utime import ticks_ms  # type: ignore
from machine import Pin  # type: ignore

print("loading fonts...")
timefont = XglcdFont('Proxy24x31.bin', 24, 31)
bally = XglcdFont('Bally7x9.bin', 7, 9)
bally_mini = XglcdFont('Bally5x8.bin', 5, 8)
prev_dur = 0


class DisplayManager:
    def __init__(self):
        self.display_states: list[DisplayState] = None
        self.display = config.display
        self.display_timer = Neotimer(config.display_timeout_min * 60_000)
        self.display_timer.start()
        self.switch = Switch(config.switch)
        with open('alarm.json', 'r') as f:
            alarmdata = json.load(f)
            self.alarm_active = alarmdata['is_active']

    def set_active_state(self, name):
        print("called activiate state")
        for display_state in self.display_states:
            if display_state.name == name:
                display_state.active = True
                self.current_state = name
                self.current_state_obj = display_state
            else:
                display_state.active = False

        if self.current_state_obj.name == 'message_reader':
            self.display_timer = Neotimer(
                config.display_messenger_timeout_min * 60_000)
        else:
            self.display_timer = Neotimer(config.display_timeout_min * 60_000)

        self.display_timer.start()

    def run_current_state(self):
        self.display.fill_rectangle(
            0, 0, self.display.width, self.display.height, True)

        self.current_state_obj.main()
        self.display.present()

        if self.display_timer.finished():
            print("display timer expired")
            self.set_active_state(aliases.display_off)

        for button in self.current_state_obj.button_map:
            button.update()
            if button.pressed:
                print("resetting display time via button press")
                self.display_timer.restart()

        self.switch.update()

        if self.current_state == aliases.set_alarm:
            self.alarm_active = self.current_state_obj.alarm_active


class DisplayState:
    def __init__(self, buttonmap, name, display_manager: DisplayManager):
        self.display = config.display
        self.name = name
        self.active = False
        self.button_map = buttonmap
        self.display_manager = display_manager
