#!/bin/bash

# Somewhat sloppy but hopefully complete script for installing the 
# tukey middleware.  Meant mostly for thourough documentation.

# settings for running tukey on the same node as the cloud controller
declare -A PORTS=( ["auth"]=5100 ["nova"]=8874 ["glance"]=9392)
declare -A WSGI_DIRS=( ["auth"]="auth_proxy" ["nova"]="tukey_cli" ["glance"]="tukey_cli")

PROXY_HOST="127.0.0.2"

CREATE_NEW_INTERFACE=true
CLONE_MIDDLEWARE=true

TEMP_DIR=tukey-middleware

#INSTALL_PRE=true
INSTALL_PRE=false

CONFIG_BASE_DIR=/var/www/tukey/config/middleware
LOCAL_SETTINGS_FILE=$CONFIG_BASE_DIR/local_settings.py
CONFIG_GEN_SETTINGS_FILE=$CONFIG_BASE_DIR/settings.py
PGP_KEY_DIR=$CONFIG_BASE_DIR/keys

MIDDLEWARE_REPO=http://git.bionimbus.org/git/tukey/tukey-middleware.git
TEMP_DIR=tukey-middleware

# make this be an absolute url
MIDDLEWARE_DIR=/var/www/tukey/tukey-middleware

TUKEY_USER=tukey
TUKEY_GROUP=tukey

APACHE_SITES_AVAILABLE=/etc/apache2/sites-available

