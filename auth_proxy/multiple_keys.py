#!/usr/bin/python
# we want to wrap a call to creating a keypair for the login node and
# then call keypair create for OpenStack API.
# we could actually use this to Import as many keypairs as we want
# using our own nova proxy and conventions:
# call this service with cloudname that is the correct way.

#arguments to this should be

#${sullivan/access/token/id}

#${sullivan/access/user/id}
import json 
import logging
import logging.handlers
import os
import requests
import sys

from logging_settings import get_logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

#logging settings 
logger = get_logger()

headers = {
    'Host': '127.0.0.1:8774',
    'Accept': 'application/json',
    'User-Agent': 'python-novaclient',
    'Content-Type': 'application/json',
    'Accept-Encoding': 'gzip, deflate'
}


def delete_keypair(project_id, auth_token, name, cloud):
    
    headers['X-Auth-Project-Id'] = project_id
    headers['X-Auth-Token']  = auth_token

    url = 'http://127.0.0.1:8774/v1.1/%s/os-keypairs/%s-%s' % (project_id,
         cloud, name)

    return requests.request('DELETE', url, headers=headers, data=keypair)


def create_keypair(project_id, auth_token, name, cloud, public_key=None):

    headers['X-Auth-Project-Id'] = project_id
    headers['X-Auth-Token'] = auth_token

    url = 'http://127.0.0.1:8774/v1.1/%s/os-keypairs' % project_id
    
    keypair = {
        "keypair":  {
            "name": cloud + '-' + name
        }
    }
    
    if public_key is not None:
        keypair["keypair"]["public_key"] = public_key

    logger.debug(public_key)
    
    keypair_string = json.dumps(keypair)

    headers['Content-Length'] = str(len(keypair_string))
    # may need to be jsonised 
    logger.debug("about to dispatch")

    response = requests.post(url, headers=headers, data=keypair_string)

    if response.status_code != 200:
        print '{"message": "Not all keypairs could be created.", "code": 409}'
        sys.exit(1)

    logger.debug(dir(response))

    logger.debug(response.text)

    return response.text


def main():
    project_id = sys.argv[1]
    auth_token = sys.argv[2]
    name = sys.argv[3]
    logger.debug(sys.argv[4])
    clouds = json.loads(sys.argv[4])
    method = sys.argv[5]

    public_key = None

    keypair_string = None

    if len(sys.argv) > 6:
        #if importing
        public_key = ' '.join(sys.argv[6:])
        logger.debug("PUB KEY %s", public_key)
    else:
        cloud = clouds[0]
        clouds.remove(cloud)
        keypair_string = create_keypair(project_id, auth_token, name,
            cloud)

        logger.debug(keypair_string)
        created_keypair = json.loads(keypair_string)
        if 'keypair' in created_keypair['keypair']:
            created_keypair = created_keypair['keypair']
        public_key = created_keypair['keypair']['public_key']

    result = None

    for cloud in clouds:
        result = create_keypair(project_id, auth_token, name, cloud,
            public_key=public_key)

    if keypair_string is None:
        keypair_string = result

    keypair = json.loads(keypair_string)
    if 'keypair' in keypair['keypair']:
        keypair = keypair['keypair']
    keypair_string = json.dumps(keypair)

    logger.debug("the keypair string is : %s", keypair_string)

    print keypair_string

if __name__ == "__main__":
    main()

