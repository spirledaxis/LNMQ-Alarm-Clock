import json

import config
from alarm import Alarm
from displaystates import aliases
from hardware import display, switch
from lib import Neotimer


class DisplayManager:
    def __init__(self, alarm: Alarm):
        self.display_states: list[DisplayState] = None
        self.display = display
        self.display_timer = Neotimer(config.display_timeout_min * 60_000)
        self.display_timer.start()
        self.switch = switch
        self.alarm = alarm
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
                self.display_timer.restart()

        self.switch.update()

        if self.current_state == aliases.set_alarm:
            self.alarm_active = self.current_state_obj.alarm_active


class DisplayState:
    def __init__(self, buttonmap, name, display_manager: DisplayManager):
        self.display = display
        self.name = name
        self.active = False
        self.button_map = buttonmap
        self.display_manager = display_manager
