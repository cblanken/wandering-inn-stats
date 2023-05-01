#!/bin/sh
#
# NordVPN cycle script to download all chapter in batches

nordvpn c United_States
python get.py 0 100

nordvpn c United_Kingdom
python get.py 100 200

nordvpn c Finland
python get.py 200 300

nordvpn c Germany
python get.py 300 400

nordvpn c Spain
python get.py 400 500

nordvpn c Mexico
python get.py 500 600

nordvpn c France
python get.py 600 700
