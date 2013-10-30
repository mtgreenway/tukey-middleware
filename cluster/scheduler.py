import base64
import datetime
import gnupg
import httplib
import json
import os
import random
import requests
import sys
import tempfile

from ConfigParser import ConfigParser
from logging_settings import get_logger
from psycopg2 import IntegrityError
from subprocess import Popen, PIPE
from M2Crypto import DSA, BIO

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

#logging settings 
logger = get_logger()

class connect_error():
    ''' little stub so we can polymorph on the error '''
    def __init__(self):
        self.status_code = 500

def get_host(cloud):
    return local_settings.API_HOST

def get_port(cloud):
    return local_settings.NOVA_PROXY_PORT

def host_and_headers(cloud, project_id, auth_token):
    host = '%s:%s' % (get_host(cloud), get_port(cloud))

    headers = {
        'Host': host,
        'Accept': 'application/json',
        'User-Agent': 'python-novaclient',
        'Content-Type': 'application/json',
        'Accept-Encoding': 'gzip, deflate',
        'X-Auth-Project-Id': project_id,
        'X-Auth-Token': auth_token
    }
    return host, headers


def get_instances(cloud, project_id, auth_token):
    ''' query the api for instances '''

    host, headers = host_and_headers(cloud, project_id, auth_token)
    logger.info("%s", host)

    url = "http://%s/v2/%s/servers/detail" % (host, project_id)
    logger.info(url)

    try:
        response = requests.get(url, headers=headers)
        logger.info(response.text)
    except requests.exceptions.ConnectionError:
        logger.info("connection failed")
        return connect_error()

    return response


def get_instance_name(project_id, auth_token, cloud, instance_id, instances):
    ''' Find this instance's name '''
    for instance in instances["servers"]:
        if "id" in instance and instance["id"] == instance_id \
                and instance["cloud_id"] == cloud:
            return instance["name"]


def node_delete_request(cloud, project_id, auth_token, node_id):
    ''' delete the node '''
    
    host, headers = host_and_headers(cloud, project_id, auth_token)
    logger.info("%s", host)

    url = 'http://%s/v1.1/%s/servers/%s' % (host, project_id, node_id)

    try: 
        response = requests.delete(url, headers=headers)
    except requests.exceptions.ConnectionError:
        return connect_error()

    logger.debug("tried to terminate instance %s", node_id)
    logger.debug(response)

    return response
   

def node_launch_request(cloud, project_id, auth_token, node_object):
    ''' Do the node launching stuff.
    TODO: factor out the proxy style so that auth_multiple keys and this can
    both share it.  '''

    host, headers = host_and_headers(cloud, project_id, auth_token)
    logger.info("%s", host)


    url = 'http://%s/v1.1/%s/servers' % (host, project_id)

    json_string = json.dumps(node_object)

    headers['Content-Length'] = str(len(json_string))

    try: 
        response = requests.post(url, headers=headers, data=json_string)
    except requests.exceptions.ConnectionError:
        logger.info("we had a probvlem")
        return connect_error()

    return response


def flavor_request(cloud, project_id, auth_token, flavor):
    ''' Get details about this flavor '''

    host, headers = host_and_headers(cloud, project_id, auth_token)
    logger.info("%s", host)


    url = 'http://%s/v2/%s/flavors/%s' % (host, project_id, flavor)

    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError:
        return connect_error()

    return response


def get_cores(cloud, project_id, auth_token, flavor):
    ''' Get the number of cores this flavor has '''
 
    #TODO: need to get all flavors and look through them for reliable ...
    response = flavor_request(cloud, project_id, auth_token, flavor)
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
    logger.debug(script)
    return base64.b64encode(script)


def run_ssh_on_string(command, string):
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(string)
    temp.close()

    process = Popen(command % temp.name, stdout=PIPE, shell=True)
    exit_code = os.waitpid(process.pid, 0)
    output = process.communicate()[0]

    os.unlink(temp.name)

    return output


def generate_keypair(password=None):
    dsa = DSA.gen_params(1024, os.urandom)

    mem_pub = BIO.MemoryBuffer()
    mem_private = BIO.MemoryBuffer()

    dsa.gen_key()
    if password is None:
        dsa.save_key_bio(mem_private, cipher=None)
    else:
        dsa.save_key_bio(mem_private, callback=lambda _: password)

    private_key =  mem_private.getvalue()

    dsa.save_pub_key_bio(mem_pub)

    public_key = run_ssh_on_string(local_settings.SSH_KEYGEN_COMMAND + " -f %s -i -m PKCS8",
        mem_pub.getvalue())[:-1]
    return public_key, private_key



def launch_instances(project_id, auth_token, cloud, image, flavor, number,
    cluster_id, username, cloud_auth_token, keyname):
    ''' Launch a tiny headnode and number compute nodes with flavor and image
    '''
    
    cores = get_cores(cloud, project_id, auth_token, flavor)
    public_key, private_key = generate_keypair()

    head_node_user_data = get_user_data("torque_server.py",
        {"username": username, "cluster_id": cluster_id, "nodes": number,
            "host": local_settings.clouds[cloud]["nova_host"], 
            "port": local_settings.clouds[cloud]["nova_port"],
            "auth_token": cloud_auth_token, "tenant_id": project_id,
            "pdc": "True" if local_settings.clouds[cloud]["torque"]["pdc"] else "False",
            "cores": cores,
            "setup_dir": local_settings.clouds[cloud]["torque"]["setup_dir"],
            "public_key": public_key, "private_key": private_key,
            "headnode_script": 
                local_settings.clouds[cloud]["torque"]["headnode_script"]})

    head_node = {
        "server":  {
            "name": "%s-torque-headnode-%s" % (cloud, cluster_id),
            "flavorRef": 3,
            "imageRef": local_settings.clouds[cloud]["torque"]["headnode_image"],
            "max_count": 1,
            "min_count": 1,
            "user_data": head_node_user_data,
            "security_groups": [{"name": "default"}]
        }
    }

    if keyname is not None:
        head_node["server"]["key_name"] = keyname

    response = node_launch_request(cloud, project_id, auth_token, head_node) 
    if response.status_code != 200:
       return response.status_code

    head_node_response = json.loads(response.text)
    node_ids = [head_node_response["server"]["id"]]

    compute_node_user_data = get_user_data("torque-node.sh", 
        {"username": username, "cluster_id": cluster_id,
        "pdc": "true" if local_settings.clouds[cloud]["torque"]["pdc"] else "false",
        "setup_dir": local_settings.clouds[cloud]["torque"]["setup_dir"],
        "public_key": public_key, "private_key": private_key,
        "node_script": local_settings.clouds[cloud]["torque"]["node_script"]})

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

    if keyname is not None:
        compute_node["server"]["key_name"] = keyname

    response = node_launch_request(cloud, project_id, auth_token, compute_node)

    if response.status_code != 200:
        logger.debug(response.status_code)
        logger.debug(response.text)
        logger.debug("Couldn't launch instances")
        logger.debug("going to kill and nova dont care")
        # terminate all the previously launched instances
        for node_id in node_ids:
            node_delete_request(cloud, project_id, auth_token, node_id)
        return response.status_code

    node_response = json.loads(response.text)
    node_ids.append([node_response["server"]["id"]])
        
    return 200 


def launch_cluster(project_id, auth_token, cloud, username, image, flavor,
    number, cloud_auth_token, keyname=None):
    ''' Main cluster launch method.  Launches the instances needed for the 
    cluster then dispatches the request to the cluster service running on 
    the cloud headnode where it can run the specialized boot up services.
    TODO: There might actually be no reason to have a centralized cluster 
    service we can use -f to tell the each node in the cluster exactly what
    it needs to do. '''
    logger.debug("launching cluster")
    print "keyname", keyname

    rand_base = "0000000%s" % random.randrange(sys.maxint)
    date = datetime.datetime.now()
    # underscore is not allowed in a hostname
    cluster_id = "%s-%s" % (rand_base[-8:], date.strftime("%m-%d-%y"))

    status = launch_instances(project_id, auth_token, cloud, image, flavor,
        number, cluster_id, username, cloud_auth_token, keyname)

    logger.debug(status)

    if status != 200:
        return '{"message": "Not all nodes could be created.", "code": 409}'
 
    return json.dumps({"servers": [ {"id": ""} for i in range(int(number)) ] })


def delete_cluster(project_id, auth_token, cloud, username, instance_id):
    ''' Find the name of the instance then all instances with that same name
     and the headnode and delete all of those instances. '''
    logger.debug("deleting cluster")
     
    real_id = instance_id[len("cluster" + cloud) + 1:]

    instances = json.loads(get_instances(cloud, project_id, auth_token).text)
    name = get_instance_name(project_id, auth_token, cloud, real_id, instances)
    logger.info("the name %s", name)
    torque_id = "-".join(name.split("-")[2:])

    error = False

    for instance in [i for i in instances["servers"]
             if "name" in i and "-" in i["name"]]:
        base = "-".join(instance["name"].split("-")[:2])
        name_id = "-".join(instance["name"].split("-")[2:])
        if (base == "torque-node" or base == "torque-headnode") and \
            name_id == torque_id:
            logger.debug("deleting %s %s", instance["id"], instance["name"])
            response = node_delete_request(cloud, project_id, auth_token, instance["id"])
            if response.status_code != 200:
                error = True 
            logger.debug(response.text)
    if error:
        return '{"message": "Not all nodes could be deleted.", "code": 409}'
    return '{"server": []}'
         

def main():
    logger.debug("in main")
    if len(sys.argv) == 9:
        print launch_cluster(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
            sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8])
    if len(sys.argv) == 10:
        print "key_name", sys.argv[9]
        print launch_cluster(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
            sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8], sys.argv[9])
    elif len(sys.argv) == 6:
        print delete_cluster(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
            sys.argv[5])


if __name__ == "__main__":
    main()
