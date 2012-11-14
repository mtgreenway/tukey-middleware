#!/usr/bin/python

# Grossman Computing Laboratory
# Institute for Genomics and Systems Biology
# The University of Chicago 900 E 57th St KCBD 10146, Chicago, IL 60637
# Tel: +1-773-702-9765. Fax: +1-773-834-2877
# ------------------------------------------
#
# Matthew Greenway <mgreenway@uchicago.edu>


from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver
from libcloud.storage.base import Container
from cloudTools import CloudTools
from xml.etree.ElementTree import tostring, XML
import string
import tempfile
import json

def main():
    (options, args) = CloudTools.parser.parse_args()

    #eucalyptus specific, refactor
    credFile = open(options.cred, 'r')
    credentials = CloudTools.parseEucarc(credFile.read())
    credFile.close()
    credType = CloudTools.euca

    url = CloudTools.parseHost(credentials[credType['storage']])
        
    Driver = get_driver(Provider.S3)

    conn = Driver(credentials[credType['key']], secret=credentials[credType['secret']],
                  host=url['host'], port=url['port'], 
                  secure=False)
    
 
    # Eucalyptus HACK
    euca_namespace = 'ns0:'

    conn.connection.request_path = url['path']
    conn.namespace = '';
    conn.list_containers = lambda : conn._to_containers(
        XML(
            string.replace(
                tostring(
                    conn.connection.request('/').object
                ),
                euca_namespace,
                ''
            )
        ),
        xpath='ListAllMyBucketsResponse/Buckets/Bucket'
     )

    conn.list_container_objects = lambda container: conn._to_objs(
         obj=XML(
             string.replace(
                 tostring(
                     conn.connection.request(
                         '/%s' % (container.name),
                         params={}
                     ).object),
                     euca_namespace,
                     ''
             )
         ),
         xpath='ListBucketResponse/Contents', container=container
    )
    
    # LIST
    if options.list == "containers":
        print(CloudTools.jsonifyLList(conn.list_containers()))
    
    elif options.list == "objects":
        files = []
        for container in conn.list_containers():
            tempFiles = conn.list_container_objects(container)
            for file in tempFiles:
                file.__dict__['bucket_name'] = getattr(container, 'name')
                files.append(file)
        print(CloudTools.jsonifyLList(files))

    #ACTIONS
    elif options.action == "create_container":
        resp = conn.create_container(options.container)
        CloudTools.result(isinstance(resp, Container))
        
    elif options.action == "delete_container":
        container = CloudTools.findBy("name", conn.list_containers(), options.container)
        CloudTools.result(conn.delete_container(container))
        
    elif options.action == "upload_object":
        container = CloudTools.findBy("name", conn.list_containers(), options.container)
        conn.upload_object(options.file, container, options.object)
        print(CloudTools.SUCCESS)
        
    elif options.action == "download_object":
        container = CloudTools.findBy("name", conn.list_containers(), options.container)
        obj = CloudTools.findBy("name", conn.list_container_objects(container), options.object)
        temp = tempfile.NamedTemporaryFile(delete=False)
        conn.download_object(obj, temp.name, True)
        j_obj = dict()
        j_obj['filename'] = temp.name
        print(json.dumps([j_obj]))
        
    elif options.action == "delete_object":
        container = CloudTools.findBy("name", conn.list_containers(), options.container)
        object = CloudTools.findBy("name", conn.list_container_objects(container), options.object)
        CloudTools.result(conn.delete_object(object))
        
        
if __name__ == "__main__":
    main()
