from displaystates import aliases
from components import Button
import config
import socket
from displaystates.mode import DisplayState
from lib.neotimer import Neotimer

class DisplayOff(DisplayState):
    def __init__(self, display_manager, name):
        self.button_map = [Button(config.snd_fx_l, self.exit), Button(config.snze_l, self.toggle_light)]
        self.display_manager = display_manager
        self.timer = Neotimer(100)
        self.first_time = True
        super().__init__(self.button_map, name, display_manager)

    def main(self):
        if self.first_time:
            self.first_time = False
            self.display.sleep()
    
    def toggle_light(self):
            host = config.server_ip
            path = '/toggle_light'
            addr = socket.getaddrinfo(host, config.server_port)[0][-1]
            s = socket.socket()
            s.connect(addr)
            s.send(b"GET " + path.encode() + b" HTTP/1.1\r\nHost: " +
                   host.encode() + b"\r\nConnection: close\r\n\r\n")
            s.close()

    def exit(self):
        print("on exit")
        self.display.wake()
        self.first_time = True
        # self.display_manager.display_timer.reset() # buttons already do this
        self.display_manager.set_active_state(aliases.home)

