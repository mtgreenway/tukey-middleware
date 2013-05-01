# mgreenway 2012
# Apache 2 ????

from flask import Flask, request, abort
from logging_settings import get_logger
from logging_settings import get_logger

import gnupg
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

app = Flask(__name__)

#logging settings 
logger = get_logger()

def append_key(key_file_name, key_text):
    ''' Appends key key_text to authorized_keys file key_file_name.
    If key_text ends with a newline it is appended to the file that's
    name is specified by the string key_file_name otherwise a newline
    is concatenated to the end of key_text and then appended.'''

    logger.debug("going to open %s" % key_file_name)

    key_file = open(key_file_name, 'a')

    if key_text[-1] == '\n':
        key_file.write(key_text)
    else:
        key_file.write(key_text + '\n')

    key_file.close()


def delete_key(key_file_name, key_text):
    ''' Deletes any line matching the the string key_text from 
    file key_file_name.
    Reads in all lines of the
    '''

    if key_text[-1] != '\n':
        key_text = key_text + '\n'

    key_file = open(key_file_name)
    
    keys = key_file.readlines()
    
    key_file.close()
    
    key_file = open(key_file_name, 'w')

    logger.debug(key_text)

    logger.debug([key for key in keys if key != key_text])
    
    key_file.writelines([key for key in keys if key != key_text])
 
    key_file.close()


@app.route("/", methods=['PUT'])
def put():

    message = gpg.decrypt(request.data, passphrase=PASSPHRASE)

    logger.debug("the message is %s", message)

    key_info = json.loads(str(message))

    logger.debug(key_info['username'])

    key_file =  HOME_DIR + '/' + key_info['username'] + '/' + KEY_FILE

    logger.debug(key_file)

    append_key(key_file, key_info['public_key'])

    return "called"


@app.route("/", methods=['DELETE'])
def delete():

    message = gpg.decrypt(request.data, passphrase=PASSPHRASE)
 
    key_info = json.loads(str(message))
 
    logger.debug(message)
 
    key_file_name = "%s/%s/%s" % (HOME_DIR, key_info['username'], KEY_FILE)
 
    logger.debug(key_file_name)
 
    delete_key(key_file_name, key_info['public_key'])
 
    return "called"


HOME_DIR = local_settings.KEY_SERVER_HOME_DIR
GPG_HOME = local_settings.SERVER_GPG_HOME
PASSPHRASE = local_settings.SERVER_GPG_PASSPHRASE
KEY_FILE = local_settings.KEY_SERVER_KEY_FILE


if __name__ == "__main__":
    HOST = sys.argv[1] 
    PORT = int(sys.argv[2])

    if len(sys.argv) > 3:
        HOME_DIR = sys.argv[3]

    if len(sys.argv) > 4:
        GPG_HOME = sys.argv[4]

    if len(sys.argv) > 5:
        PASSPHRASE = sys.argv[5]

    if len(sys.argv) > 6:
        KEY_FILE = sys.argv[6]

    gpg = gnupg.GPG(gnupghome=GPG_HOME)
        
    app.run(host=HOST, port=PORT)

