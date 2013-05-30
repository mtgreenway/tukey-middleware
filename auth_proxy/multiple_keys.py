#!/usr/bin/python
# we want to wrap a call to creating a keypair for the login node and
# then call keypair create for OpenStack API.
# we could actually use this to Import as many keypairs as we want
# using our own nova proxy and conventions:
# call this service with cloudname that is the correct way.

#arguments to this should be ${sullivan/access/token/id} ${sullivan/access/user/id}
''' Performs a recursive http request to create keys on every cloud '''

import json
import os
import requests
import sys

from logging_settings import get_logger
from subprocess import Popen, PIPE

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

#logging settings
LOGGER = get_logger()

HOST = '%s:%s' % (local_settings.API_HOST, local_settings.NOVA_PROXY_PORT)

HEADERS = {
    'Host': HOST,
    'Accept': 'application/json',
    'User-Agent': 'python-novaclient',
    'Content-Type': 'application/json',
    'Accept-Encoding': 'gzip, deflate'
}


def create_keypair(project_id, auth_token, name, cloud, public_key=None):
    ''' Recursively call the nova proxy with a os-keypairs create key request
    '''

    HEADERS['X-Auth-Project-Id'] = project_id
    HEADERS['X-Auth-Token'] = auth_token

    url = 'http://%s/v1.1/%s/os-keypairs' % (HOST, project_id)

    keypair = {
        "keypair":  {
            "name": cloud + '-' + name
        }
    }

    if public_key is not None:
        keypair["keypair"]["public_key"] = public_key

    LOGGER.debug(public_key)

    keypair_string = json.dumps(keypair)

    HEADERS['Content-Length'] = str(len(keypair_string))
    # may need to be jsonised
    LOGGER.debug("about to dispatch")

    response = requests.post(url, headers=HEADERS, data=keypair_string)

    if response.status_code != 200:
        print '{"message": "Not all keypairs could be created.", "code": 409}'
        sys.exit(1)

    LOGGER.debug(response.text)

    return response.text


def main():
    project_id = sys.argv[1]
    auth_token = sys.argv[2]
    name = sys.argv[3]
    LOGGER.debug(sys.argv[4])
    clouds = json.loads(sys.argv[4])

    public_key = None

    keypair_string = None

    if len(sys.argv) > 6:
        #if importing
        public_key = ' '.join(sys.argv[6:])
        LOGGER.debug("PUB KEY %s", public_key)
    else:
        cloud = clouds[0]
        clouds.remove(cloud)
        keypair_string = create_keypair(project_id, auth_token, name,
            cloud)

        LOGGER.debug(keypair_string)
        created_keypair = json.loads(keypair_string)
        if 'keypair' in created_keypair['keypair']:
            created_keypair = created_keypair['keypair']
        public_key = created_keypair['keypair']['public_key']

        # Eucalyptus will not give us a pubkey
        if public_key == "":
            private_key = created_keypair['keypair']['private_key'].replace(
                '\n', '\\\\n')
            command = "/bin/echo -e %s |" + local_settings.SSH_KEYGEN_COMMAND \
                + " -y -f /dev/stdin"
            LOGGER.debug(command % private_key)
            process = Popen(command % private_key, stdout=PIPE, shell=True)
            output = process.communicate()[0]
            LOGGER.debug(output)
            public_key = output

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

    LOGGER.debug("the keypair string is : %s", keypair_string)

    print keypair_string

if __name__ == "__main__":
    main()
