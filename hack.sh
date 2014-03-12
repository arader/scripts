#!/bin/sh

tmux list-windows | grep "[0-9]*: hack" > /dev/null

if [ $? -eq 0 ]; then
    echo "hack.sh is already running"
    return 0
fi

# new window labeled 'hack'
tmux new-window -n "hack" irssi

tmux split-window -h
tmux split-window -h
tmux split-window -h
tmux select-layout tiled
tmux split-window -h "tail -f /var/log/messages"
tmux split-window -h "~/dev/scripts/mapper.py"
tmux split-window -h "~/dev/scripts/fibber.py"
tmux split-window -h "htop -d 50"

tmux select-layout "c55f,271x66,0,0{109x66,0,0[109x33,0,0,455,109x32,0,34,456],80x66,110,0[80x33,110,0,457,80x32,110,34,458],80x66,191,0[80x8,191,0,459,80x13,191,9,460,80x22,191,23,486,80x4,191,46,463,80x15,191,51,461]}" > /dev/null
