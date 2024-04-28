#!/bin/bash

if [ ! -z "$PUID" ] && [ ! -z "$PGID" ]; then
    usermod -u $PUID pn
    groupmod -g $PGID pn
fi

cmd="python -m palworld_pal_editor --nocli"

if [ -n "$APP_LANG" ]; then cmd="$cmd --lang=\"$APP_LANG\""; fi
if [ -n "$APP_PORT" ]; then cmd="$cmd --port=$APP_PORT"; fi
if [ -n "$MODE" ]; then cmd="$cmd --mode=\"$MODE\""; fi
if [ -n "$SAVE_PATH" ]; then cmd="$cmd --path=\"$SAVE_PATH\""; fi
if [ -n "$PASSWORD" ]; then cmd="$cmd --password=\"$PASSWORD\""; fi

echo "Launching: $cmd"

eval "$cmd"