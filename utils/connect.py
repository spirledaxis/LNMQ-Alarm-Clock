import time

import network  # type: ignore
from wificreds import name, password


def do_connect(retries=3):
    def connect():
        if sta_if.isconnected():
            print("already connected to wifi! No action taken.")
            return
        else:
            print('Connecting to network...')
            sta_if.active(True)
            sta_if.connect(name, password)
            for _ in range(20):
                if sta_if.isconnected():
                    break
                time.sleep(0.5)

    retry_counter = 0
    print('do_connect called')
    sta_if = network.WLAN(network.STA_IF)
    


    ip, subnet, gateway, dns = sta_if.ifconfig()
    print('Network config:', (ip, subnet, gateway, dns))

    if ip == "0.0.0.0" and retry_counter < retries:
        print("Detected bad IP, retrying...")
        time.sleep(5)
        retry_counter += 1
        print(retry_counter, retries)
        connect()

    print(sta_if)
    return sta_if


def check_connection():
    sta_if = network.WLAN(network.WLAN.IF_STA)
    return sta_if.isconnected()

