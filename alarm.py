from lib import timeutils
from lib.neotimer import Neotimer
import json

class Alarm:
    def __init__(self, timeout_s, motor, speaker, switch):
        """use military time for the hour. """
        with open('alarm.json', 'r') as f:
            # print(f.read())
            alarm = json.load(f)
            alarm_hour = int(alarm['hour'])
            alarm_ampm = alarm['ampm']
            self.minute = int(alarm['minute'])
            self.ringtone = alarm['ringtone']

        self.hour = timeutils.to_military_time(alarm_hour, alarm_ampm)
        self.timeout_timer = Neotimer(timeout_s * 1000)
        self.enabled = switch.get_state()
        self.switch = switch
        self.is_active = False
        self.locked = False  # used so we don't call fire for the entire minute
        self.motor = motor
        self.motor.set_movement_by_ringtone(self.ringtone)
        self.speaker = speaker
        self.speaker_state_timer = Neotimer(1000)
        self.original_ringtone = self.ringtone
        

    def update(self, now, home):
        """
        Args:
            now: a rtc tuple"""
        #(year, month, mday, hour, minute, second, weekday, yearday)
        self.switch.update()
        if self.switch.get_state():
            self.enabled = True
        else:
            self.enabled = False

        now_hour = now[4]
        now_minute = now[5]
        #print(self.hour, self.minute, self.locked, self.enabled)
        if now_hour == self.hour and now_minute == self.minute and not self.locked and self.enabled:
            self.fire(now, home)
            print("firing")

        elif now_minute != self.minute and self.locked:
            self.locked = False

        if self.timeout_timer.finished():
            print("timeout reached")
            self.timeout_timer.reset()
            self.stop()

        if self.is_active:
            if not self.speaker.queryBusy() and self.speaker_state_timer.finished():
                print("going at it again")
                #self.motor.stop()  # stop the motor in the case that the movement is longer than the audio
                # Can't use this because it introduces delay which cooks sync
                self.speaker.playTrack(1, self.ringtone)
                self.motor.start()
                self.speaker_state_timer.restart()

            #self.motor.do_movement() #moved to another thread

    def fire(self, now, home):
        if self.locked:
            return

        if now[2] == 1:
            self.original_ringtone = self.ringtone
            self.ringtone = 16  # first of the month ringtone

        with open('alarm.json', 'r') as f:
            alarm_message = json.load(f)['alarm_message']
        with open('ringtones.json', 'r') as f:
            volume = json.load(f)[self.ringtone - 1]['volume']

        print("alarm should go off now")
        self.locked = True
        self.is_active = True
        home.display_manager.display.wake()
        home.display_manager.display_timer.restart()
        #TODO: switch to alias, but cant import due to circulars
        home.display_manager.set_active_state("home")
        home.motd_mode = "bounce"
        home.motd = alarm_message
        self.speaker.setVolume(volume)
        self.speaker.playTrack(1, self.ringtone)
        self.motor.start()
        self.motor.set_movement_by_ringtone(self.ringtone)
        self.timeout_timer.start()
        self.speaker_state_timer.start()

    def stop(self):
        print("stopping...")
        if not self.is_active:
            print("attempted to stop alarm, but none was active")

        self.speaker.pause()
        self.motor.stop()
        self.timeout_timer.reset()
        self.is_active = False
        self.ringtone = self.original_ringtone