# mgreenway 2012
# Apache 2 ????

from flask import Flask, request, abort
from logging_settings import get_logger
from subprocess import call

import gnupg
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

app = Flask(__name__)

#logging settings 
logger = get_logger()

def start_cluster(username, cluster_id, number):
    ''' Launch a cluster with number compute nodes from image with flavor for 
    username '''
    print locals() 
    call(["/glusterfs/users/torque_nodes/headnode/start-cluster-tukey",
        username, cluster_id, number]) 


@app.route("/", methods=['POST'])
def post():

    gpg = gnupg.GPG(gnupghome=local_settings.SERVER_GPG_HOME)

    message = gpg.decrypt(request.data,
        passphrase=local_settings.SERVER_GPG_PASSPHRASE)

    print message

    logger.debug("the message is %s", message)

    cluster_info = json.loads(str(message))

    if cluster_info["passphrase"] != local_settings.SERVER_PASSPHRASE:
        abort(401)

    logger.debug(cluster_info['username'])

    start_cluster(cluster_info["username"], cluster_info["cluster_id"],
        cluster_info["number"])

    return "done"

def main():
    app.run(host=sys.argv[1], port=int(sys.argv[2]))


if __name__ == "__main__":
    main()

