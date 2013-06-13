#!/bin/bash
CONF_FILE=/tmp/torque_config
TORQ_CONF_FILE=/tmp/torque_config2

hostname torque-node$(ip a s eth0|grep inet|head -n1|cut -d' ' -f6|cut -d/ -f1|tr . -)
echo 127.0.0.1 torque-node$(ip a s eth0|grep inet|head -n1|cut -d' ' -f6|cut -d/ -f1|tr . -) >> /etc/hosts
chown root:root $TORQ_CONF_FILE
mv $TORQ_CONF_FILE /etc/ld.so.conf.d/torque.conf
ldconfig
/cloudconf/torque/setup_scripts/torque-package-mom-linux-x86_64.sh --install
/cloudconf/torque/setup_scripts/torque-package-clients-linux-x86_64.sh --install
chown root:root $CONF_FILE
mv $CONF_FILE /var/spool/torque/mom_priv/config
killall -9 pbs_mom
ldconfig
pbs_mom
