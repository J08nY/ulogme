#!/usr/bin/env python

from utils import ULogmeServer
import sys

if __name__ == "__main__":
    # Port settings
    if len(sys.argv) > 1:
        PORT = int(sys.argv[1])
    else:
        PORT = 8124

    # serve render/ folder, not current folder
    print ('Serving ulogme, see it on http://ulogme.localhost:' + str(PORT))
    server = ULogmeServer("", PORT)
    server.start()
