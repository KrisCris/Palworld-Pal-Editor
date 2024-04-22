#!/bin/bash
set -e

# Optionally, set the timezone based on the TZ environment variable
if [ -n "$TZ" ]; then
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
fi

# Update the IDs of the user and group "appuser" to match PUID and PGID provided by the user
if [ ! -z "$PUID" ] && [ ! -z "$PGID" ]; then
    usermod -u $PUID pn
    groupmod -g $PGID pn
fi

# Ensure the working directory is owned by the appuser, adjusting permissions as necessary
chown -R pn:pn /app



cmd="gosu pn ./setup_and_run.sh"

# Check each environment variable and append it to the command if it exists
if [ -n "$APP_LANG" ]; then cmd="$cmd --lang=\"$APP_LANG\""; fi
if [ -n "$APP_PORT" ]; then cmd="$cmd --port=$APP_PORT"; fi
if [ -n "$MODE" ]; then cmd="$cmd --mode=\"$MODE\""; fi
if [ -n "$SAVE_PATH" ]; then cmd="$cmd --path=\"$SAVE_PATH\""; fi
if [ -n "$PASSWORD" ]; then cmd="$cmd --password=\"$PASSWORD\""; fi
if [ -n "$INTERACTIVE" ]; then cmd="$cmd --interactive=\"$INTERACTIVE\""; fi

echo "Launching: $cmd"

eval exec $cmd
