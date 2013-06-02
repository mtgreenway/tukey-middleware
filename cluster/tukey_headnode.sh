#!/bin/bash
cluster_id=$1
ips=$2
cores=$3

echo /etc/local/lib/ > /etc/ld.so.conf.d/torque.conf
ldconfig
echo torque-headnode-$cluster_id > /var/spool/torque/server_name
qterm
echo y|/glusterfs/users/torque_nodes/setup_scripts/torque.setup root
qterm
killall pbs_server
killall trqauthd
killall pbs_sched
pbs_server
trqauthd
pbs_sched

for addr in $ips
do
    p="torque-node$(echo $addr|tr . -)"
    echo $addr $p >> /etc/hosts
    while ! nc -z $p 15002
    do
        sleep 1
    done

    qmgr -c "create node $p"
    qmgr -c "set node $p state = free"
    qmgr -c "set node $p np=$cores"
done

