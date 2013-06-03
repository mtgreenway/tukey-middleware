import base64
import datetime
import gnupg
import httplib
import json
import os
import random
import requests
import sys

from ConfigParser import ConfigParser
from logging_settings import get_logger
from psycopg2 import IntegrityError
from subprocess import Popen, PIPE

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

#logging settings 
logger = get_logger()

class connect_error():
    ''' little stub so we can polymorph on the error '''
    def __init__(self):
        self.status_code = 500

def get_instances(project_id, auth_token):
    ''' query the api for instances '''

    host = '%s:%s' % (local_settings.API_HOST, local_settings.NOVA_PROXY_PORT)

    url = "http://%s/v2/%s/servers/detail" % (host, project_id)

    headers = {
        "X-Auth-Project-Id": project_id,
        "X-Auth-Token": auth_token
    }

    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError:
        return connect_error()

    return response


def get_instance_name(project_id, auth_token, cloud, instance_id, instances):
    ''' Find this instance's name '''
    for instance in instances["servers"]:
        if instance["id"] == instance_id and instance["cloud_id"] == cloud:
            return instance["name"]


def node_delete_request(project_id, auth_token, node_id):
    ''' delete the node '''

    host = '%s:%s' % (local_settings.API_HOST, local_settings.NOVA_PROXY_PORT)

    headers = {
        'Host': host,
        'Accept': 'application/json',
        'User-Agent': 'python-novaclient',
        'Content-Type': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
        'X-Auth-Project-Id': project_id,
        'X-Auth-Token': auth_token
    }

    url = 'http://%s/v1.1/%s/servers/%s' % (host, project_id, node_id)

    try: 
        response = requests.delete(url, headers=headers)
    except requests.exceptions.ConnectionError:
        return connect_error()

    logger.debug("tried to terminate instance %s", node_id)
    logger.debug(response)

    return response
   

def node_launch_request(project_id, auth_token, node_object):
    ''' Do the node launching stuff.
    TODO: factor out the proxy style so that auth_multiple keys and this can
    both share it.  '''

    host = '%s:%s' % (local_settings.API_HOST, local_settings.NOVA_PROXY_PORT)

    headers = {
        'Host': host,
        'Accept': 'application/json',
        'User-Agent': 'python-novaclient',
        'Content-Type': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
        'X-Auth-Project-Id': project_id,
        'X-Auth-Token': auth_token
    }

    url = 'http://%s/v1.1/%s/servers' % (host, project_id)

    json_string = json.dumps(node_object)

    headers['Content-Length'] = str(len(json_string))

    try: 
        response = requests.post(url, headers=headers, data=json_string)
    except requests.exceptions.ConnectionError:
        return connect_error()

    return response


def flavor_request(project_id, auth_token, flavor):
    ''' Get details about this flavor '''

    host = '%s:%s' % (local_settings.API_HOST, local_settings.NOVA_PROXY_PORT)

    headers = {
        'Host': host,
        'Accept': 'application/json',
        'User-Agent': 'python-novaclient',
        'Content-Type': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
        'X-Auth-Project-Id': project_id,
        'X-Auth-Token': auth_token
    }

    url = 'http://%s/v2/%s/flavors/%s' % (host, project_id, flavor)

    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError:
        return connect_error()

    return response


def get_cores(project_id, auth_token, flavor):
    ''' Get the number of cores this flavor has '''
 
    response = flavor_request(project_id, auth_token, flavor)
    if response.status_code == 200:
        flavor_details = json.loads(response.text)
        return flavor_details["flavor"]["vcpus"]


def get_user_data(file_name, format_dict):
    ''' Read file in same dir and format with the dict then b64 encode'''
    script_file = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
        file_name))
    script = script_file.read() 
    script_file.close()
    script = script % format_dict
    return base64.b64encode(script)


def launch_instances(project_id, auth_token, cloud, image, flavor, number,
    cluster_id, username):
    ''' Launch a tiny headnode and number compute nodes with flavor and image
    '''
    
    cores = get_cores(project_id, auth_token, flavor)

    head_node_user_data = get_user_data("torque_server.py",
        {"username": username, "cluster_id": cluster_id, "nodes": number,
            "host": local_settings.clouds[cloud]["nova_host"], 
            "port": local_settings.clouds[cloud]["nova_port"],
            "auth_token": auth_token, "tenant_id": project_id,
            "cores": cores})

    head_node = {
        "server":  {
            "name": "%s-torque-headnode-%s" % (cloud, cluster_id),
            "flavorRef": 1,
            "imageRef": local_settings.clouds[cloud]["torque_image"],
            "max_count": 1,
            "min_count": 1,
            "user_data": head_node_user_data,
            "security_groups": [{"name": "default"}]
        }
    }

    response = node_launch_request(project_id, auth_token, head_node) 
    if response.status_code != 200:
       return response.status_code

    head_node_response = json.loads(response.text)
    node_ids = [head_node_response["server"]["id"]]

    compute_node_user_data = get_user_data("torque-node.sh", 
        {"username": username, "cluster_id": cluster_id})

    #for i in range(int(number)):

    compute_node = {
        "server":  {
            "name": "%s-torque-node-%s" % (cloud, cluster_id),
            "flavorRef": flavor,
            "imageRef": image,
            "max_count": number,
            "min_count": number,
            "user_data": compute_node_user_data,
            "security_groups": [{"name": "default"}]
        }
    }

    response = node_launch_request(project_id, auth_token, compute_node)

    if response.status_code != 200:
        logger.debug(response.status_code)
        logger.debug(response.text)
        logger.debug("Couldn't launch instances")
        logger.debug("going to kill and nova dont care")
        # terminate all the previously launched instances
        for node_id in node_ids:
            node_delete_request(project_id, auth_token, node_id)
        return response.status_code

    node_response = json.loads(response.text)
    node_ids.append([node_response["server"]["id"]])
        
    return 200 


def launch_cluster(project_id, auth_token, cloud, username, image, flavor,
    number):
    ''' Main cluster launch method.  Launches the instances needed for the 
    cluster then dispatches the request to the cluster service running on 
    the cloud headnode where it can run the specialized boot up services.
    TODO: There might actually be no reason to have a centralized cluster 
    service we can use -f to tell the each node in the cluster exactly what
    it needs to do. '''

    rand_base = "0000000%s" % random.randrange(sys.maxint)
    date = datetime.datetime.now()
    # underscore is not allowed in a hostname
    cluster_id = "%s-%s" % (rand_base[-8:], date.strftime("%m-%d-%y"))

    status = launch_instances(project_id, auth_token, cloud, image, flavor,
        number, cluster_id, username)

    logger.debug(status)

    if status != 200:
        return '{"message": "Not all nodes could be created.", "code": 409}'
 
    return json.dumps({"servers": [ {"id": ""} for i in range(int(number)) ] })


def delete_cluster(project_id, auth_token, cloud, username, instance_id):
    ''' Find the name of the instance then all instances with that same name
     and the headnode and delete all of those instances. '''
     
    real_id = instance_id[len("cluster" + cloud) + 1:]

    instances = json.loads(get_instances(project_id, auth_token).text)
    name = get_instance_name(project_id, auth_token, cloud, real_id, instances)
    torque_id = "-".join(name.split("-")[2:])

    error = False

    for instance in instances["servers"]:
        base = "-".join(instance["name"].split("-")[:2])
        name_id = "-".join(instance["name"].split("-")[2:])
        if (base == "torque-node" or base == "torque-headnode") and \
            name_id == torque_id:
            logger.debug("deleting %s %s", instance["id"], instance["name"])
            response = node_delete_request(project_id, auth_token, instance["id"])
            if response.status_code != 200:
                error = True 
            logger.debug(response.text)
    if error:
        return '{"message": "Not all nodes could be deleted.", "code": 409}'
    return '{"server": []}'
         

def main():
    logger.debug("in main")
    if len(sys.argv) == 8:
        print launch_cluster(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
            sys.argv[5], sys.argv[6], sys.argv[7])
    elif len(sys.argv) == 6:
        print delete_cluster(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
            sys.argv[5])


if __name__ == "__main__":
    main()
