from machine import PWM, Pin  # type: ignore

from lib.neotimer import Neotimer

from .motor_movements import *


class Motor:
    def __init__(self, left_pin, right_pin, pwm_freq, min_pwm):
        "cmd sytax: ('dir', time_ms, %speed)"
        self.left_pin = PWM(Pin(left_pin), pwm_freq, duty_u16=0)
        self.right_pin = PWM(Pin(right_pin), pwm_freq, duty_u16=0)
        self.is_idle = True
        self.ready = False
        self.movement_increment = -1
        self.timer = Neotimer(0)
        self.min_pwm = min_pwm
        self.max_pwm = 65535
        self.repeat = False

    def _interact(self, cmd, speed_percent):
        # speed to duty cycle (speed param is percentage)
        speed_percent = max(0, min(speed_percent, 100))
        # Linear interpolation
        duty_cycle = int(self.min_pwm + (speed_percent / 100)
                         * (self.max_pwm - self.min_pwm))

        if cmd == 'l':
            self.left_pin.duty_u16(duty_cycle)
            self.right_pin.duty_u16(0)
        elif cmd == 'r':
            self.left_pin.duty_u16(0)
            self.right_pin.duty_u16(duty_cycle)
        elif cmd == 'w':
            self.left_pin.duty_u16(0)
            self.right_pin.duty_u16(0)

        self.is_idle = False

    def set_movement(self, movement):
        """A movement is a list of tuples.
        Syntax: (cmd, dur_ms, speed)
        cmd: 'l', 'r', or 'w' (wait)
        dur_ms: duration of that cmd
        speed: a percent of the motors speed
        """
        self.movement = movement
        self.timer.start()

    def do_movement(self):
        if not self.ready:
            return

        if self.timer.finished():
            if self.movement_increment + 1 >= len(self.movement):
                print("end of movement")
                if not self.repeat:
                    self.stop()
                self.movement_increment = -1

            else:
                self.movement_increment += 1
                cmd, dur_ms, speed = self.movement[self.movement_increment]
                self.timer = Neotimer(dur_ms)
                self.timer.start()
                self._interact(cmd, speed)

    def motor_thread_step(self):
        if self.ready:
            self.do_movement()

    def movement_len_ms(self, movement):
        time_ms = 0
        for _, dur_ms, _, in movement:
            time_ms += dur_ms

        return time_ms

    def stop(self):
        print("stopping motor")
        self.left_pin.duty_u16(0)
        self.right_pin.duty_u16(0)
        self.is_idle = True
        self.ready = False
        self.timer = Neotimer(0)
        self.timer.start()
        self.movement_increment = -1

    def start(self, reset_increment=False):
        self.ready = True
        if reset_increment:
            self.movement_increment = -1

    def set_movement_by_ringtone(self, ringtone):
        self.repeat = False
        if ringtone == 13:
            self.set_movement(freedom_dive)
        elif ringtone == 8:
            self.set_movement(i_am_speed)
        elif ringtone == 19:
            self.set_movement(eta)
        elif ringtone == 17:
            self.set_movement(stay_with_me)
        elif ringtone == 18:
            self.set_movement(clash_royale)
        else:
            self.set_movement(default)
            self.repeat = True
