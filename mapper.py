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

    def calc_targets(self):
        targets = [[47, -122]]
        return targets

    def draw_map(self, map_pad):
        y = 0
        for line in Mapper.map_lines:
            map_pad.addstr(y, 0, line, curses.color_pair(1))
            y += 1

        for target in self.calc_targets():
            x, y = self.lat_long_to_x_y(target[0], target[1])
            map_pad.addch(y, x, 'x', curses.color_pair(3))

    def draw_map_border(self, stdscr):
        long_markers = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
        lat_markers = [90, 60, 30, 0, -30, -60, -90]
        height, width = stdscr.getmaxyx()
        right_edge = min(Mapper.map_width + 5, width - 2)
        bottom_edge = min(Mapper.map_height + 2, height - 1)

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

            label_x = x + 5 - int(round((len(label) / 2), 0))

            if (label_x + len(label) > width - 1):
                break

            stdscr.addstr(0, label_x, label, curses.color_pair(4))

        for x in range(4, right_edge + 1):
            ch = "-" if (x - 4) % 6 else "+"
            stdscr.addch(1, x, ch, curses.color_pair(4))

        for y in range(2, bottom_edge):
            stdscr.addstr(y, 4, "|", curses.color_pair(4))
            stdscr.addstr(y, right_edge, "|", curses.color_pair(4))

        for marker in lat_markers:
            x,y = self.lat_long_to_x_y(marker, 0)
            label = "{0}".format(int(math.fabs(marker)))

            if (marker < 0):
                label += "S"
            elif (marker > 0):
                label += "N"
            else:
                label = "000"

            if (y + 2 > height - 1):
                break

            stdscr.addstr(y + 2, 1, label + "+", curses.color_pair(4))

        for x in range(4, right_edge + 1):
            ch = "-" if (x - 4) % 6 else "+"
            stdscr.addch(bottom_edge, x, ch, curses.color_pair(4))

    def draw_cpl(self, cpl_pad):
        y = 0
        for fib in self.fibs:
            ip, country, city = self.get_host_info(fib)

            if (ip):
                locale = "%s, %s" % (city, country)

                cpl_pad.addstr(y, 0, "%s" % fib, curses.color_pair(4))
                cpl_pad.addstr(y, 3, ip, curses.color_pair(1))
                cpl_pad.addstr(y, Mapper.map_width - len(locale) - 1, locale, curses.color_pair(2))
            else:
                cpl_pad.addstr(y, 0, "%s" % fib, curses.color_pair(4))
                cpl_pad.addstr(y, 3, "DOWN", curses.color_pair(3))

            y += 1

    def lat_long_to_x_y(self, lat, long):
        # map is 71x23
        # lat goes from -90 to +90
        # long goes from -180 to +180
        # 35,11 is 0N,0W
        x = int(round(math.floor(Mapper.map_width / 2) + ((Mapper.map_width / 360.0) * long), 0))
        y = int(round(math.floor(Mapper.map_height / 2) - ((Mapper.map_height / 180.0) * lat), 0))

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

    def run(self, stdscr):
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)

        # getch should be none blocking
        stdscr.nodelay(1)

        map_pad = curses.newpad(Mapper.map_height, Mapper.map_width + 1)
        cpl_pad = curses.newpad(len(self.fibs), Mapper.map_width + 1)

        update = True
        last_updated = None

        while not self.quit:
            height, width = stdscr.getmaxyx()

            if (update or time.time() - last_updated > 300):
                stdscr.clear()
                map_pad.clear()
                self.draw_map_border(stdscr)
                self.draw_map(map_pad)
                self.draw_cpl(cpl_pad)

                update = False
                last_updated = time.time()

            ch = stdscr.getch()
            stdscr.refresh()
            map_pad.refresh(0,0, 2,5, min(height - 2, Mapper.map_height + 1),min(width - 3, Mapper.map_width + 3))

            if (height > Mapper.map_height + 3):
                cpl_pad.refresh(0,0, Mapper.map_height + 3,5, height,width - 3)

            if (ch != -1):
                self.process_input(ch)
                update = True
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
