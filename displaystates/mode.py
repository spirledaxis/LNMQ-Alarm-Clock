from displaystates import aliases
from components import Switch
import config
from lib.xglcd_font import XglcdFont
import json
from lib.neotimer import Neotimer
from utime import ticks_ms  # type: ignore

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

        self.switch.update()


class DisplayState:
    def __init__(self, buttonmap, name, display_manager: DisplayManager):
        self.display = config.display
        self.name = name
        self.active = False
        self.button_map = buttonmap
        self.display_manager = display_manager


if __name__ == '__main__':
    from displaystates import Home, DisplayOff, MessageViewer, SetAlarm

    with open('motds.json', 'r') as f:
        motds_data = json.load(f)
    import config
    from components import Alarm, Switch, Motor

    motor = Motor(config.motor_l, config.motor_r,
                  config.motor_pwm_freq, config.motor_min_pwm)
    switch = Switch(config.switch)
    myalarm = Alarm(config.alarm_timeout_min * 60,
                    motor, config.speaker, switch)
    display_manager = DisplayManager()
    home = Home(display_manager, myalarm, 'home')
    alarm = SetAlarm(display_manager, myalarm, 'set_alarm')
    off = DisplayOff(display_manager, 'display_off')
    messenger = MessageViewer(display_manager, 'message_reader', home)
    display_manager.display_states = [home, alarm, off, messenger]
    display_manager.set_active_state(aliases.set_alarm)
    print("running mode")
    prev_dur = 0
    while True:
        display_manager.run_current_state()
        dur = display_manager.display_timer.get_elapsed()
        done = display_manager.display_timer.finished()
        cycle_time = dur - prev_dur
        prev_dur = dur
        #print(config.display_timeout_min*60_000-dur, done, cycle_time)
