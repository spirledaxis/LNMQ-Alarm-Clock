from machine import Pin  # type: ignore

from lib import Neotimer


class Button:
    def __init__(self, pin, callback, debounce_ms=100):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.callback_func = callback
        self.debounce_timer = Neotimer(debounce_ms)
        self.state = 0
        self.prev_state = 0
        self.is_debounced = False
        self.pressed = False

    def update(self):
        if self.debounce_timer.debounce_signal(not self.pin.value()):
            self.is_debounced = True

        if self.pin.value() == 0:  # the pull up resistor inverts the signal, pressed reads as 0
            self.state = 1  # self.state and prev_state use 1 as pressed, opposite to pin.value
        else:
            self.state = 0

        if (self.state == 1 and self.prev_state == 0):
            if self.is_debounced:
                self.pressed = True
                self.callback_func()
            else:
                print("under debounce cooldown")

            self.is_debounced = False

        else:
            self.pressed = False

        self.prev_state = self.state


class RepeatButton(Button):
    def __init__(self, pin, callback, init_delay_ms=200, repeat_ms=100):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.callback_func = callback
        self.init_delay = Neotimer(init_delay_ms)
        self.repeat_ms = Neotimer(repeat_ms)
        self.pressed = False

    def update_state(self):
        if self.pin.value() == 0:  # the pull up resistor inverts the signal, pressed reads as 0
            self.state = 1  # self.state and prev_state use 1 as pressed, opposite to pin.value
        else:
            self.state = 0

    def update(self):
        self.update_state()
        if self.init_delay.hold_signal(
                self.state) and self.repeat_ms.repeat_execution() and self.state == 1:
            self.callback_func()

        if self.state == 1:
            self.pressed = True
        else:
            self.pressed = False
