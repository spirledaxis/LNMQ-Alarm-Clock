from lib import timeutils
from lib.neotimer import Neotimer
import json
from displaystates import aliases
import motd_parser


class Alarm:
    def __init__(self, timeout_s, motor, headlights, speaker, switch):
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
        self.switch = switch
        self.is_active = False
        self.locked = False  # used so we don't call fire for the entire minute
        self.motor = motor
        self.headlights = headlights
        self.motor.set_movement_by_ringtone(self.ringtone)
        self.speaker = speaker
        self.speaker_state_timer = Neotimer(1000)
        self.original_ringtone = self.ringtone
        self.snoozed = False

    def update(self, now, home):
        """
        Args:
            now: a rtc tuple"""
        #(year, month, mday, hour, minute, second, weekday, yearday)

        now_hour = now[4]
        now_minute = now[5]
        #print(self.hour, self.minute, self.locked, self.enabled)
        if now_hour == self.hour and now_minute == self.minute and not self.locked:
            self.fire(now, home)
            print("firing")

        elif now_minute != self.minute and self.locked:
            self.locked = False

        if self.timeout_timer.finished():
            print("timeout reached")
            self.timeout_timer.reset()
            self.stop()
            home.motd = motd_parser.select_random_motd(self.motds_data)['motd']
            home.motd_mode = 'scroll'

        if self.is_active:
            if not self.speaker.queryBusy() and self.speaker_state_timer.finished():
                print("going at it again")
                # self.motor.stop()  # stop the motor in the case that the movement is longer than the audio
                # Can't use this because it introduces delay which cooks sync
                self.speaker.playTrack(1, self.ringtone)
                self.motor.start()
                self.speaker_state_timer.restart()

            # self.motor.do_movement() #moved to another thread

    def fire(self, now, home):
        if self.locked:
            return

        if now[2] == 1:
            self.original_ringtone = self.ringtone
            self.ringtone = 11  # first of the month ringtone

        with open('alarm.json', 'r') as f:
            alarm_message = json.load(f)['alarm_message']
        with open('ringtones.json', 'r') as f:
            volume = json.load(f)[self.ringtone - 1]['volume']

        print("alarm should go off now")
        self.locked = True
        self.is_active = True
        home.display_manager.display.wake()
        home.display_manager.display_timer.restart()
        home.display_manager.set_active_state(aliases.home)
        home.motd_mode = "bounce"
        home.motd = alarm_message
        self.speaker.setVolume(volume)
        self.speaker.playTrack(1, self.ringtone)
        self.motor.start()
        self.motor.set_movement_by_ringtone(self.ringtone)
        self.headlights.start(self.ringtone)
        self.timeout_timer.start()
        self.speaker_state_timer.start()
    def snooze(self):
        self.is_active = False
        self.snoozed = True
        self.minute += 10
        if self.minute > 60:
            self.hour += 1
            if self.hour > 23:
                self.hour = 0
            self.minute = self.minute % 60

    def stop(self):
        print("stopping...")
        if not self.is_active:
            print("attempted to stop alarm, but none was active")

        self.speaker.pause()
        self.motor.stop()
        self.headlights.stop()
        self.timeout_timer.reset()
        self.is_active = False
        self.ringtone = self.original_ringtone

        if self.snoozed:
            with open('alarm.json', 'r') as f:
                data = json.load(f)
            
            self.hour = data['hour']
            self.minute = data['minute']
            ampm = data['ampm']
            if ampm == 'pm':
                self.hour += 12
                if self.hour >= 24:
                    self.hour = 0

            self.snoozed = False
