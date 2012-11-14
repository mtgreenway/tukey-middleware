#!/bin/bash

sudo -u postgres psql -c "CREATE DATABASE federated_auth;"
sudo -u postgres psql -c "CREATE USER cloudgui with PASSWORD '$1';"
sudo -u postgres psql federated_auth < auth_proxy/federated_auth.sql
