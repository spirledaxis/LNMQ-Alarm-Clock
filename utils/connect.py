from wificreds import name, password
import network  # type: ignore
import time

def do_connect():
    print('do_connect called')
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Connecting to network...')
        sta_if.active(True)
        sta_if.connect(name, password)
        for _ in range(20):
            if sta_if.isconnected():
                break
            time.sleep(0.5)
    
    ip, subnet, gateway, dns = sta_if.ifconfig()
    print('Network config:', (ip, subnet, gateway, dns))

    if ip == "0.0.0.0":
        print("Detected bad IP, retrying...")
        time.sleep(5)
        do_connect()

    return sta_if


def check_connection():
    sta_if = network.WLAN(network.WLAN.IF_STA)
    return sta_if.isconnected()


if __name__ == '__main__':
    do_connect()
