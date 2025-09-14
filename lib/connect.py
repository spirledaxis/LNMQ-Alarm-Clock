from wificreds import name, password
import network  # type: ignore


def do_connect():
    print('do_connected called')
    sta_if = network.WLAN(network.WLAN.IF_STA)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(name, password)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ipconfig('addr4'))
    return sta_if

def check_connection():
    sta_if = network.WLAN(network.WLAN.IF_STA)
    return sta_if.isconnected()

