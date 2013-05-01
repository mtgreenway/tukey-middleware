import gnupg
import httplib
import json
import os
import sys

from ConfigParser import ConfigParser
from logging_settings import get_logger
from psycopg2 import IntegrityError
from subprocess import Popen, PIPE

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

#logging settings 
logger = get_logger()


def send_to_host(cloud, username, image, flavor, number):
 
    host = local_settings.clouds[cloud]["login_node"]["host"]
    port = local_settings.clouds[cloud]["login_node"]["cluster_port"]
    keyfile_name = local_settings.KEY_DIR + local_settings.clouds[cloud]["login_node"]["gpg_pubkey"]
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
        "image": image,
        "flavor": flavor,
        "number": number
    })

    message = gpg.encrypt(raw_message, recipient, always_trust=True,
        sign=local_settings.GPG_FINGERPRINT,
        passphrase=local_settings.GPG_PASSPHRASE)

    logger.debug("host: %s", host)
    logger.debug("port: %s", port)
    conn = httplib.HTTPConnection("%s:%s" % (host, port))
    conn.request("POST", '/', str(message))
    resp = conn.getresponse()

    if resp.status != 200:
        raise
    content = resp.read()

    logger.debug("content %s", content)

    print '{"servers": [{"id": "fake", "links": [] }] }'

    return content


def main():
    send_to_host(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
        sys.argv[5])


if __name__ == "__main__":
    main()
