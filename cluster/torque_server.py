#!/usr/bin/python

import getpass
import json
import os
import httplib
import sys
import time

project_name = "%(username)s"
auth_token = "%(auth_token)s"
host = "%(host)s"
port = %(port)s
tenant_id = "%(tenant_id)s"
cluster_id = "%(cluster_id)s"

if %(pdc)s and getpass.getuser() != project_name:
    sys.exit(1)

while not os.path.exists("%(setup_dir)s"):
    time.sleep(1) 

headers = {"x-auth-project-id": project_name, "x-auth-token": auth_token}
conn = httplib.HTTPConnection(host, port)
conn.request("GET", "/".join(["/v2", tenant_id, "servers/detail"]), None, headers)
response = conn.getresponse()

ips = ""

servers = [i for i in json.loads(response.read())["servers"]
    if i["name"] == "torque-node-" + cluster_id]

for i in servers:
    try:
        ips = " ".join([ips, i["addresses"]["private"][0]["addr"]])
    except KeyError:
        pass

ips = '"' + ips + '"'

if not %(pdc)s:
    os.system("echo %(public_key)s >> /home/ubuntu/.ssh/authorized_keys")
    os.system("""echo "%(private_key)s" >> /home/ubuntu/.ssh/id_dsa""")
    os.system("chown ubuntu:ubuntu /home/ubuntu/.ssh/id_dsa")
    os.system("chmod 600 /home/ubuntu/.ssh/id_dsa")

os.system(" ".join(["sudo", "%(headnode_script)s", cluster_id, ips, "%(cores)s"]))
#os.system("echo ran > /tmp/worked")
