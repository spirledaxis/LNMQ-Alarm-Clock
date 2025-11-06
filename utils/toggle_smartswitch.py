import socket

import config


def toggle_smartswitch():
    host = config.server_ip
    path = '/toggle_light'
    addr = socket.getaddrinfo(host, config.server_port)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(b"GET " + path.encode() + b" HTTP/1.1\r\nHost: " +
           host.encode() + b"\r\nConnection: close\r\n\r\n")
    s.close()
