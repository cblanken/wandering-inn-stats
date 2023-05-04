#!/bin/sh
#
# NordVPN cycle script to download all chapter in batches

nordvpn c United_States
python manage.py get_volumes 0 1

nordvpn c United_Kingdom
python manage.py get_volumes 1 1

nordvpn c Finland
python manage.py get_volumes 2 1

nordvpn c Germany
python manage.py get_volumes 3 1

nordvpn c Spain
python manage.py get_volumes 4 1

nordvpn c Mexico
python manage.py get_volumes 5 1

nordvpn c France
python manage.py get_volumes 6 1

nordvpn c Estonia
python manage.py get_volumes 7 1

nordvpn c Austria
python manage.py get_volumes 8 1

nordvpn d
