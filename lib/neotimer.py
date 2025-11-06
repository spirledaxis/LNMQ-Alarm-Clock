from time import ticks_diff, ticks_ms

# Neotimer Class


class Neotimer:
    def __init__(self, duration):
        self.duration = duration
        self.last = ticks_ms()
        self.started = False
        self.done = False
        self.repetitions = -1  # Unlimited

    def start(self):
        "Start the timer"
        self.reset()
        self.started = True

    def stop(self):
        "Stop the timer"
        self.started = False
        return self.get_elapsed()

    def reset(self):
        "Reset the timer back to its original duration. Also stops the timer."
        self.stop()
        self.last = ticks_ms()
        self.done = False

    def restart(self):
        "Restart the timer. Like reset, but doesn't stop the timer"
        self.last = ticks_ms()
        self.done = False

    def finished(self):
        "Returns True if the timer has finished"
        if not self.started:
            return False

        if self.get_elapsed() >= self.duration:
            self.done = True
            return True
        else:
            return False

    def get_elapsed(self):
        "Returns elapsed time"
        return ticks_diff(ticks_ms(), self.last)

    def get_remaining(self):
        "Returns remaining time. Returns 0 when timer is done."
        if not self.started:
            return self.duration

        remaining_time = self.duration - ticks_diff(ticks_ms(), self.last)
        if remaining_time < 0:
            return 0
        else:
            return remaining_time

    def debounce_signal(self, signal):
        "Debounces a signal with duration"
        if not self.started:
            self.start()
        if signal and self.finished():
            self.start()
            return True
        else:
            return False

    def hold_signal(self, signal):
        "Returns true if a signal is on for duration"
        if signal:
            if not self.started:
                self.start()
            return True if self.finished() else False

        self.reset()  # <--- Stops and resets the timer.
        return False

    def repeat_execution(self):
        "Returns true when timer is done and resets it"
        if self.finished():
            self.reset()
            return True

        if not self.started:
            self.started = True
            self.last = ticks_ms()

        return False

    def repeat_execution_times(self, count):
        "Executes repeat_execution count times. Resets timer on every execution except last."
        if count != -1:
            if self.repetitions == -1:  # <---- Initial state is -1
                self.repetitions = count
            if self.repetitions == 0:  # <---- When finished return False
                return False
            if self.repeat_execution():  # <---- Otherwise call repeat_execution()
                self.repetitions -= 1
                return True
            else:
                return False
        else:
            # <---- if repetitions is -1, just call repeat_execution()
            return self.repeat_execution()

    def reset_repetitions(self):
        "Resets repetitions"
        self.repetitions = -1

    def waiting(self):
        "Returns True for the duration of the timer"
        if self.started and not self.finished():
            return True
        else:
            return False
