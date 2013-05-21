#!/bin/bash
CLUSTER_ID=%(cluster_id)s

if [ `whoami` != "%(username)s" ]
then
  exit 1
fi

# wait for gluster to come up
while ! ls /glusterfs/users/torque_nodes/setup_scripts/
do
    sleep 1
done

CONF_FILE=/tmp/torque_config
TORQ_CONF_FILE=/tmp/torque_config2
echo -ne '$pbsserver  ' > $CONF_FILE
echo "torque-headnode-$CLUSTER_ID" >> $CONF_FILE
echo '$logevent      225' >> $CONF_FILE
echo '$usecp *:/glusterfs/users /glusterfs/users' >> $CONF_FILE
echo '$loglevel 4' >> $CONF_FILE

echo '/etc/local/lib/' > $TORQ_CONF_FILE

# Using a security flaw here w e will need to change this

echo "#!/bin/bash" >> /tmp/setup_nodes.sh
echo "hostname torque-node\$(ip a s eth0|grep inet|head -n1|cut -d' ' -f6|cut -d/ -f1|tr . -)" >> /tmp/setup_nodes.sh
echo "echo 127.0.0.1 torque-node\$(ip a s eth0|grep inet|head -n1|cut -d' ' -f6|cut -d/ -f1|tr . -) >> /etc/hosts" >> /tmp/setup_nodes.sh
echo "chown root:root $TORQ_CONF_FILE" >> /tmp/setup_nodes.sh
echo "mv $TORQ_CONF_FILE /etc/ld.so.conf.d/torque.conf" >> /tmp/setup_nodes.sh
echo 'ldconfig' >> /tmp/setup_nodes.sh
echo '/glusterfs/users/torque_nodes/setup_scripts/torque-package-mom-linux-x86_64.sh --install' >> /tmp/setup_nodes.sh
echo '/glusterfs/users/torque_nodes/setup_scripts/torque-package-clients-linux-x86_64.sh --install' >> /tmp/setup_nodes.sh
echo "chown root:root $CONF_FILE" >> /tmp/setup_nodes.sh
echo "mv $CONF_FILE /var/spool/torque/mom_priv/config" >> /tmp/setup_nodes.sh
echo 'killall -9 pbs_mom' >> /tmp/setup_nodes.sh
echo 'ldconfig' >> /tmp/setup_nodes.sh
echo 'pbs_mom' >> /tmp/setup_nodes.sh

chmod +x /tmp/setup_nodes.sh

sudo /tmp/setup_nodes.sh
