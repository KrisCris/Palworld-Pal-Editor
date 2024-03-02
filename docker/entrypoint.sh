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

echo "launching..."
# Execute setup_and_run script with environment variables as arguments
exec gosu pn ./setup_and_run.sh --lang "$APP_LANG" --port $APP_PORT --mode "$MODE" --path "$SAVE_PATH" --password "$PASSWORD" "$PY_INTERACTIVE_FLAG"

