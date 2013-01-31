#!/bin/bash

set -v

sudo cp tools/logrotate.d/* /etc/logrotate.d/

sudo mkdir $1 && sudo chown $2 $1

