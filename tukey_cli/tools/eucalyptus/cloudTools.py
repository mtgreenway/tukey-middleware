# Grossman Computing Laboratory
# Institute for Genomics and Systems Biology
# The University of Chicago 900 E 57th St KCBD 10146, Chicago, IL 60637
# Tel: +1-773-702-9765. Fax: +1-773-834-2877
# ------------------------------------------
#
# Matthew Greenway <mgreenway@uchicago.edu>

# Utility functions for querying Eucalyptus clouds

import json
from optparse import OptionParser

class CloudTools:
    parser = OptionParser()
    parser.add_option("-l", "--list", action="store", type="string", dest="list")
    parser.add_option("-a", "--action", action="store", type="string", dest="action")
    parser.add_option("-i", "--id", action="store", type="string", dest="id")
    parser.add_option("-s", "--size", action="store", type="string", dest="size")
    parser.add_option("-k", "--keyname", action="store", type="string", dest="keyname")
    parser.add_option("-n", "--number", action="store", type="string", dest="number", default="1")
    parser.add_option("-c", "--credentials", action="store", type="string", dest="cred")
    parser.add_option("-d", "--keydir", action="store", type="string", dest="keydir")
    parser.add_option("-p", "--keyfile", action="store", type="string", dest="keyfile")
    parser.add_option("-q", "--limit", action="store", type="int", dest="limit")
    parser.add_option("-m", "--marker", action="store", type="string", dest="marker")
    parser.add_option("-u", "--userdata", action="store", type="string", dest="userdata")
    # b is for bucket
    parser.add_option("-b", "--container", action="store", type="string", dest="container")
    parser.add_option("-o", "--object", action="store", type="string", dest="object")
    parser.add_option("-f", "--file", action="store", type="string", dest="file")
        
    euca = {'key':'EC2_ACCESS_KEY', 'secret':'EC2_SECRET_KEY', 'host':'EC2_URL', 'storage':'S3_URL'}
    
    SUCCESS = '[{"result": "success"}]'
    ERROR   = '[{"result": "error"}]'
    
    @staticmethod
    def parseEucarc(input):
        """ Parse eucarc and returns a dictionary with the environment variables
        :param input: string of the eucarc file
        """
        EC2Dict = dict()
        
        lines = input.split('\n')
        for line in lines:
            splitLine = line.split(' ')
            if len(splitLine) != 2:
                continue
            keyPair = splitLine[1].split('=')
            EC2Dict[keyPair[0]] = keyPair[1].strip("'")
        return EC2Dict
        
    @staticmethod
    def parseHost(url):
        """ Parse URL of the type found in eucarc EC2_URL. 
        Returns dict with keys 'host','port','path'
        :param url: full URL with port and path for cloud api interface
        """
        # this seems like a job for regexp 
        sections = url.split(':')
        hostPortPath = dict()
        hostPortPath['host'] = sections[1][2:]
        hostPortPath['port'] = sections[2].split('/')[0]
        hostPortPath['path'] = sections[2][len(hostPortPath['port']):]
        return hostPortPath
        
    @staticmethod
    def jsonifyLList(list):
        """ JSONify an object returned by conn.list_images
        :param list: something like conn.list_images 
        """
        jsonified = ''
        for element in list:
            dic = element.__dict__
            if 'driver' in dic:
                del dic['driver']
            if 'container' in dic:
                del dic['container']
            jsonified += json.dumps(dic) + ','
        return '[' + jsonified[0:-1] + ']'
       
    @staticmethod
    def findBy(attr, list, id):
        """ search for element with 'id' in list
        :param list: something like conn.list_images
        :param id:   something like 'eki-E7641078'
        """
        for element in list:
            if getattr(element, attr) == id:
                return element
            
    @staticmethod
    def result(res):
        """ if res is true then print the success string
        if res is false print the error string
        :param res: True or False like delete_container() returns
        """
        if res:
            print(CloudTools.SUCCESS)
        else:
            print(CloudTools.ERROR)
            
    @staticmethod
    def notImplemented():
        print("not implemented")
    
