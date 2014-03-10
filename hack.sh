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
tmux split-window -h
tmux split-window -h "tail -f /var/log/messages"
tmux split-window -h "htop -d 50"

tmux select-layout "2b60,271x66,0,0{109x66,0,0[109x33,0,0,415,109x32,0,34,427],80x66,110,0[80x33,110,0,419,80x32,110,34,428],80x66,191,0[80x42,191,0,425,80x14,191,43,430,80x8,191,58,431]}" > /dev/null
