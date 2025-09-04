from displaystates import aliases
from components import Button
import config
from displaystates.mode import DisplayState
class DisplayOff(DisplayState):
    def __init__(self, display_manager, name):
        self.button_map = [Button(config.snd_fx_l, self.exit)]
        self.display_manager = display_manager
        super().__init__(self.button_map, name, display_manager)

    def main(self):
        self.display.sleep()

    def exit(self):
        print("on exit")
        self.display.wake()
        # self.display_manager.display_timer.reset() # buttons already do this
        self.display_manager.set_active_state(aliases.home)