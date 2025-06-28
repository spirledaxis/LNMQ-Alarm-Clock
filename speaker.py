#In order ror this example-code to work, make sure you have a
#card with at least one folder, containing at least two mp3:s.
#The folders should be named 01, 02 etc and files should be named
#001.mp3, 002.mp3 etc.
from utime import sleep_ms, sleep
from picodfplayer import DFPlayer
from machine import Pin

#Constants. Change these if DFPlayer is connected to other pins.
UART_INSTANCE=0
TX_PIN = 12
RX_PIN = 13
BUSY_PIN = Pin(16, Pin.IN) #cant get this to work
TRANSITOR = Pin(17, Pin.OUT)
#Create player instance
player=DFPlayer(UART_INSTANCE, TX_PIN, RX_PIN, BUSY_PIN)
TRANSITOR.on()


try:
    #Play the first song (001.mp3) from the first folder (01)
    print(BUSY_PIN.value())
    print('Playing track 001.mp3 in folder 01')
    player.playTrack(1,1)

    while True:
        sleep(0.2)
        print(BUSY_PIN.value())
        player.playerBusy()
    
except KeyboardInterrupt:
    TRANSITOR.off()
    player.pause()