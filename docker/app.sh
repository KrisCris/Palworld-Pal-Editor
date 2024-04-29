#!/bin/bash

if [ ! -z "$PUID" ] && [ ! -z "$PGID" ]; then
    usermod -u $PUID pn
    groupmod -g $PGID pn
fi

cmd="gosu pn:pn python -m palworld_pal_editor --nocli --path=\"/mnt/gamesave\""

if [ -n "$APP_LANG" ]; then cmd="$cmd --lang=\"$APP_LANG\""; fi
if [ -n "$APP_PORT" ]; then cmd="$cmd --port=$APP_PORT"; fi
if [ -n "$MODE" ]; then cmd="$cmd --mode=\"$MODE\""; fi
if [ -n "$PASSWORD" ]; then cmd="$cmd --password=\"$PASSWORD\""; fi

echo "Launching: $cmd"

eval "$cmd"