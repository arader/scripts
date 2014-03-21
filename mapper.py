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

    border_size = 1

    min_cpl_height = 5

    compass_top_height = 1
    compass_bottom_height = 1
    compass_left_width = 3
    compass_right_width = 1

    map_width = 71
    map_height = 23

    long_markers = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
    lat_markers = [90, 60, 30, 0, -30, -60, -90]

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
        max_y, max_x = map_pad.getmaxyx()

        map_pad.border()

        for marker in Mapper.long_markers:
            x,y = self.lat_long_to_x_y(0, marker)

            x += Mapper.border_size

            if (x >= max_x - Mapper.border_size):
                break

            map_pad.addch(0, x, curses.ACS_TTEE)
            map_pad.addch(max_y - 1, x, curses.ACS_BTEE)

        for marker in Mapper.lat_markers:
            x,y = self.lat_long_to_x_y(marker, 0)

            y += Mapper.border_size

            if (y >= max_y - Mapper.border_size):
                break;

            map_pad.addch(y, 0, curses.ACS_LTEE)
            map_pad.addch(y, max_x - 1, curses.ACS_RTEE)

        for y in range(0, min(max_y - 2, len(Mapper.map_lines))):
            for x in range(0, min(max_x - 2, len(Mapper.map_lines[y]))):
                    map_pad.addch(y + 1, x + 1, Mapper.map_lines[y][x], Mapper.green_on_black)

        for coord in self.my_coords:
            x, y = self.lat_long_to_x_y(coord[0], coord[1])
            x += Mapper.border_size
            y += Mapper.border_size
            if (x < max_x - Mapper.border_size and y < max_y - Mapper.border_size):
                map_pad.addch(y, x, 'x', Mapper.yellow_on_black)

        for coord in self.inbound_coords:
            x, y = self.lat_long_to_x_y(coord[0], coord[1])
            x += Mapper.border_size
            y += Mapper.border_size
            if (x < max_x - Mapper.border_size and y < max_y - Mapper.border_size):
                map_pad.addch(y, x, 'x', Mapper.red_on_black)


    def draw_compass(self, stdscr, map_pad_y, map_pad_x, map_pad_h, map_pad_w):
        height, width = stdscr.getmaxyx()
        right_edge = map_pad_x + map_pad_w
        bottom_edge = map_pad_y + map_pad_h

        for marker in Mapper.long_markers:
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

            x += Mapper.offset_left + Mapper.compass_left_width + 1

            label_x = x - int(round((len(label) / 2), 0))

            if (x > right_edge):
                break

            for i in range(0, len(label)):
                if (label_x + i >= right_edge):
                    break

                stdscr.addch(Mapper.offset_top, label_x + i, label[i], Mapper.cyan_on_black)

        for marker in Mapper.lat_markers:
            x,y = self.lat_long_to_x_y(marker, 0)
            label = "{0}".format(int(math.fabs(marker)))

            if (marker < 0):
                label += "S"
            elif (marker > 0):
                label += "N"
            else:
                label = "000"

            y += Mapper.offset_top + Mapper.compass_top_height + 1

            if (y >= bottom_edge):
                break

            stdscr.addstr(y, Mapper.offset_left, label, Mapper.cyan_on_black)

    def draw_cpl(self, cpl_pad):
        max_y, max_x = cpl_pad.getmaxyx()

        cpl_pad.border()
        y = Mapper.border_size

        for route in self.routes:
            route_idx = "%s" % route[0]
            route_idx_x = Mapper.border_size
            route_ip = route[1] if route[1] else "DOWN"
            route_ip_color = Mapper.green_on_black if route[1] else Mapper.red_on_black
            route_ip_x = route_idx_x + len(route_idx) + 1

            for i in range(0, min(len(route_idx), max_x - route_idx_x - 1)):
                cpl_pad.addch(y, route_idx_x + i, route_idx[i], Mapper.cyan_on_black)

            for i in range(0, min(len(route_ip), max_x - route_ip_x - 1)):
                cpl_pad.addch(y, route_ip_x + i, route_ip[i], route_ip_color)

            if (route[1]):
                locale = "%s, %s" % (route[3], route[2])
                locale_x = max(route_ip_x + len(route_ip) + 1, max_x - len(locale) - 1)

                for i in range(0, min(len(locale), max_x - locale_x - 1)):
                    cpl_pad.addch(y, locale_x + i, locale[i], Mapper.yellow_on_black)

            y += 1

            if (y >= max_y - 1):
                break

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

            ip = data['ip'].encode()
            country = data['country_code'].encode()
            city = data['city'].encode()
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
        Mapper.green_on_black = curses.color_pair(1)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        Mapper.yellow_on_black = curses.color_pair(2)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        Mapper.red_on_black = curses.color_pair(3)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        Mapper.cyan_on_black = curses.color_pair(4)

        redraw = True
        last_updated = time.time() - 1000

        map_pad = None
        map_pad_y = None
        map_pad_x = None
        map_pad_h = None
        map_pad_w = None

        cpl_pad = None
        cpl_pad_y = None
        cpl_pad_x = None
        cpl_pad_h = None
        cpl_pad_w = None

        input_pad = curses.newpad(1,1)
        input_pad.nodelay(1)

        while not self.quit:

            if (time.time() - last_updated > 300):
                self.update_data()
                redraw = True
                last_updated = time.time()

            if (redraw):
                max_y, max_x = stdscr.getmaxyx()

                map_pad_y = Mapper.offset_top + Mapper.compass_top_height
                map_pad_x = Mapper.offset_left + Mapper.compass_left_width

                cpl_pad_y = min(max_y - (Mapper.min_cpl_height + (2 * Mapper.border_size)), map_pad_y + Mapper.map_height + (2 * Mapper.border_size))
                cpl_pad_x = map_pad_x

                cpl_pad_h = max_y - cpl_pad_y
                cpl_pad_w = min(Mapper.map_width + (2 * Mapper.border_size), max_x - (Mapper.compass_left_width + Mapper.offset_left))

                map_pad_h = cpl_pad_y - map_pad_y
                map_pad_w = cpl_pad_w

                stdscr.clear()

                if (map_pad_h > 0 and map_pad_w > 0):
                    map_pad = curses.newpad(map_pad_h, map_pad_w)
                    cpl_pad = curses.newpad(cpl_pad_h, cpl_pad_w)

                    self.draw_compass(stdscr, map_pad_y, map_pad_x, map_pad_h, map_pad_w)
                    self.draw_map(map_pad)
                    self.draw_cpl(cpl_pad)

                    stdscr.refresh()
                    map_pad.refresh(0,0, map_pad_y,map_pad_x, map_pad_y + map_pad_h,map_pad_x + map_pad_w)
                    cpl_pad.refresh(0,0, cpl_pad_y,cpl_pad_x, cpl_pad_y + cpl_pad_h,cpl_pad_x + cpl_pad_w)

                redraw = False

            ch = input_pad.getch()

            if (ch != -1):
                self.process_input(ch)
                redraw = True
            else:
                time.sleep(0.5)

def sigwinch(signum, frame):
    curses.endwin()
    curses.initscr()

def main(stdscr):
    mapper = Mapper()
    mapper.run(stdscr)

if __name__ =='__main__':
    signal.signal(signal.SIGWINCH, sigwinch)
    curses.wrapper(main)
