'''
Created on Apr 10, 2012

@author: Matt
'''
import unittest
from jsonTransform.jsonTransform import Transformer
from ConfigParser import ConfigParser


class Test(unittest.TestCase):


    def testConfigParser(self):
        config = ConfigParser()
        
        config.read("config/test.conf")
        
        section = "transformations:listInstances"
        
        self.assertEqual(config.sections()[1], section)
        
        self.assertEqual(config.options(section)[0], "address")
        
        self.assertEqual(config.get(section,"address"), "addresses/igsbnet/[0]/addr")
        
    def testConfigWithJson(self):
        config = ConfigParser()
        config.read("config/test.conf")
        trans = Transformer()
        
        section = "transformations:listInstances"
        
        for rule in config.options(section):
            print rule
            path = config.get(section, rule)
            print trans.transform('{' + 
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
                 '    }', rule, path)
        
        
    def testCommandConf(self):
        config = ConfigParser()
        config.read("config/test.conf")
        
        section = "commands"
        
        self.assertEqual(config.sections()[0], section)
        
        #self.assertEqual(config.options(section)[0], "listInstances")
        
        print config.get(section,"listInstances")
        #self.assertEqual(, "/usr/bin/python /var/lib/cloudgui/compute.py ", msg)
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testConfigParser']
    unittest.main()