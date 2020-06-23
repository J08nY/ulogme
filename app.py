#!/usr/bin/env python

import signal
import subprocess
from threading import Thread, Event
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
from gi.repository import GLib as glib
from gi.repository import AppIndicator3 as appindicator
import dbus
from dbus.mainloop.glib import DBusGMainLoop

from utils import normalize_time, ULogmeServer


class WorkerThread(Thread):
    keep_running: bool = True
    not_screensaver: Event
    
    def __init__(self, not_screensaver):
        super().__init__()
        self.not_screensaver = not_screensaver

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
            if not self.not_screensaver.is_set():
                win_title = "__LOCKEDSCREEN"
            else:
                win_num = subprocess.run(["xdotool", "getactivewindow"], stdout=subprocess.PIPE, text=True).stdout[:-1]
                win_title = subprocess.run(["xdotool", "getwindowname", win_num], stdout=subprocess.PIPE, text=True).stdout[:-1]
            if win_title != last_title:
                self.log(win_title)
            last_title = win_title
            if win_title == "__LOCKEDSCREEN":
                self.not_screensaver.wait()
            else:
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
    window_log: Optional[WindowLog] = None
    keystroke_log: Optional[KeyStrokeLog] = None
    server: Optional[ULogmeServer] = None
    not_screensaver: Event

    def __init__(self, mainloop):
        gtk.Application.__init__(self, application_id="sk.neuromancer.ulogme", flags=gio.ApplicationFlags.FLAGS_NONE)
        self.mainloop = mainloop
        self.dbus_mainloop = DBusGMainLoop()
        self.bus = dbus.SessionBus(mainloop=self.dbus_mainloop)
        self.bus.add_signal_receiver(self.dbus_screensaver, dbus_interface="org.gnome.ScreenSaver", path="/org/gnome/ScreenSaver", member_keyword="member")
        self.not_screensaver = Event()
        self.not_screensaver.set()
        
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
        self.item_toggle_serve = gtk.MenuItem(label="Start server")
        self.item_toggle_serve.connect("activate", self.toggle_server)
        self.menu.append(item_start)
        self.menu.append(item_stop)
        self.menu.append(gtk.SeparatorMenuItem())
        self.menu.append(self.item_toggle_serve)
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
            self.window_log = WindowLog(self.not_screensaver)
            self.window_log.start()
            self.keystroke_log = KeyStrokeLog(self.not_screensaver)
            self.keystroke_log.start()
            self.running = True

    def dbus_screensaver(self, *args, member=None):
        if member == "ActiveChanged":
            if args[0]:
                self.not_screensaver.clear()
            else:
                self.not_screensaver.set()

    def toggle_server(self, *args):
        if self.server is None:
            self.server = ULogmeServer("", 8124)
            self.server.start()
            self.item_toggle_serve.set_label("Stop server")
        else:
            self.server.terminate()
            self.server.join()
            self.server.close()
            self.server = None
            self.item_toggle_serve.set_label("Start server")

    def stop(self, *args):
        if self.running:
            self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
            self.window_log.keep_running = False
            self.keystroke_log.keep_running = False
            self.running = False

    def quit(self, *args):
        self.stop()
        if self.server is not None:
            self.server.terminate()
            self.server.join()
            self.server.close()
        self.mainloop.quit()


if __name__ == "__main__":
    mainloop = glib.MainLoop()
    app = ULogme(mainloop=mainloop)
    app.run(sys.argv)
    mainloop.run()
