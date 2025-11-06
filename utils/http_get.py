import socket


def http_get(host, port, path):
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect(addr)
        # HTTP/1.0 + Host header
        s.send(b"GET %s HTTP/1.0\r\nHost: %s\r\n\r\n" %
               (path.encode(), host.encode()))
        data = b""
        while True:
            chunk = s.recv(128)
            if not chunk:
                break
            data += chunk
        header_end = data.find(b"\r\n\r\n")
        if header_end != -1:
            return data[header_end + 4:].decode()
        return data.decode()
    finally:
        s.close()
