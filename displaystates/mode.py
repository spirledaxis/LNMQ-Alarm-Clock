from displaystates import aliases
from hardware import Switch
import config
from lib.xglcd_font import XglcdFont
import json
from lib.neotimer import Neotimer
from utime import ticks_ms  # type: ignore
from machine import Pin #type: ignore

timefont = XglcdFont('Proxy24x31.c', 24, 31)
bally = XglcdFont('Bally7x9.c', 7, 9)

prev_dur = 0


class DisplayManager:
    def __init__(self):
        self.display_states: list[DisplayState] = None
        self.display = config.display
        self.display_timer = Neotimer(config.display_timeout_min * 60_000)
        self.display_timer.start()
        self.switch = Switch(config.switch)
        self.usb_power = Pin('WL_GPIO2', Pin.IN)
        self.bat_lock = False

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

        before = ticks_ms()
        self.current_state_obj.main()
        after = ticks_ms()
        #print(ticks_diff(after, before), "gng")
        #self.display.draw_vline(self.display.width//2, 0, self.display.height-1)
        self.display.present()
        # print(self.display_timer.get_remaining())

        if self.display_timer.finished():
            print("display timer expired")
            self.set_active_state(aliases.display_off)

        for button in self.current_state_obj.button_map:
            button.update()
            if button.pressed:
                print("resetting display time via button press")
                self.display_timer.restart()

        if self.usb_power.value() == 0 and not self.bat_lock: 
            self.bat_lock = True
            self.display_timer = Neotimer(config.display_timeout_bat_s * 1000)
            self.display_timer.start()

        elif self.usb_power.value() == 1 and self.bat_lock:
            self.bat_lock = False
            if self.current_state_obj.name == 'message_reader':
                self.display_timer = Neotimer(
                    config.display_messenger_timeout_min * 60_000)
            else:
                self.display_timer = Neotimer(config.display_timeout_min * 60_000)

            self.display_timer.start()

        self.switch.update()


class DisplayState:
    def __init__(self, buttonmap, name, display_manager: DisplayManager):
        self.display = config.display
        self.name = name
        self.active = False
        self.button_map = buttonmap
        self.display_manager = display_manager



