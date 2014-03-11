#!/usr/bin/env python

import curses
import json
import os
import subprocess
import time

fibs = [0,1,2,3]
quit = False
updated = None

def draw(stdscr):
    global updated

    if (updated == None or time.time() - updated > 300):
        y = 0
        max_y, max_x = stdscr.getmaxyx()

        for fib in fibs:
            if (y >= max_y):
                break;

            ip, country, city = get_host_info(fib)

            if (ip):
                locale = "%s, %s" % (city, country)

                stdscr.addstr(y, 1, "%s" % fib, curses.color_pair(4));
                stdscr.addstr(y, 4, ip, curses.color_pair(1));
                # python bug 8243 - can't draw in lower right
                stdscr.addstr(y, max_x - len(locale) - 1, locale, curses.color_pair(2))
            else:
                stdscr.addstr(y, 1, "%s" % fib, curses.color_pair(4));
                stdscr.addstr(y, 4, "DOWN", curses.color_pair(3));

            y += 1

        updated = time.time()

def get_host_info(fib):
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

    while not quit:
        draw(stdscr)

        ch = stdscr.getch()

        if (ch != -1):
            process_input(ch)
        else:
            time.sleep(0.250)

if __name__ =='__main__':
    curses.wrapper(main)
