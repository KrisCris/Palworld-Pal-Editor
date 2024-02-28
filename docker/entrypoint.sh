#!/bin/bash
set -e

# Optionally, set the timezone based on the TZ environment variable
if [ -n "$TZ" ]; then
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
fi

# Update the IDs of the user and group "appuser" to match PUID and PGID provided by the user
if [ ! -z "$PUID" ] && [ ! -z "$PGID" ]; then
    usermod -u $PUID appuser
    groupmod -g $PGID appuser
fi

# Ensure the working directory is owned by the appuser, adjusting permissions as necessary
chown -R appuser:appuser /app

# Execute setup_and_run script with environment variables as arguments
exec gosu appuser ./setup_and_run.sh --lang $APP_LANG --port $APP_PORT "--$MODE" --path "$SAVE_PATH" "$PY_INTERACTIVE_FLAG"

