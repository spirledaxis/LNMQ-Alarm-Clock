import socket
import connect
import json
from machine import RTC #type: ignore

html = """
<!DOCTYPE html>
<html>
  <head>
    <title>MOTD Server</title>
  </head>
  <body>
    <h1>Message of the Day</h1>
    <form action="/" method="get">
      <input type="text" name="motd" placeholder="Enter MOTD here">
      <input type="text" name="author" placeholder="Enter author">
      <input type="submit" value="Submit">
    </form>
    <p>Current MOTD: <strong>{motd}</strong></p>
    <p>Author: <strong>{author}</strong></p>
  </body>
</html>
"""
connect.do_connect()
motd = "None yet!"
author = "Unknown"

#example setting motd and author
#http://192.168.1.51/?motd=Hello+World&author=gurt

# Set up a basic socket server
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print('Listening on http://0.0.0.0/')

rtc = RTC()

while True:
  cl, addr = s.accept()
  print('Client connected from', addr)
  request = cl.recv(1024).decode('utf-8')

  # Look for '?motd=' and '&author=' in the request
  if 'GET /?motd=' in request:
      query = request.split('GET /?')[1].split(' ')[0]
      params = query.split('&')
      for p in params:
          if p.startswith('motd='):
              motd = p.split('=')[1].replace('+', ' ').replace('%20', ' ')
          elif p.startswith('author='):
              author = p.split('=')[1].replace('+', ' ').replace('%20', ' ')
          
      print(f"New data: {motd}, {author}")

      with open('motds.json', 'r') as f:
          data = json.load(f)
          print(data)
      highest_id_dict = data[-1]
      highest_id = highest_id_dict["id"]
      new_id = highest_id + 1

      now = rtc.datetime()
      newdata = {
          "motd": motd,
          "id": new_id,
          "author": author,
          "time": now

      }
      
      data.append(newdata)

      with open('motds.json', 'w') as f:
              json.dump(data, f)
      
      print("saved the new data")

  if 'GET /motds.json' in request:
    with open('motds.json', 'r') as f:
            data = json.load(f)

    response_body = json.dumps(data)
    cl.send('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
    cl.send(response_body)
    cl.close()
    continue
    

  response = html.format(motd=motd, author=author)
  
  cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
  cl.send(response)
  cl.close()


