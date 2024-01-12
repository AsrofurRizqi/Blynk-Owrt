#!/bin/sh /etc/rc.common

START=95
STOP=01

USE_PROCD=1
SCRIPT="/usr/bin/owrtblynk.py"

start_service() {
    procd_open_instance
    procd_set_param command /usr/bin/python3 "$SCRIPT"
    procd_close_instance
}
stop() {
    echo "Stopping owrtblynk.py"
    pkill -f /usr/bin/owlrtblynk.py
}

# init.d script for owrtblynk.py , put it in /etc/init.d/ and chmod +x