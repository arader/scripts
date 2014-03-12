#!/usr/bin/env python

import curses
import json
import math
import os
import subprocess
import time

quit = False

map = [
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
    ]

def calc_targets():
    targets = [[47, -122]]

    return targets

def draw(map_pad):
    y = 0
    for line in map:
        map_pad.addstr(y, 0, line, curses.color_pair(1))
        y += 1

    for target in calc_targets():
        x, y = lat_long_to_x_y(target[0], target[1])
        map_pad.addch(y, x, 'x', curses.color_pair(3))

def draw_map_border(all_pad):
    long_markers = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
    lat_markers = [90, 60, 30, 0, -30, -60]
    # draw the top row of longitude markers
    longitude_border = "+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+"
    
    for marker in long_markers:
        x,y = lat_long_to_x_y(0, marker)
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

        all_pad.addstr(0, x + 4 - int(round((len(label) / 2), 0)), label, curses.color_pair(4))

    all_pad.addstr(1, 3, longitude_border, curses.color_pair(4))

    for y in range(2,21):
        all_pad.addstr(y, 3, "|", curses.color_pair(4))
        all_pad.addstr(y, 75, "|", curses.color_pair(4))

    for marker in lat_markers:
        x,y = lat_long_to_x_y(marker, 0)
        label = "{0}".format(int(math.fabs(marker)))

        if (marker < 0):
            label += "S"
        elif (marker > 0):
            label += "N"
        else:
            label = "000"

        all_pad.addstr(y + 2, 0, label + "+", curses.color_pair(4))

    all_pad.addstr(21, 3, longitude_border, curses.color_pair(4))

def lat_long_to_x_y(lat, long):
    # map is 71x23
    # lat goes from -90 to +90
    # long goes from -180 to +180
    # 35,11 is 0N,0W
    x = int(round(35 + ((71 / 360.0) * long), 0))
    y = int(round(11 - ((23 / 180.0) * lat), 0))

    return x, y

def process_input(value):
    if (value == ord("q")):
        global quit
        quit = True

def main(stdscr):
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)

    # getch should be none blocking
    stdscr.nodelay(1)

    height, width = stdscr.getmaxyx()

    all_pad = curses.newpad(22, 76 + 1)
    map_pad = curses.newpad(19, 71 + 1)

    # refresh the screen once so getch doesn't do it
    stdscr.refresh()

    update = False
    last_updated = time.time() - 500

    while not quit:
        if (update or time.time() - last_updated > 300):
            draw_map_border(all_pad)
            all_pad.refresh(0,0, 0,1, height-1,width-1)
            draw(map_pad)
            map_pad.refresh(0,0, 2,5, 20,74)

            update = False
            last_updated = time.time()

        ch = stdscr.getch()

        if (ch != -1):
            process_input(ch)
            update = True
        else:
            time.sleep(0.250)

if __name__ =='__main__':
    curses.wrapper(main)
