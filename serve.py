#!/usr/bin/env python

import socketserver
import http.server
import datetime
import sys
import cgi
import os

from export_events import update_events
from utils import normalize_time


# Custom handler
class CustomHandler(http.server.SimpleHTTPRequestHandler):
  def do_GET(self):
    # default behavior
    http.server.SimpleHTTPRequestHandler.do_GET(self) 

  def do_POST(self):
    form = cgi.FieldStorage(
      fp = self.rfile,
      headers = self.headers,
      environ = {'REQUEST_METHOD':'POST', 'CONTENT_TYPE':self.headers['Content-Type']})
    result = 'NOT_UNDERSTOOD'

    if self.path == '/refresh':
      # recompute jsons. We have to pop out to root from render directory
      # temporarily. It's a little ugly
      refresh_time = form.getvalue('time')
      update_events("../logs", ".") # defined in export_events.py
      result = 'OK'
      
    if self.path == '/addnote':
      # add note at specified time and refresh
      note = form.getvalue('note')
      note_time = int(form.getvalue('time'))
      dt = datetime.datetime.strptime(note_time, "%s")
      note_file = "../logs/notes_{}.txt".format(normalize_time(dt).strftime("%s"))
      with open(note_file, "a") as f:
        f.write(dt.strftime("%s") + " " + note)
      update_events("../logs", ".") # defined in export_events.py
      result = 'OK'

    if self.path == '/blog':
      # add note at specified time and refresh
      post = form.getvalue('post')
      if post is None: post = ''
      post_time = int(form.getvalue('time'))
      dt = datetime.datetime.strptime(post_time, "%s")
      blog_file = "../logs/blog_{}.txt".format(normalize_time(dt).strftime("%s")) 
      with open(blog_file, 'w') as f:
        f.write(post)
      update_events("../logs", ".") # defined in export_events.py
      result = 'OK'
    
    self.send_response(200)
    self.send_header('Content-type','text/html')
    self.end_headers()
    self.wfile.write(result.encode())


if __name__ == "__main__":
    # Port settings
    if len(sys.argv) > 1:
      PORT = int(sys.argv[1])
    else:
      PORT = 8124

    # serve render/ folder, not current folder
    os.chdir('render')
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("", PORT), CustomHandler)

    print ('Serving ulogme, see it on http://ulogme.localhost:' + str(PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
