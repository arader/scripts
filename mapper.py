#!/usr/bin/env python

import curses
import json
import locale
import math
import os
import re
import signal
import subprocess
import time

encoding = locale.getdefaultlocale()[1]

class Location:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

class Point:
    def __init__(self, lat, lon, color, symbol='x'):
        self.lat = lat
        self.lon = lon
        self.color = color
        self.symbol = symbol

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

    lon_markers = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
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
        self.points = []
        self.routes = []
        self.last_updated = None

    def update_data(self, redraw):
        self.points = []
        self.routes = []

        if (not self.last_updated):
            self.last_updated = time.time() - 500
            return redraw

        if (time.time() - self.last_updated < 300):
            return redraw

        hosts = self.get_connected_hosts()
        host_locs = self.get_ip_info(hosts)

        for loc in host_locs:
            self.points.append(Point(loc.lat, loc.lon, Mapper.red_on_black))

        for fib in Mapper.fibs:
            ip, lat, lon, country, region, city = self.get_route_info(fib)

            if (lat and lon):
                self.points.append(Point(lat, lon, Mapper.yellow_on_black))

            self.routes.append([fib, ip, country, region, city])

        self.last_updated = time.time()

        return True

    def get_route_info(self, fib):
        ip = None
        lat = None
        lon = None
        country = None
        region = None
        city = None
        data = None

        try:
            with open(os.devnull, 'w') as dev_null:
                data = json.loads(subprocess.check_output(["setfib", "%s" %fib, "curl", "-s", "http://api.0x666.tk/ip"], stderr=dev_null).decode(encoding))

            ip = data['Response'][0]['Address']
            lat = data['Response'][0]['GeoLoc']['Latitude']
            lon = data['Response'][0]['GeoLoc']['Longitude']
            country = data['Response'][0]['GeoLoc']['Country']
            region = data['Response'][0]['GeoLoc']['Region']
            city = data['Response'][0]['GeoLoc']['City']
        except:
            pass

        return ip, lat, lon, country, region, city

    def get_connected_hosts(self):
        hosts = []

        with open(os.devnull, 'w') as dev_null:
            pattern = re.compile('\S+[ ]+\S+[ ]+\S+[ ]+\S+[ ]+([0-9a-f.:]+)\.[0-9]+')
            lines = subprocess.check_output(["netstat", "-f", "inet", "-n"]).decode(encoding).split('\n')

            for line in lines:
                match = pattern.match(line)
                if (match):
                    hosts.append(match.group(1))

        return hosts

    def get_ip_info(self, ips):
        locs = []

        try:
            with open(os.devnull, 'w') as dev_null:
                data = json.loads(subprocess.check_output(["curl", "-s", "http://api.0x666.tk/ip?a=" + ','.join(ips)], stderr=dev_null).decode(encoding))

            for loc in data['Response']:
                lat = loc['GeoLoc']['Latitude']
                lon = loc['GeoLoc']['Longitude']

                locs.append(Location(lat, lon))
        except:
            pass

        return locs

    def draw_map(self, map_pad):
        max_y, max_x = map_pad.getmaxyx()

        map_pad.border()

        for marker in Mapper.lon_markers:
            x,y = self.lat_lon_to_x_y(0, marker)

            if (x >= max_x - Mapper.border_size):
                break

            # don't draw at corners
            if (x == 0 or x == max_x - 1):
                continue

            map_pad.addch(0, x, curses.ACS_TTEE)
            map_pad.addch(max_y - 1, x, curses.ACS_BTEE)

        for marker in Mapper.lat_markers:
            x,y = self.lat_lon_to_x_y(marker, 0)

            if (y >= max_y - Mapper.border_size):
                break;

            # don't draw at corners
            if (y == 0 or y == max_y - 1):
                continue

            map_pad.addch(y, 0, curses.ACS_LTEE)
            map_pad.addch(y, max_x - 1, curses.ACS_RTEE)

        for y in range(0, min(max_y - 2, len(Mapper.map_lines))):
            for x in range(0, min(max_x - 2, len(Mapper.map_lines[y]))):
                    map_pad.addch(y + 1, x + 1, Mapper.map_lines[y][x], Mapper.green_on_black)

        for point in self.points:
            x, y = self.lat_lon_to_x_y(point.lat, point.lon)
            if (x < max_x - Mapper.border_size and y < max_y - Mapper.border_size):
                map_pad.addch(y, x, point.symbol, point.color)

    def draw_compass(self, stdscr, map_pad_y, map_pad_x, map_pad_h, map_pad_w):
        height, width = stdscr.getmaxyx()
        right_edge = max(map_pad_x + map_pad_w, width)
        bottom_edge = map_pad_y + map_pad_h

        for marker in Mapper.lon_markers:
            x,y = self.lat_lon_to_x_y(0, marker)
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

            for i in range(0, len(label)):
                if (label_x + i >= right_edge):
                    break

                stdscr.addch(Mapper.offset_top, label_x + i, label[i], Mapper.cyan_on_black)

        for marker in Mapper.lat_markers:
            x,y = self.lat_lon_to_x_y(marker, 0)
            label = "{0}".format(int(math.fabs(marker)))

            if (marker < 0):
                label += "S"
            elif (marker > 0):
                label += "N"
            else:
                label = "000"

            y += Mapper.offset_top + Mapper.compass_top_height

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
                locale = ""

                if (route[4] and route[3] and route[2]):
                    locale = "%s %s, %s" % (route[4], route[3], route[2])
                elif (route[4] and route[2]):
                    locale = "%s, %s" % (route[4], route[2])
                elif (route[3] and route[2]):
                    locale = "%s, %s" % (route[3], route[2])
                elif (route[2]):
                    locale = "%s" % route[2]
                else:
                    locale = "UNKNOWN"

                locale_x = max(route_ip_x + len(route_ip) + 1, max_x - len(locale) - 1)

                for i in range(0, min(len(locale), max_x - locale_x - 1)):
                    cpl_pad.addch(y, locale_x + i, locale[i], Mapper.yellow_on_black)

            y += 1

            if (y >= max_y - 1):
                break

    def lat_lon_to_x_y(self, lat, lon):
        # map is 71x23
        # lat goes from -90 to +90
        # lon goes from -180 to +180

        dx = (lon + 180)
        dy = (-1 * lat + 90)

        if (dx > 360):
            dx = 360

        if (dy > 180):
            dy = 180

        x = int(round(dx * ((Mapper.map_width + (2 * Mapper.border_size) - 1) / 360.0), 0))
        y = int(round(dy * ((Mapper.map_height + (2 * Mapper.border_size) - 1) / 180.0), 0))

        return x, y

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

            if (self.update_data(redraw)):
                redraw = True

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
