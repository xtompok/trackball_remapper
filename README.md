# Trackball Remapper
Python evdev script for remapping buttons of Logitech Trakball Marble

## Functions
 - swap left and right button (left-handed mode)
 - make right small button
    - when only clicking the middle button
    - click and move ball the "scroll modifier" - when holding right small button down the ball movement is interpretted as horizontal and vertical scrolling

## Requirements
 - `python3-evdev`

## Usage
 - `sudo python3 remapper.py`

## Autostart on boot (systemd)
1. Copy the project to a stable location (the service expects `/opt/trackball_remapper`):
    - `sudo mkdir -p /opt`
    - `sudo cp -r /path/to/trackball_remapper /opt/trackball_remapper`

2. Install the unit file:
    - `sudo cp /opt/trackball_remapper/trackball-remapper.service /etc/systemd/system/trackball-remapper.service`

3. Reload systemd, enable on boot, and start now:
    - `sudo systemctl daemon-reload`
    - `sudo systemctl enable --now trackball-remapper.service`

4. Check status/logs:
    - `sudo systemctl status trackball-remapper.service`
    - `journalctl -u trackball-remapper.service -f`
