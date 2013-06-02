echo 127.0.0.1 torque-node$(ip a s eth0|grep inet|head -n1|cut -d' ' -f6|cut -d/ -f1|tr . -) >> /etc/hosts
chown root:root $TORQ_CONF_FILE
mv $TORQ_CONF_FILE /etc/ld.so.conf.d/torque.conf
ldconfig
/glusterfs/users/torque_nodes/setup_scripts/torque-package-mom-linux-x86_64.sh --install
/glusterfs/users/torque_nodes/setup_scripts/torque-package-clients-linux-x86_64.sh --install
chown root:root $CONF_FILE
mv $CONF_FILE /var/spool/torque/mom_priv/config
killall -9 pbs_mom
ldconfig
pbs_mom
