import socket
import select
import time

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 80))
s.listen(5)
s.setblocking(False)

while True:
    # do display, motor, etc (non-blocking)
    
    # Poll sockets
    rlist, _, _ = select.select([s], [], [], 0)
    if rlist:
        cl, addr = s.accept()
        print('Client connected from', addr)
        try:
            request = cl.recv(1024).decode()
            print('Request:', request)

            # ... handle request, write motds.json, etc ...

            cl.send(b'HTTP/1.0 200 OK\r\n\r\nHello!')
        except Exception as e:
            print("client error:", e)
        finally:
            cl.close()

    time.sleep(0.01)  # tiny sleep to keep CPU cool
