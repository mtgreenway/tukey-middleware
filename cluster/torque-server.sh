#!/bin/bash
CLUSTER_ID=%(cluster_id)s
NODES=%(nodes)s

if [ `whoami` != "%(username)s" ]
then
  exit 1
fi

# wait for gluster to come up
while ! ls /glusterfs/users/torque_nodes/setup_scripts/
do
    sleep 1
done

echo 'echo /etc/local/lib/ > /etc/ld.so.conf.d/torque.conf' >> /tmp/setup_nodes.sh
echo 'ldconfig' >> /tmp/setup_nodes.sh
echo "echo torque-headnode-$CLUSTER_ID > /var/spool/torque/server_name" >> /tmp/setup_nodes.sh
echo 'qterm' >> /tmp/setup_nodes.sh
echo 'echo y|/glusterfs/users/torque_nodes/setup_scripts/torque.setup root' >> /tmp/setup_nodes.sh
echo 'qterm' >> /tmp/setup_nodes.sh
echo 'killall pbs_server' >> /tmp/setup_nodes.sh
echo 'killall trqauthd' >> /tmp/setup_nodes.sh
echo 'killall pbs_sched' >> /tmp/setup_nodes.sh
echo 'pbs_server' >> /tmp/setup_nodes.sh
echo 'trqauthd' >> /tmp/setup_nodes.sh
echo 'pbs_sched' >> /tmp/setup_nodes.sh
echo "for i in \$(seq $NODES)" >> /tmp/setup_nodes.sh
echo 'do' >> /tmp/setup_nodes.sh
echo "    p=torque-node\$i-$CLUSTER_ID" >> /tmp/setup_nodes.sh
echo '    while ! nc -z $p 15002' >> /tmp/setup_nodes.sh
echo '    do' >> /tmp/setup_nodes.sh
echo '        sleep 1' >> /tmp/setup_nodes.sh
echo '    done' >> /tmp/setup_nodes.sh

echo '    qmgr -c "create node $p"' >> /tmp/setup_nodes.sh
echo '    qmgr -c "set node $p state = free"' >> /tmp/setup_nodes.sh
echo 'done' >> /tmp/setup_nodes.sh

chmod +x /tmp/setup_nodes.sh

sudo /tmp/setup_nodes.sh
