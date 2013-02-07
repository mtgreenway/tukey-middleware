#!/bin/bash

# Somewhat sloppy but hopefully complete script for installing the 
# tukey middleware.  Meant mostly for thourough documentation.

declare -A PORTS=( ["auth"]=5000 ["nova"]=8774 ["glance"]=9292)
declare -A WSGI_DIRS=( ["auth"]="auth_proxy" ["nova"]="tukey_cli" ["glance"]="tukey_cli")

PROXY_HOST="localhost"

CREATE_NEW_INTERFACE=false
CLONE_MIDDLEWARE=true

TEMP_DIR=tukey-middleware

INSTALL_PRE=true

LOCAL_SETTINGS_FILE=/home/ubuntu/local_settings.py
CONFIG_GEN_SETTINGS_FILE=/home/ubuntu/settings.py
PGP_KEY_DIR=/home/ubuntu/keys

MIDDLEWARE_REPO=ssh://git@source.bionimbus.org/home/git/tukey-middleware.git
TEMP_DIR=tukey-middleware

# make this be an absolute url
MIDDLEWARE_DIR=/var/www/tukey/tukey-middleware

#TUKEY_USER=tukey
TUKEY_USER=ubuntu
#TUKEY_GROUP=tukey
TUKEY_GROUP=ubuntu

APACHE_SITES_AVAILABLE=/etc/apache2/sites-available
