import gnupg
import httplib
import json
import os
import sys
import tempfile

from ConfigParser import ConfigParser
from M2Crypto import DSA, BIO
from auth_db import insert_sshkey, delete_sshkey, get_keypairs, get_keypair
from logging_settings import get_logger
from psycopg2 import IntegrityError
from subprocess import Popen, PIPE

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

#logging settings 
logger = get_logger()

SSH_KEYGEN = local_settings.SSH_KEYGEN_COMMAND


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
    
    public_key = run_ssh_on_string(SSH_KEYGEN + " -f %s -i -m PKCS8",
        mem_pub.getvalue())[:-1]
    return public_key, private_key


def send_to_host(username, public_key, method='PUT'):
 
    fingerprint = sys.argv[1]
    gpg_home = sys.argv[2]
    passphrase = sys.argv[3]
    host = sys.argv[4]
    keyfile_name = sys.argv[5]

    logger.debug(keyfile_name)
    
    keyfile = open(keyfile_name)
    host_key = keyfile.read()
    keyfile.close()

    logger.debug(host_key)

    gpg = gnupg.GPG(gnupghome=gpg_home)

    import_result = gpg.import_keys(host_key)

    recipient = import_result.fingerprints[0]

    raw_message = json.dumps(
    {
        "username": username, 
        "public_key": public_key
    })

    message = gpg.encrypt(raw_message, recipient, always_trust=True,
        sign=fingerprint, passphrase=passphrase)

    logger.debug("host: %s", host)
    conn = httplib.HTTPConnection(host)
    conn.request(method, '/', str(message))
    resp = conn.getresponse()

    if resp.status != 200:
        raise
    content = resp.read()

    logger.debug("content %s", content)

    return content


def populate_key(cloud, username, keyname, public_key, private_key=''):

    fingerprint = run_ssh_on_string(SSH_KEYGEN + " -lf %s", public_key).split(
        ' ')[1]

    logger.debug(fingerprint)
    
    try:
        insert_sshkey(cloud, username, public_key, fingerprint, keyname)

        try:
            send_to_host(username, public_key)

    
            print json.dumps([{
                "keypair": {
                    "public_key": public_key,
                    "private_key": private_key,
                    "user_id": "",
                    "name": keyname,
                    "fingerprint": fingerprint
                }
            }])

        except:
            delete_sshkey(cloud, username, keyname)
            print '{"message": "Key pair \'%s\' could not be created.", "code": 409}' % keyname
        
    except IntegrityError:
        print '{"message": "Key pair \'%s\' already exists.", "code": 409}' % keyname
    

def main():
    # args 1,2,3,4,5 are all used for gpg 
        
    option = sys.argv[6]
    username = sys.argv[7]
    cloud = sys.argv[8]

    logger.debug(username)
    logger.debug(option)
    
    if option == 'create':
	logger.debug("there is no keyname")
        keyname = sys.argv[9]
	logger.debug("keyname %s", keyname)
        if len(sys.argv) > 10:
            password = sys.argv[10]
            public_key, private_key = generate_keypair(password=password)
        else:
            public_key, private_key = generate_keypair()
        populate_key(cloud, username, keyname, public_key, private_key)
    
    elif option == 'import':
        keyname = sys.argv[9]
        public_key = ' '.join(sys.argv[10:])

        logger.debug(public_key)
        
        populate_key(cloud, username, keyname, public_key)

    elif option == 'delete':
        logger.debug("going to delete")
        keyname = sys.argv[9]
        logger.debug("cloud: %s, username: %s, keyname: %s", cloud, username, keyname)
	public_key = get_keypair(cloud, username, keyname)[0]
	logger.debug(public_key)
        try:
            send_to_host(username, public_key, method='DELETE')
            if not delete_sshkey(cloud, username, keyname):
                send_to_host(username, public_key)
                print '{"message": "Key pair \'%s\' could not be deleted.", "code": 409}' % keyname
        except:
            print '{"message": "Key pair \'%s\' could not be deleted.", "code": 409}' % keyname

    elif option == 'list':
        print json.dumps(get_keypairs(cloud, username))


if __name__ == "__main__":
    main()
