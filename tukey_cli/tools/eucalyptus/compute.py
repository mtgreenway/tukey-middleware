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

from boto.ec2.connection import EC2Connection
from boto.exception import EC2ResponseError
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

    credFile = open(options.cred, 'r')
    credentials = CloudTools.parseEucarc(credFile.read())
    credFile.close()

    credType = CloudTools.euca

    url = CloudTools.parseHost(credentials[credType['host']])

    if options.ec2:
        api_handler = EC2(credentials[credType['key']],
            credentials[credType['secret']], url['host'], url['path'], options)
    else:
        api_handler = Eucalyptus(credentials[credType['key']],
            credentials[credType['secret']], url['host'], url['port'],
            url['path'], options)

    api_handler.api_request()
    

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


class Compute(object):
    ''' Shared compute actions between Eucalyptus and EC2 '''

    def list_instances(self):
        ''' List instances if options.id is set then just list info on that
        instance '''
    
        if self.options.id:
            json_results = resource_by_id(self.options.id, self.conn.list_nodes())
        else:
            json_results = CloudTools.jsonifyLList(self.conn.list_nodes())
        return json_results.replace('"status": "running"','"status": "active"')
    
    
    def list_keys(self):
        ''' List the keys, libcloud didn't work so we had to fetch some xml'''
    
        aws_schema = "http://ec2.amazonaws.com/doc/2010-08-31/"
        xml_as_dict = xmldict.xml_to_dict(self.conn.connection.request(
            self.conn.path, params={'Action': 'DescribeKeyPairs'}
            ).__dict__['body'].replace(aws_schema, ''))
        if xml_as_dict["DescribeKeyPairsResponse"]["keySet"] is None:
            return "[]"
        else:
            result = xml_as_dict["DescribeKeyPairsResponse"]["keySet"]["item"]
    
            if 'keyName' in result:
                result['keyMaterial'] = ""
                result = [result]
            else:
                for item in result:
                    if 'keyName' in result:
                        item['keyMaterial'] = ""
    
            if self.options.id:
                result = keypair_by_name(self.options.id, result)
            keys_json = json.dumps(result)
            return keys_json
    
    
    def launch_instance(self):
        ''' Launch an instance need to clean up the exception logic '''
        
        try:
            img = CloudTools.findBy("id", self.conn.list_images(),
                self.options.id)
            sze = CloudTools.findBy("id", self.conn.list_sizes(),
                self.options.size)
            if hasattr(self.options, 'keyname') and self.options.keyname is not None:
                if hasattr(self.options, 'userdata') and self.options.userdata is not None:
                    self.conn.create_node(name='', image=img, size=sze,
                        ex_keyname=self.options.keyname,
                        ex_mincount=self.options.number,
                        ex_userdata=base64.b64decode(self.options.userdata))
                else:
                    self.conn.create_node(name='', image=img, size=sze,
                        ex_keyname=self.options.keyname,
                        ex_mincount=self.options.number)
    
            return CloudTools.SUCCESS
        except InvalidCredsError:
            raise InvalidCredsError()
        except:
            return '[{"message": "Quota exceeded: code=InstanceLimitExceeded", "code": 413, "retryAfter": 0}]'
    
    def delete_instance(self, instance_id):
        ''' Delete the instance with id instance_id'''
    
        ins = CloudTools.findBy("id", self.conn.list_nodes(), instance_id)
        self.conn.destroy_node(ins)
        return CloudTools.SUCCESS
    
    def create_keypair(self, keyname, conn):
        ''' Create a new keypair '''
        try:
            resp = conn.ex_create_keypair(name=keyname)
            for keys in resp:
                resp[keys] = resp[keys].replace('\n','\\n')
            resp['keyName'] = keyname
            return json.dumps([resp])
        except InvalidCredsError:
            raise InvalidCredsError()
        except:
            return '[{"message": "Key pair \'' + keyname + '\' already exists.", "code": 409}]'
   
    def list_sizes(options, conn):
        ''' TODO: clean shouldn't be going to JSON then back to objects'''
        sizes_json = CloudTools.jsonifyLList(conn.list_sizes())
        sizes = json.loads(sizes_json)
        return json.dumps({s["id"]: s for s in sizes})
    
    def api_request(self):#self.options, self.conn):
        try:
            # LIST
            if self.options.list == "images":
                print self.list_images()
    
            elif self.options.list == "instances":
                print self.list_instances()
                
            elif self.options.list == "keys":
                print self.list_keys()
    
            elif self.options.list == "sizes":
                print self.list_sizes()
    
            # ACTIONS
            elif self.options.action == "launch":
                print self.launch_instance()
    
            elif self.options.action == "kill":
                print self.delete_instance(self.options.id)
    
            elif self.options.action == "create_keypair":
                print self.create_keypair(self.options.keyname, self.conn)
    
            elif self.options.action == "import_keypair":
                print self.import_keypair(self.options.keyname,
                    self.options.keyfile, self.conn)
                
        except InvalidCredsError:
            # Eucalyptus rate limits requests
            time.sleep(2)
            self.api_request()


class Eucalyptus(Compute):
    ''' Eucalyptus specific compute api '''

    def __init__(self, key, secret, host, port, path, options):

        Driver = get_driver(Provider.EUCALYPTUS)
        self.conn = Driver(key, secret=secret, host=host, port=port, path=path,
            secure=False)
        self.options = options

    def list_images(self):
        ''' Returns JSON list of images '''
    
        if self.options.id:
            json_results = resource_by_id(self.options.id,
                self.conn.list_images())
        else:
            json_results = CloudTools.jsonifyLList(self.conn.list_images())
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
    
        if self.options.limit:
            start = 0
            if self.options.marker:
                logger.debug("marker is set")
                logger.debug(self.options.marker)
    
                for index, image in enumerate(json.loads(json_results)):
                    if image['id'] == self.options.marker:
                        start = index + 1
                 
            logger.debug("the limit: %s", self.options.limit)
            logger.debug(len(json.loads(json_results)))
            logger.debug(start + self.options.limit)
            json_results = json.dumps(
                json.loads(json_results)[start:start + self.options.limit])
    
        return json_results


class EC2(Compute):
    ''' EC2 specific compute api '''
    
    def __init__(self, key, secret, host, path, options):

        Driver = get_driver(Provider.EC2)
        self.conn = Driver(key, secret=secret, host=host, path=path, secure=True)
        self.boto_conn = EC2Connection(key, secret)
        self.options = options

    def list_instances(self):
        ''' process ip '''
        
        vms = json.loads(super(EC2, self).list_instances())

        return json.dumps([dict(i.items() + [("public_ip", i["public_ips"][0])]) 
            if "public_ips" in i and len(i["public_ips"]) > 0 else i 
            for i in vms])
         
    def list_images(self):
        ''' For now just list the image that you own '''

        ign = ['region', 'connection', 'block_device_mapping']

        return json.dumps(
            [{k: i.__dict__["location"] if k == "name" and v is None else v
                for k, v in i.__dict__.items() if k not in ign}
                for i in self.boto_conn.get_all_images(owners=["self"])])
    
    def import_keypair(self, keyname, keyfile, conn):
        '''AWS will only accept RSA keys'''
        try:
            resp = conn.ex_import_keypair(name=keyname, keyfile=keyfile)
            for keys in resp:
                resp[keys] = resp[keys].replace('\n','\\n')
            return json.dumps([resp])
        except Exception, e:
            return '[{"message": "%s", "code": 409}]' % e.message

            
 

if __name__ == "__main__":
    main()
