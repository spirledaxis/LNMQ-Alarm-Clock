import pywemo
import socket
import time

url = pywemo.setup_url_for_address("192.168.1.18")
fan = pywemo.discovery.device_from_description(url)

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
s.settimeout(1)

try:
    while True:
        try:
            cl, addr = s.accept()
        except socket.timeout:
            continue

        print('Client connected from', addr)
        request = cl.recv(1024).decode('utf-8')
        print('Request:', request)

        if 'GET /toggle_light' in request:
            try:
                fan.toggle()
                body = f'light toggled: {fan.get_state()}'
                response = (
                    'HTTP/1.1 200 OK\r\n'
                    'Content-Type: text/plain\r\n'
                    f'Content-Length: {len(body)}\r\n'
                    'Connection: close\r\n'
                    '\r\n'
                    f'{body}'
                )
            except Exception as e:
                body = str(e)
                response = (
                    'HTTP/1.1 500 Internal Server Error\r\n'
                    'Content-Type: text/plain\r\n'
                    f'Content-Length: {len(body)}\r\n'
                    'Connection: close\r\n'
                    '\r\n'
                    f'{body}'
                )

            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()

        else:
            # For other requests, respond 404 and close
            body = '404 Not Found'
            response = (
                'HTTP/1.1 404 Not Found\r\n'
                'Content-Type: text/plain\r\n'
                f'Content-Length: {len(body)}\r\n'
                'Connection: close\r\n'
                '\r\n'
                f'{body}'
            )
            cl.sendall(response.encode())
            time.sleep(0.1)
            cl.close()

finally:
    s.close()
