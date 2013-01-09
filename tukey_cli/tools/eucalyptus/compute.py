#!/usr/bin/python

# Grossman Computing Laboratory
# Institute for Genomics and Systems Biology
# The University of Chicago 900 E 57th St KCBD 10146, Chicago, IL 60637
# Tel: +1-773-702-9765. Fax: +1-773-834-2877
# ------------------------------------------
#
# Matthew Greenway <mgreenway@uchicago.edu>

import base64
import glob
import json
import logging
import logging.handlers
import os
import string
import sys
import time
import xmldict

from cloudTools import CloudTools
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from xml.etree.ElementTree import tostring, XML
from libcloud.common.types import InvalidCredsError

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../../../local')
import local_settings

logger = logging.getLogger('tukey-euca')
logger.setLevel(local_settings.LOG_LEVEL)

formatter = logging.Formatter(local_settings.LOG_FORMAT)

log_file_name = local_settings.LOG_DIR + 'tukey-euca.log'

logFile = logging.handlers.WatchedFileHandler(log_file_name)
logFile.setFormatter(formatter)

logger.addHandler(logFile)


def main():
    (options, args) = CloudTools.parser.parse_args()

    #eucalyptus specific, refactor
    credFile = open(options.cred, 'r')
    credentials = CloudTools.parseEucarc(credFile.read())
    credFile.close()

    credType = CloudTools.euca
    Driver = get_driver(Provider.EUCALYPTUS)

    url = CloudTools.parseHost(credentials[credType['host']])

    conn = Driver(credentials[credType['key']], secret=credentials[credType['secret']],
                  host=url['host'], port=url['port'], path=url['path'],
                  secure=False)

    conn.list_keys = lambda : conn.connection.request(conn.path, params={'Action': 'DescribeKeyPairs'})

    api_request(options, conn)
    

def resource_by_id(id, resources):
    image = CloudTools.findBy("id", resources, id)
    if image is None:
        return '[]'
    i_dict = image.__dict__
    del i_dict['driver']
    return json.dumps([i_dict])

def keypair_by_name(name, keypairs):
    for key in keypairs:
        if 'name' in key and key['name'] == name:
            return key

        
def api_request(options, conn):
    try:
        # LIST
        if options.list == "images":
            if options.id:
                json_results = resource_by_id(options.id, conn.list_images())
            else:
                json_results = CloudTools.jsonifyLList(conn.list_images())
            json_results = json_results.replace(
                '"imagetype": "ramdisk"',
                '"imagetype":"ramdisk","container_format":"ari"')
            json_results = json_results.replace(
                '"imagetype": "kernel"',
                '"imagetype":"kernel","container_format":"aki"')
            json_results = json_results.replace(
                '"imagetype": "machine"',
                '"imagetype":"machine","container_format":"ami"')

            json_results = json_results.replace('"state": "available"','"state": "active"')

            if options.limit:
                start = 0
                if options.marker:
                    logger.debug("marker is set")
                    logger.debug(options.marker)

                    # I think my logic here was that if the marker
                    # was an OpenStack image than we aren't even looking
                    # at these images yet however this means that either
                    # we have looked at all of them or none of them yet
                    # in the latter case we will never be able to look
                    # at them so I would rather choose the less wrong
                    # option of always showing them.
#                    if not options.marker.startswith(('emi','eki','eri')):
#                        start = limit
#                    else:
                    for index, image in enumerate(json.loads(json_results)):
                        if image['id'] == options.marker:
                            start = index + 1
                     
                logger.debug("the limit: %s", options.limit)
                logger.debug(len(json.loads(json_results)))
                logger.debug(start + options.limit)
                json_results = json.dumps(json.loads(json_results)[start:start + options.limit])
		

            print json_results

        elif options.list == "instances":
            if options.id:
        	json_results = resource_by_id(options.id, conn.list_nodes())
            else:
        	json_results = CloudTools.jsonifyLList(conn.list_nodes())
            print json_results.replace('"status": "running"','"status": "active"')

        elif options.list == "keys":
            aws_schema = "http://ec2.amazonaws.com/doc/2010-08-31/"
            xml_as_dict = xmldict.xml_to_dict(conn.list_keys().__dict__['body'].replace(aws_schema, ''))
            if xml_as_dict["DescribeKeyPairsResponse"]["keySet"] is None:
        	print []
            else:
        	result =  xml_as_dict["DescribeKeyPairsResponse"]["keySet"]["item"]


        	if 'keyName' in result:
        	    result['keyMaterial'] = ""
        	    result = [result]
        	else:
        	    for item in result:
        	        if 'keyName' in result:
        			item['keyMaterial'] = ""

        	if options.id:
        	    result = keypair_by_name(options.id, result)
                keys_json = json.dumps(result)
                print(keys_json)

        # ACTIONS
        elif options.action == "launch":
            try:
        	img = CloudTools.findBy("id", conn.list_images(), options.id)
                sze = CloudTools.findBy("id", conn.list_sizes(), options.size)
        	if hasattr(options, 'keyname') and options.keyname is not None:
        	    if hasattr(options, 'userdata') and options.userdata is not None:
        		conn.create_node(name='', image=img, size=sze,
                            ex_keyname=options.keyname,
                            ex_mincount=options.number,
        		    ex_userdata=base64.b64decode(options.userdata))
        	    else:			
        		conn.create_node(name='', image=img, size=sze, 
        		    ex_keyname=options.keyname, 
        		    ex_mincount=options.number)

        	print(CloudTools.SUCCESS)
            except InvalidCredsError:
                raise InvalidCredsError()
            except:
        	print '[{"message": "Quota exceeded: code=InstanceLimitExceeded", "code": 413, "retryAfter": 0}]'

        elif options.action == "kill":
            ins = CloudTools.findBy("id", conn.list_nodes(), options.id)
            conn.destroy_node(ins)
            print(CloudTools.SUCCESS)

        elif options.action == "create_keypair":
            try:
        	resp = conn.ex_create_keypair(name=options.keyname)
    		for keys in resp:
        	    resp[keys] = resp[keys].replace('\n','\\n')
        	resp['keyName'] = options.keyname
        	print json.dumps([resp])
            except InvalidCredsError:
        	raise InvalidCredsError()
            except:
        	print '[{"message": "Key pair \'' + options.keyname + '\' already exists.", "code": 409}]'

        elif options.action == "import_keypair":
            resp = conn.ex_import_keypair(name=options.keyname, keyfile=options.keyfile)
            for keys in resp:
                resp[keys] = resp[keys].replace('\n','\\n')
            print json.dumps([resp])
            
    except InvalidCredsError:
        time.sleep(2)
        api_request(options, conn)
            
            
if __name__ == "__main__":
    main()
