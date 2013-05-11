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


def launch_instances(project_id, auth_token, cloud, image, flavor, number,
    cluster_id):
    ''' Launch a tiny headnode and number compute nodes with flavor and image
    '''

    head_node = {
        "server":  {
            "name": "%s-torque-headnode-%s" % (cloud, cluster_id),
            "flavorRef": 1,
            "imageRef": image,
            "max_count": 1,
            "min_count": 1,
            "security_groups": [{"name": "default"}]
        }
    }

    response = node_launch_request(project_id, auth_token, head_node) 
    if response.status_code != 200:
       return response.status_code

    head_node_response = json.loads(response.text)
    node_ids = [head_node_response["server"]["id"]]

    for i in range(int(number)):

        compute_node = {
            "server":  {
                "name": "%s-torque-node%s-%s" % (cloud, i + 1, cluster_id),
                "flavorRef": flavor,
                "imageRef": image,
                "max_count": 1,
                "min_count": 1,
                "security_groups": [{"name": "default"}]
            }
        }

        response = node_launch_request(project_id, auth_token, compute_node)

        if response.status_code != 200:
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
    cluster_id = "%s_%s" % (rand_base[-8:], date.strftime("%m-%d-%y"))

    status = launch_instances(project_id, auth_token, cloud, image, flavor,
        number, cluster_id)

    logger.debug(status)

    if status != 200:
        print '{"message": "Not all nodes could be created.", "code": 409}'
        sys.exit(1)
 
    host = local_settings.clouds[cloud]["login_node"]["host"]
    port = local_settings.clouds[cloud]["login_node"]["cluster_port"]
    keyfile_name = local_settings.KEY_DIR + local_settings.clouds[cloud][
        "login_node"]["gpg_pubkey"]
    password_to_send = local_settings.clouds[cloud]["login_node"]["passphrase"]

    logger.debug(keyfile_name)
    
    keyfile = open(keyfile_name)
    host_key = keyfile.read()
    keyfile.close()
    logger.debug("hey")

    logger.debug(host_key)

    gpg = gnupg.GPG(gnupghome=local_settings.GPG_HOME)

    import_result = gpg.import_keys(host_key)

    recipient = import_result.fingerprints[0]

    raw_message = json.dumps(
    {
        "passphrase": password_to_send,
        "username": username, 
        "cluster_id": cluster_id,
        #"image": image,
        #"flavor": flavor,
        "number": number
    })

    message = gpg.encrypt(raw_message, recipient, always_trust=True,
        sign=local_settings.GPG_FINGERPRINT,
        passphrase=local_settings.GPG_PASSPHRASE)

    logger.debug("host: %s", host)
    logger.debug("port: %s", port)
    try:
        conn = httplib.HTTPConnection("%s:%s" % (host, port))
        conn.request("POST", '/', str(message))
        resp = conn.getresponse()
        conn.close()
    except:
        return '{"message": "Cluster launch failed.", "code": 409}'

    if resp.status != 200:
        return '{"message": "Cluster launch failed.", "code": %s}' % resp.status
    content = resp.read()

    logger.debug("content %s", content)

    return json.dumps({"servers": [ {"id": ""} for i in range(int(number)) ] })

    #return content


def main():
    logger.debug("in main")
    print launch_cluster(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
        sys.argv[5], sys.argv[6], sys.argv[7])


if __name__ == "__main__":
    main()
