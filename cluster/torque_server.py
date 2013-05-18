#!/usr/bin/python

import getpass
import json
import os
import httplib
import stat
import sys
import time

project_name = "%(username)s"
auth_token = "%(auth_token)s"
host = "%(host)s"
port = %(port)s
tenant_id = "%(tenant_id)s"
cluster_id = "%(cluster_id)s"

if getpass.getuser() != project_name:
    sys.exit(1)

while not os.path.exists("/glusterfs/users/torque_nodes/setup_scripts/"):
    time.wait(1) 

headers = {"x-auth-project-id": project_name, "x-auth-token": auth_token}
conn = httplib.HTTPConnection(host, port)
conn.request("GET", "/".join(["/v2", tenant_id, "servers/detail"]), None, headers)
response = conn.getresponse()

node = 0
setup_nodes = "#!/bin/bash"

for i in json.loads(response.read())["servers"]:
    if i["name"] == "torque-node-" + cluster_id:
        node = node + 1
        host_name = "torque-node" + i["addresses"]["private"][0]["addr"]
        hostnames = " ".join([hostnames, host_name])
        line = " ".join(["echo", i["addresses"]["private"][0]["addr"], 
            host_name, ">> /etc/hosts"])
    	setup_nodes = "\n".join([setup_nodes, line])

setup_nodes = "\n".join([setup_nodes, '''
echo /etc/local/lib/ > /etc/ld.so.conf.d/torque.conf
ldconfig
echo torque-headnode-%(cluster_id)s > /var/spool/torque/server_name
qterm
echo y|/glusterfs/users/torque_nodes/setup_scripts/torque.setup root
qterm
killall pbs_server
killall trqauthd
killall pbs_sched
pbs_server
trqauthd
pbs_sched''',
"for p in " + hostnames, 
'''do
    while ! nc -z $p 15002
    do
        sleep 1
    done

    qmgr -c "create node $p"
    qmgr -c "set node $p state = free"
done '''])

f = open('/tmp/setup_nodes.sh', 'w+')
f.write(setup_nodes)
f.close()
st = os.stat('/tmp/setup_nodes.sh')
os.chmod('/tmp/setup_nodes.sh', st.st_mode | stat.S_IEXEC)

os.system('sudo /tmp/setup_nodes.sh')

