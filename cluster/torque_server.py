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

if getpass.getuser() != project_name:
    sys.exit(1)

while not os.path.exists("/glusterfs/users/torque_nodes/setup_scripts/"):
    time.wait(1) 

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

os.system(" ".join(["sudo",
    "/glusterfs/users/torque_nodes/headnode/tukey_headnode.sh", cluster_id,
    ips, "%(cores)s"]))

