import datetime
import json
import os
import cgi
import os.path
import http.server
import glob
import socketserver
from multiprocessing import Process

from typing import Optional


def normalize_time(dt: Optional[datetime.datetime] = None):
    if dt is None:
        dt = datetime.datetime.now()
    d = datetime.datetime(dt.year, dt.month, dt.day, 7)
    if dt.hour < 7:
        d -= datetime.timedelta(days=1)
    return d


def load_events(fname):
    """
    Reads a file that consists of first column of unix timestamps
    followed by arbitrary string, one per line. Outputs as dictionary.
    Also keeps track of min and max time seen in global mint,maxt
    """
    events = []

    try:
        with open(fname, 'r') as f:
            ws = f.read().splitlines()
        events = []
        for w in ws:
            ix = w.find(' ') # find first space, that's where stamp ends
            stamp = int(w[:ix])
            s = w[ix+1:]
            events.append({'t':stamp, 's':s})
    except Exception as e:
        pass
    return events


def mtime(f):
    """
    return time file was last modified, or 0 if it doesnt exist
    """
    if os.path.isfile(f):
        return int(os.path.getmtime(f))
    else:
        return 0


def update_events(log_dir, out_dir):
    """
    goes down the list of .txt log files and writes all .json
    files that can be used by the frontend
    """
    L = []
    L.extend(glob.glob(os.path.join(log_dir, "keyfreq_*.txt")))
    L.extend(glob.glob(os.path.join(log_dir, "window_*.txt")))
    L.extend(glob.glob(os.path.join(log_dir, "notes_*.txt")))

    # extract all times. all log files of form {type}_{stamp}.txt
    #print(L)
    ts = [int(x[x.find('_')+1:x.find('.txt')]) for x in L]
    ts = list(set(ts))
    ts.sort()

    mint = min(ts)

    # march from beginning to end, group events for each day and write json
    t = mint
    out_list = []
    for t in ts:
        t0 = t
        t1 = t0 + 60*60*24 # 24 hrs later
        fout = 'events_%d.json' % (t0, )
        out_list.append({'t0':t0, 't1':t1, 'fname': fout})

        fwrite = os.path.join(out_dir, fout)
        e1f = os.path.join(log_dir, 'window_%d.txt' % (t0, ))
        e2f = os.path.join(log_dir, 'keyfreq_%d.txt' % (t0, ))
        e3f = os.path.join(log_dir, 'notes_%d.txt' % (t0, ))
        e4f = os.path.join(log_dir, 'blog_%d.txt' % (t0, ))

        dowrite = False

        # output file already exists?
        # if the log files have not changed there is no need to regen
        if os.path.isfile(fwrite):
            tmod = mtime(fwrite)
            e1mod = mtime(e1f)
            e2mod = mtime(e2f)
            e3mod = mtime(e3f)
            e4mod = mtime(e4f)
            if e1mod > tmod or e2mod > tmod or e3mod > tmod or e4mod > tmod:
                dowrite = True # better update!
                # print('a log file has changed, so will update %s' % (fwrite, ))
        else:
            # output file doesnt exist, so write.
            dowrite = True

        if dowrite:
            # okay lets do work
            e1 = load_events(e1f)
            e2 = load_events(e2f)
            e3 = load_events(e3f)
            for k in e2: k['s'] = int(k['s']) # int convert

            e4 = ''
            if os.path.isfile(e4f):
                with open(e4f, 'r') as f:
                    e4 = f.read()

            eout = {'window_events': e1, 'keyfreq_events': e2, 'notes_events': e3, 'blog': e4}
            with open(fwrite, 'w') as f:
                f.write(json.dumps(eout))
            #print('wrote ' + fwrite)

    #outside for loop
    fwrite = os.path.join(out_dir, 'export_list.json')
    with open(fwrite, 'w') as f:
        f.write(json.dumps(out_list))
    #print('wrote ' + fwrite)


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # default behavior
        http.server.SimpleHTTPRequestHandler.do_GET(self) 

    def do_POST(self):
        form = cgi.FieldStorage(fp = self.rfile, headers = self.headers,
        environ = {'REQUEST_METHOD':'POST', 'CONTENT_TYPE':self.headers['Content-Type']})
        result = 'NOT_UNDERSTOOD'

        if self.path == '/refresh':
            # refresh jsons
            update_events("../logs", ".")
            result = 'OK'
      
        if self.path == '/addnote':
            # add note at specified time and refresh
            note = form.getvalue('note')
            note_time = int(form.getvalue('time'))
            dt = datetime.datetime.fromtimestamp(note_time)
            note_file = "../logs/notes_{}.txt".format(int(normalize_time(dt).timestamp()))
            with open(note_file, "a") as f:
                f.write(dt.strftime("%s") + " " + note + "\n")
            update_events("../logs", ".")
            result = 'OK'

        if self.path == '/blog':
            # add note at specified time and refresh
            post = form.getvalue('post')
            if post is None: 
                post = ''
            post_time = int(form.getvalue('time'))
            dt = datetime.datetime.fromtimestamp(post_time)
            blog_file = "../logs/blog_{}.txt".format(int(normalize_time(dt).timestamp()))
            with open(blog_file, 'w') as f:
                f.write(post)
            update_events("../logs", ".") # defined in export_events.py
            result = 'OK'
    
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(result.encode())

    def log_message(self, *args):
        pass


class ULogmeServer(Process):

    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port

    def run(self):
        os.chdir('render')
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        httpd = socketserver.ThreadingTCPServer((self.ip, self.port), CustomHandler)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.server_close()
