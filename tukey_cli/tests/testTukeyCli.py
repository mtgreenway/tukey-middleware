'''
Created on Apr 11, 2012

@author: Matt
'''
import unittest
import json
from tukeyCli.tukeyCli import TukeyCli
from jsonTransform.jsonTransform import Transformer


class Test(unittest.TestCase):


    def setUp(self):
        self.sites_enabled = 'config/sites-enabled/'
        self.config_dir = 'config/'
        self.site1 = 'nova.conf'
        self.site2 = 'test.conf'
        self.nova2 = 'nova2.conf'
        self.list_instances = 'listInstances'
        
        self.cli = TukeyCli(Transformer())
        self.cli.load_config_dir(self.sites_enabled)


    def tearDown(self):
        pass


    def testConfigCheck(self):
        # The only thing that is essential is to have 
        # the check-creds section and that must have a
        # command option
        
        valid_conf = self.config_dir + 'test.conf'
        
        no_command = self.config_dir + 'noCredCommand.conf'
        
        no_check_creds = self.config_dir + 'noCheck-creds.conf'
        
        nonexisting_file = 'nope.nope'
        
        self.assertTrue(self.cli.check_config(valid_conf))
        
        self.assertTrue(not self.cli.check_config(nonexisting_file))        
        
        self.assertTrue(not self.cli.check_config(no_command))
        
        self.assertTrue(not self.cli.check_config(no_check_creds))
        
        
    def testLoadConfigs(self):
        #base dir that contains broken config files
        self.assertTrue(not self.cli.load_config_dir(self.config_dir))
        
        #good dir with only good config files
        self.assertTrue(self.cli.load_config_dir(self.sites_enabled))
        
        self.assertTrue(self.cli.load_config_dir(self.sites_enabled + self.site1))
        
    
    def testSites(self):
        '''
            sites are loaded when config is loaded
        '''        
        self.assertTrue(self.site1 in self.cli.get_sites())
        
        self.assertTrue(self.site2 in self.cli.get_sites())
        
        
    
    def testCheckEnabled(self):
        # nova.conf has a link to scripts\fail.bat
        self.assertTrue(not self.cli.check_enabled(self.site1, dict()))
        
        self.assertTrue(self.cli.check_enabled(self.site2, dict()))
        
    
    def testReplaceVar(self):
        values = dict()
        values["USER"] = 'test'
        values["TEST"] = 'user'
        
        orig = "test ${USER} ${USER}s${TEST}"
        
        expected = "test test testsuser"
        
        new_str = self.cli.replace_var(orig, values)
        
        self.assertEquals(new_str, expected)
        
    
    def testGenerateCommands(self):
        
        values = {self.site2: {"USER": "matt"}}
        commands = self.cli.generate_commands(self.list_instances, values)
        
        expected = '/usr/bin/python /var/lib/cloudgui/compute.py --credentials /var/lib/cloudgui/users/matt/.euca/eucarc --list instances'
        self.assertEquals(commands[self.site2], expected)
        
        
    def testStrip(self):
        result = '{"servers":[{"status": "ACTIVE", "updated": "2012-04-10T18:46:58Z", "hostId": "1b7a88a0ced014a91f2a41e8d03dc8923548e39471371285640247ae", "user_id": "adminUser", "name": "tester", "links": [{"href": "http://172.16.1.1:8774/v1.1/adminTenant/servers/500", "rel": "self"}, {"href": "http://172.16.1.1:8774/adminTenant/servers/500", "rel": "bookmark"}], "created": "2012-04-10T18:46:47Z", "tenant_id": "1", "image": {"id": "7", "links": [{"href": "http://172.16.1.1:8774/adminTenant/images/7", "rel": "bookmark"}]}, "uuid": "d72c9f9d-6988-4369-9fca-9f3d799fe965", "accessIPv4": "", "metadata": {}, "accessIPv6": "", "key_name": "new_key", "progress": 100, "flavor": {"id": "1", "links": [{"href": "http://172.16.1.1:8774/adminTenant/flavors/1", "rel": "bookmark"}]}, "config_drive": "", "id": 500, "addresses": {"igsbnet": [{"version": 4, "addr": "172.16.2.119"}]}}]}'
        result2 = '[{"status": "ACTIVE", "updated": "2012-04-10T18:46:58Z", "hostId": "1b7a88a0ced014a91f2a41e8d03dc8923548e39471371285640247ae", "user_id": "adminUser", "name": "tester", "links": [{"href": "http://172.16.1.1:8774/v1.1/adminTenant/servers/500", "rel": "self"}, {"href": "http://172.16.1.1:8774/adminTenant/servers/500", "rel": "bookmark"}], "created": "2012-04-10T18:46:47Z", "tenant_id": "1", "image": {"id": "7", "links": [{"href": "http://172.16.1.1:8774/adminTenant/images/7", "rel": "bookmark"}]}, "uuid": "d72c9f9d-6988-4369-9fca-9f3d799fe965", "accessIPv4": "", "metadata": {}, "accessIPv6": "", "key_name": "new_key", "progress": 100, "flavor": {"id": "1", "links": [{"href": "http://172.16.1.1:8774/adminTenant/flavors/1", "rel": "bookmark"}]}, "config_drive": "", "id": 500, "addresses": {"igsbnet": [{"version": 4, "addr": "172.16.2.119"}]}}]'
        stripped = self.cli.strip(result, self.nova2, self.list_instances)
        
        old_obj = json.loads(result)
        new_obj = json.loads(stripped)
        
        self.assertEquals(old_obj['servers'],new_obj)
        
        stripped = self.cli.strip(result2, self.nova2, self.list_instances)
        
        new_obj = json.loads(stripped)
        
        self.assertEquals(old_obj['servers'],new_obj)
        
    def testTransform(self):
        json_string = '[{"status": "ACTIVE", "updated": "2012-04-10T18:46:58Z", "hostId": "1b7a88a0ced014a91f2a41e8d03dc8923548e39471371285640247ae", "user_id": "adminUser", "name": "tester", "links": [{"href": "http://172.16.1.1:8774/v1.1/adminTenant/servers/500", "rel": "self"}, {"href": "http://172.16.1.1:8774/adminTenant/servers/500", "rel": "bookmark"}], "created": "2012-04-10T18:46:47Z", "tenant_id": "1", "image": {"id": "7", "links": [{"href": "http://172.16.1.1:8774/adminTenant/images/7", "rel": "bookmark"}]}, "addresses": {"igsbnet": [{"version": 4, "addr": "172.16.2.119"}]}, "accessIPv4": "", "accessIPv6": "", "config_drive": "", "key_name": "new_key", "progress": 100, "flavor": {"id": "1", "links": [{"href": "http://172.16.1.1:8774/adminTenant/flavors/1", "rel": "bookmark"}]}, "metadata": {}, "id": 500, "uuid": "d72c9f9d-6988-4369-9fca-9f3d799fe965"}]'
        result = self.cli.transform(json_string, self.nova2, self.list_instances, {})
        res_obj = json.loads(result)
        
        self.assertTrue('address' in res_obj[0].keys())
        
    def testTag(self):
        json_string = '[{"status": "ACTIVE", "updated": "2012-04-10T18:46:58Z", "hostId": "1b7a88a0ced014a91f2a41e8d03dc8923548e39471371285640247ae", "user_id": "adminUser", "name": "tester", "links": [{"href": "http://172.16.1.1:8774/v1.1/adminTenant/servers/500", "rel": "self"}, {"href": "http://172.16.1.1:8774/adminTenant/servers/500", "rel": "bookmark"}], "created": "2012-04-10T18:46:47Z", "tenant_id": "1", "image": {"id": "7", "links": [{"href": "http://172.16.1.1:8774/adminTenant/images/7", "rel": "bookmark"}]}, "addresses": {"igsbnet": [{"version": 4, "addr": "172.16.2.119"}]}, "accessIPv4": "", "accessIPv6": "", "config_drive": "", "key_name": "new_key", "progress": 100, "flavor": {"id": "1", "links": [{"href": "http://172.16.1.1:8774/adminTenant/flavors/1", "rel": "bookmark"}]}, "metadata": {}, "id": 500, "uuid": "d72c9f9d-6988-4369-9fca-9f3d799fe965"}]'
        result = self.cli.tag(json_string, self.site2)
        j_objs = json.loads(result)
        for j_obj in j_objs:
            self.assertTrue('cloud' in j_obj)
        
    def testSetError(self):
        # test that is wont fail on a file without error
        self.cli.set_error(self.site1, self.list_instances, "test")
        
        result = self.cli.set_error(self.site2, self.list_instances, "test")
        
        res_obj = json.loads(result)
        
        self.assertEquals(res_obj[0]['error'], 'test')
        
    def testExecuteCommands(self):
        values = dict()
        values["USER"] = "matt"
        
        result = self.cli.execute_commands(self.list_instances, values)
        res_objs = json.loads(result)
        for res_obj in res_objs:
            self.assertTrue('address' in res_obj.keys() or 'error' in res_obj.keys())
        
    
    def testReplaceVarInResult(self):
        values = dict()
        values["USER"] = "matt"
        
        start_json = '''
            [{
                "id": "i-47F6083A",
                "user_id": "${USER}",
                "launchdatetime": "2012-04-06T21:53:16.59Z",
                "accessipv4": "",
                "tenant_id": "${USER}",
                "username": "test"
            }]'''
        
        result = self.cli.replace_var(start_json, values)
                
        res_obj = json.loads(result)
        
        self.assertEqual(res_obj[0]['user_id'], 'matt')
        
        
    def testNamedObjects(self):
        values = dict()
        values["USER"] = "matt"
        
        result = self.cli.execute_commands(self.list_instances, values,object_name="servers")
        
        res_obj = json.loads(result)
        self.assertTrue('servers' in res_obj.keys())        

        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testConfigCheck']
    unittest.main()