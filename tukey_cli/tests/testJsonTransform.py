'''
Created on Apr 10, 2012

@author: Matt
'''
import unittest
import json
from jsonTransform.jsonTransform import Transformer

class TestTransformer(unittest.TestCase):

    def setUp(self):
        self.trans = Transformer()
        
        self.json_string = str('{' + 
 '        "status": "ACTIVE",' + 
 '        "updated": "2012-04-10T18:46:58Z",' + 
 '        "hostId": "1b7a88a0ced014a91f2a41e8d03dc8923548e39471371285640247ae",' + 
 '        "user_id": "adminUser",' + 
 '        "name": "tester",' + 
 '        "links": [' + 
 '            {' + 
 '                "href": "http://172.16.1.1:8774/v1.1/adminTenant/servers/500",' + 
 '                "rel": "self"' + 
 '            },' + 
 '            {' + 
 '                "href": "http://172.16.1.1:8774/adminTenant/servers/500",' + 
 '                "rel": "bookmark"' + 
 '            }' + 
 '        ],' + 
 '        "addresses": {' + 
 '            "igsbnet": [' + 
 '                {' + 
 '                    "version": 4,' + 
 '                    "addr": "172.16.2.119"' + 
 '                }' + 
 '            ]' + 
 '        },' + 
 '        "tenant_id": "1",' + 
 '        "image": {' + 
 '            "id": "7",' + 
 '            "links": [' + 
 '                {' + 
 '                    "href": "http://172.16.1.1:8774/adminTenant/images/7",' + 
 '                    "rel": "bookmark"' + 
 '                }' + 
 '            ]' + 
 '        },' + 
 '        "created": "2012-04-10T18:46:47Z",' + 
 '        "uuid": "d72c9f9d-6988-4369-9fca-9f3d799fe965",' + 
 '        "accessIPv4": "",' + 
 '        "accessIPv6": "",' + 
 '        "key_name": "new_key",' + 
 '        "progress": 100,' + 
 '        "flavor": {' + 
 '            "id": "1",' + 
 '            "links": [' + 
 '                {' + 
 '                    "href": "http://172.16.1.1:8774/adminTenant/flavors/1",' + 
 '                    "rel": "bookmark"' + 
 '                }' + 
 '            ]' + 
 '        },' + 
 '        "config_drive": "",' + 
 '        "id": 500,' + 
 '        "metadata": {}' + 
 '    }')
        
        self.euca_instances = str('{' +
                '"username": "test",' +
                '"id": "i-47F6083A",' +
                '"image": "emi-59EA120E",' +
                '"address": "10.103.112.63",' +
                '"status": "running",' +
                '"host": "kg12-compute-17",' +
                '"launchindex": "0",' +
                '"instancetype": "c1.xlarge",' +
                '"launchdatetime": "2012-04-06T21:53:16.59Z",' +
                '"placement": "kg12",' +
                '"kernel": "eki-E7641078",' +
                '"ramdisk": "eri-1BF61154"' +
            '}')
         

    def tearDown(self):
        pass

    def testTransformation(self):
        '''
        
        '''
        new_json = self.trans.transform(self.json_string, "address", "$(addresses/igsbnet/[0]/addr)")
        
        j_obj = json.loads(new_json)
        
        self.trans.transform('{"status": "ACTIVE"}', "name", "$(test/not)")
        
        self.assertEquals(j_obj["address"], "172.16.2.119")
        

    def testTransformList(self):
        new_json = self.trans.transform_list('[' + self.json_string + ']', "address", "$(addresses/igsbnet/[0]/addr)")
        
        j_obj = json.loads(new_json)
        
        self.assertEquals(j_obj[0]["address"], "172.16.2.119")
        
        
    def testStrip(self):
        
        orig_json = '{"servers":[{"status": "ACTIVE", "updated": "2012-04-10T18:46:58Z", "hostId": "1b7a88a0ced014a91f2a41e8d03dc8923548e39471371285640247ae", "user_id": "adminUser", "name": "tester", "links": [{"href": "http://172.16.1.1:8774/v1.1/adminTenant/servers/500", "rel": "self"}, {"href": "http://172.16.1.1:8774/adminTenant/servers/500", "rel": "bookmark"}], "created": "2012-04-10T18:46:47Z", "tenant_id": "1", "image": {"id": "7", "links": [{"href": "http://172.16.1.1:8774/adminTenant/images/7", "rel": "bookmark"}]}, "uuid": "d72c9f9d-6988-4369-9fca-9f3d799fe965", "accessIPv4": "", "metadata": {}, "accessIPv6": "", "key_name": "new_key", "progress": 100, "flavor": {"id": "1", "links": [{"href": "http://172.16.1.1:8774/adminTenant/flavors/1", "rel": "bookmark"}]}, "config_drive": "", "id": 500, "addresses": {"igsbnet": [{"version": 4, "addr": "172.16.2.119"}]}}]}'
        
        
        # Using json.loads and json.dumps are not inverses of each other
        # the ordering of the string is not the same
        # however comparing dictionaries will work
        
        expected = '[{"status": "ACTIVE", "updated": "2012-04-10T18:46:58Z", "hostId": "1b7a88a0ced014a91f2a41e8d03dc8923548e39471371285640247ae", "user_id": "adminUser", "name": "tester", "links": [{"href": "http://172.16.1.1:8774/v1.1/adminTenant/servers/500", "rel": "self"}, {"href": "http://172.16.1.1:8774/adminTenant/servers/500", "rel": "bookmark"}], "created": "2012-04-10T18:46:47Z", "tenant_id": "1", "image": {"id": "7", "links": [{"href": "http://172.16.1.1:8774/adminTenant/images/7", "rel": "bookmark"}]}, "addresses": {"igsbnet": [{"version": 4, "addr": "172.16.2.119"}]}, "accessIPv4": "", "accessIPv6": "", "config_drive": "", "key_name": "new_key", "progress": 100, "flavor": {"id": "1", "links": [{"href": "http://172.16.1.1:8774/adminTenant/flavors/1", "rel": "bookmark"}]}, "metadata": {}, "id": 500, "uuid": "d72c9f9d-6988-4369-9fca-9f3d799fe965"}]'
        
        trans = Transformer()
        
        new_json = trans.strip(orig_json, 'servers')
        
        e_obj = json.loads(expected)
        
        n_obj = json.loads(new_json)
        
        self.assertEquals(n_obj, e_obj)
        
        
    def testTemplate_to_json(self):
        template = str('{' +
             '"private" [' +
             '   {' +
             '      "version" 4,' +
             '     "addr" "$(address)"' +
             '}' +
             ']' +
         '}')
        
        processed = str('{' +
             '"private": [' +
             '   {' +
             '      "version": 4,' +
             '     "addr": "$(address)"' +
             '}' +
             ']' +
         '}')
        
        trans = Transformer()
        
        #print trans.template_to_json(template)
        
        self.assertEquals(trans.template_to_json(template), processed)
        
    def testTranform_templates(self):
        
        trans = Transformer()
        template = str('''{
             "private" [
                {
                   "version" 4,
                  "addr" "$(address)"
             }
             ]
         }''')
        
        json_str = '''{
            "username": "test",
            "id": "i-47F6083A",
            "image": "emi-59EA120E",
            "address": "10.103.112.63",
            "status": "running",
            "host": "kg12-compute-17",
            "launchindex": "0",
            "instancetype": "c1.xlarge",
            "launchdatetime": "2012-04-06T21:53:16.59Z",
            "placement": "kg12",
            "kernel": "eki-E7641078",
            "ramdisk": "eri-1BF61154"
        }'''

        result = trans.transform_templates(json_str, template)
        
        address = json.loads(result)['private'][0]['addr']
        
        self.assertEqual(address, '10.103.112.63')
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()