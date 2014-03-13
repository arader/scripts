#!/usr/bin/env python

import curses
import json
import math
import os
import signal
import subprocess
import time

class Mapper:
    fibs = [0,1,2,3]

    offset_left = 1
    offset_top = 0

    compass_top_height = 2
    compass_left_width = 4

    map_width = 71
    map_height = 23

    map_lines = [
        "           . _..::__:  ,-\"-\"._       |7       ,     _,.__             ",
        "   _.___ _ _<_>`!(._`.`-.    /        _._     `_ ,_/  '  '-._.---.-.__",
        " .{     \" \" `-==,',._\{  \  / {)     / _ \">_,-' `                mt-2_",
        "  \_.:--.       `._ )`^-. \"'      , [_/(                       __,/-' ",
        " '\"'     \         \"    _L       oD_,--'                )     /. (|   ",
        "          |           ,'         _)_.\\._<> 6              _,' /  '   ",
        "          `.         /          [_/_'` `\"(                <'}  )      ",
        "           \\    .-. )          /   `-'\"..' `:._          _)  '       ",
        "    `        \  (  `(          /         `:\  > \  ,-^.  /' '         ",
        "              `._,   \"\"        |           \`'   \|   ?_)  {\         ",
        "                 `=.---.       `._._       ,'     \"`  |' ,- '.        ",
        "                   |    `-._        |     /          `:`<_|h--._      ",
        "                   (        >       .     | ,          `=.__.`-'\     ",
        "                    `.     /        |     |{|              ,-.,\     .",
        "                     |   ,'          \   / `'            ,\"     \     ",
        "                     |  /             |_'                |  __  /     ",
        "                     | |                                 '-'  `-'   \.",
        "                     |/                                        \"    / ",
        "                     \.                                            '  ",
        "                                                                      ",
        "                      ,/           ______._.--._ _..---.---------._   ",
        "     ,-----\"-..?----_/ )      _,-'\"             \"                  (   ",
        " .._(                  `-----'                                      `- ",
        ]

    def __init__(self):
        self.quit = False
        self.inbound_coords = []
        self.my_coords = []
        self.routes = []

    def update_data(self):
        self.my_coords = [[47, -122]]
        self.inbound_coords = [[41.48222, -81.6697], [-90.1111, -122], [-90, -180]]

        for fib in Mapper.fibs:
            ip, country, city = self.get_host_info(fib)

            self.routes.append([fib, ip, country, city])

    def draw_map(self, map_pad):
        y = 0
        for line in Mapper.map_lines:
            map_pad.addstr(y, 0, line, curses.color_pair(1))
            y += 1

        for coord in self.my_coords:
            x, y = self.lat_long_to_x_y(coord[0], coord[1])
            map_pad.addch(y, x, 'x', curses.color_pair(2))

        for coord in self.inbound_coords:
            x, y = self.lat_long_to_x_y(coord[0], coord[1])
            map_pad.addch(y, x, 'x', curses.color_pair(3))

    def draw_map_border(self, stdscr):
        long_markers = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
        lat_markers = [90, 60, 30, 0, -30, -60, -90]
        height, width = stdscr.getmaxyx()
        right_edge = min(Mapper.offset_left + Mapper.compass_left_width + Mapper.map_width, width - 1)
        bottom_edge = min(Mapper.offset_top + Mapper.compass_top_height + Mapper.map_height, height - 1)

        for x in range(Mapper.offset_left + Mapper.compass_left_width, right_edge):
            stdscr.addch(Mapper.offset_top + Mapper.compass_top_height - 1, x, '-', curses.color_pair(4))
            stdscr.addch(bottom_edge, x, '-', curses.color_pair(4))

        for y in range(Mapper.offset_top + Mapper.compass_top_height, bottom_edge):
            stdscr.addstr(y, Mapper.offset_left + Mapper.compass_left_width - 1, "|", curses.color_pair(4))
            stdscr.addstr(y, right_edge, "|", curses.color_pair(4))

        for marker in long_markers:
            x,y = self.lat_long_to_x_y(0, marker)
            label = "{0}".format(int(math.fabs(marker)))

            if (marker % 180 and marker < 0):
                label += "W"

                if (not len(label) % 2):
                    label += " "
            elif (marker % 180 and marker > 0):
                label += "E"

                if (not len(label) % 2):
                    label = " " + label
            elif (marker == 0):
                label = "000"

            x += Mapper.offset_left + Mapper.compass_left_width

            label_x = x - int(round((len(label) / 2), 0))

            if (x > right_edge):
                break

            stdscr.addch(Mapper.offset_top + 1, x, '+', curses.color_pair(4))
            stdscr.addch(bottom_edge, x, '+', curses.color_pair(4))

            if (label_x + len(label) <= right_edge + 2):
                stdscr.addstr(Mapper.offset_top, label_x, label, curses.color_pair(4))

        for marker in lat_markers:
            x,y = self.lat_long_to_x_y(marker, 0)
            label = "{0}".format(int(math.fabs(marker)))

            if (marker < 0):
                label += "S"
            elif (marker > 0):
                label += "N"
            else:
                label = "000"

            y += Mapper.offset_top + Mapper.compass_top_height

            if (y > bottom_edge):
                break

            stdscr.addstr(y, Mapper.offset_left, label + "+", curses.color_pair(4))
            stdscr.addstr(y, right_edge, "+", curses.color_pair(4))

    def draw_cpl(self, cpl_pad):
        y = 0
        for route in self.routes:
            if (route[1]):
                locale = "%s, %s" % (route[3], route[2])

                cpl_pad.addstr(y, 0, "%s" % route[0], curses.color_pair(4))
                cpl_pad.addstr(y, 3, route[1], curses.color_pair(1))
                cpl_pad.addstr(y, Mapper.map_width - len(locale) - 1, locale, curses.color_pair(2))
            else:
                cpl_pad.addstr(y, 0, "%s" % route[0], curses.color_pair(4))
                cpl_pad.addstr(y, 3, "DOWN", curses.color_pair(3))

            y += 1

    def lat_long_to_x_y(self, lat, long):
        # map is 71x23
        # lat goes from -90 to +90
        # long goes from -180 to +180
        # 35,11 is 0N,0W

        dx = (long + 180)
        dy = (-1 * lat + 90)

        if (dx > 360):
            dx = 360

        if (dy > 180):
            dy = 180

        x = int(round(dx * ((Mapper.map_width - 1) / 360.0), 0))
        y = int(round(dy * ((Mapper.map_height - 1) / 180.0), 0))

        return x, y

    def get_host_info(self, fib):
        ip = None
        country = None
        city = None

        try:
            with open(os.devnull, 'w') as dev_null:
                data = json.loads(subprocess.check_output(["setfib", "%s" % fib, "curl", "-s", "http://api.hostip.info/get_json.php"], stderr=dev_null))

            ip = data['ip']
            country = data['country_code']
            city = data['city']
        except:
            ip = None
            country = None
            city = None

        return ip, country, city

    def process_input(self, value):
        if (value == ord("q")):
            self.quit = True
        elif (value == ord("a")):
            Mapper.offset_top += 1
        elif (value == ord("b")):
            Mapper.offset_left += 1

    def run(self, stdscr):
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)

        # getch should be none blocking
        stdscr.nodelay(1)

        map_pad = curses.newpad(Mapper.map_height + 1, Mapper.map_width + 1)
        cpl_pad = curses.newpad(len(self.fibs), Mapper.map_width + 1)

        refresh = True
        last_updated = time.time() - 1000

        while not self.quit:
            height, width = stdscr.getmaxyx()

            if (time.time() - last_updated > 300):
                self.update_data()
                refresh = True

            if (refresh):
                stdscr.clear()
                map_pad.clear()
                self.draw_map_border(stdscr)
                self.draw_map(map_pad)
                self.draw_cpl(cpl_pad)

                refresh = False
                last_updated = time.time()

            ch = stdscr.getch()
            stdscr.refresh()
            map_pad_y = Mapper.offset_top + Mapper.compass_top_height
            map_pad_x = Mapper.offset_left + Mapper.compass_left_width
            map_pad_h = min(map_pad_y + Mapper.map_height - 1, height - 1)
            map_pad_w = min(map_pad_x + Mapper.map_width - 1, width - 1)
            map_pad.refresh(0,0, map_pad_y,map_pad_x, map_pad_h,map_pad_w)

            if (height > Mapper.map_height + 3):
                cpl_pad.refresh(0,0, Mapper.map_height + 3,5, height - 1,width - 3)

            if (ch != -1):
                self.process_input(ch)
                refresh = True
            else:
                time.sleep(0.250)

def sigwinch(signum, frame):
    curses.endwin()
    curses.initscr()

def main(stdscr):
    mapper = Mapper()
    mapper.run(stdscr)

if __name__ =='__main__':
    signal.signal(signal.SIGWINCH, sigwinch)
    curses.wrapper(main)
