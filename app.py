#!/usr/bin/env python

import signal
import subprocess
from threading import Thread
from typing import Optional
import datetime
import time
import sys
import os
import re
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk as gtk
from gi.repository import Gio as gio
from gi.repository import AppIndicator3 as appindicator

from utils import normalize_time


class WorkerThread(Thread):
    keep_running: bool = True

    def log(self, content: str):
        now = datetime.datetime.now()
        d = normalize_time(now)
        fname = f"logs/{self.LOG_NAME}_{d.strftime('%s')}.txt"
        with open(fname, "a") as f:
            f.write(now.strftime("%s") + " " + content + "\n")


class WindowLog(WorkerThread):
    LOG_NAME: str = "window"

    def run(self):
        last_title = None
        while self.keep_running:
            win_num = subprocess.run(["xdotool", "getactivewindow"], stdout=subprocess.PIPE, text=True).stdout[:-1]
            win_title = subprocess.run(["xdotool", "getwindowname", win_num], stdout=subprocess.PIPE, text=True).stdout[:-1]
            win_pid = subprocess.run(["xdotool", "getwindowpid", win_num], stdout=subprocess.PIPE, text=True).stdout[:-1]
            if win_title != last_title:
                self.log(win_title)
            last_title = win_title
            time.sleep(2)
        self.log("")


class KeyStrokeLog(WorkerThread):
    LOG_NAME: str = "keyfreq"
    mod_key_pattern = re.compile("(shift_[lr]|alt_[lr]|control_[lr]|caps_lock)", re.I)
    keyboard_pattern = re.compile("keyboard.*slave.*keyboard")
    keyboard_id_pattern = re.compile("id=([0-9]*)")
    
    def run(self):
        modmap = subprocess.run(["xmodmap", "-pk"], stdout=subprocess.PIPE, text=True).stdout[:-1]
        mod_keys = []
        for line in modmap.split("\n"):
            line = line.strip()
            if self.mod_key_pattern.search(line):
                mod_keys.append(line.split(" ")[0])
        xinput_all = subprocess.run(["xinput"], stdout=subprocess.PIPE, text=True).stdout[:-1]
        keyboard = None
        for line in xinput_all.split("\n"):
            if self.keyboard_pattern.search(line) and "Virtual" not in line and self.keyboard_id_pattern.search(line):
                keyboard = self.keyboard_id_pattern.search(line).group(1)
        if keyboard is None:
            raise ValueError("Could not detect keyboard.")
        while self.keep_running:
            process = subprocess.Popen(["xinput", "test", keyboard], stdout=subprocess.PIPE, text=True)
            for i in range(10):
                time.sleep(1)
                if not self.keep_running:
                    process.terminate()
                    break
            else:
                process.terminate()
            count = 0
            data = process.stdout.read()
            for line in data.split("\n"):
                if "release" in line:
                    count += 1
            if count != 0:
                self.log(str(count))
                

class ULogme(gtk.Application):
    indicator: appindicator.Indicator
    menu: gtk.Menu
    running: bool = False
    window_log: Optional[WindowLog]
    keystroke_log: Optional[KeyStrokeLog]

    def __init__(self):
        gtk.Application.__init__(self, application_id="sk.neuromancer.ulogme", flags=gio.ApplicationFlags.FLAGS_NONE)
        self.set_property("register-session", True)
        
        self.indicator = appindicator.Indicator.new('ulogme-appindicator', "", appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_icon_full(os.path.abspath("logo_passive.svg"), "Non-recording ulogme.")
        self.indicator.set_attention_icon_full(os.path.abspath("logo_active.svg"), "Recording ulogme.")
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

        self.menu = gtk.Menu()
        item_start = gtk.MenuItem(label="Start")
        item_start.connect("activate", self.start)
        item_stop = gtk.MenuItem(label="Stop")
        item_stop.connect("activate", self.stop)
        item_quit = gtk.MenuItem(label="Quit")
        item_quit.connect("activate", self.quit)
        self.menu.append(item_start)
        self.menu.append(item_stop)
        self.menu.append(gtk.SeparatorMenuItem())
        self.menu.append(item_quit)
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        signal.signal(signal.SIGINT, self.quit)

    def do_activate(self):
        gtk.Application.do_activate(self)

    def start(self, *args):
        if not self.running:
            self.indicator.set_status(appindicator.IndicatorStatus.ATTENTION)
            self.window_log = WindowLog()
            self.window_log.start()
            self.keystroke_log = KeyStrokeLog()
            self.keystroke_log.start()
            self.running = True

    def stop(self, *args):
        if self.running:
            self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
            self.window_log.keep_running = False
            self.keystroke_log.keep_running = False
            self.running = False

    def quit(self, *args):
        self.stop()
        gtk.main_quit()


if __name__ == "__main__":
    app = ULogme()
    app.run(sys.argv)
    gtk.main()
