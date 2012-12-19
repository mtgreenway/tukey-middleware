# Copyright 2012 Open Cloud Consortium
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


'''
Created on Apr 10, 2012

@author: Matt
'''

import json
import re



class Transformer(object):
    '''
    classdocs
    '''
    
    __INDEX_LEFT  = '['
    __INDEX_RIGHT = ']'
    __PATH_DEL    = '/'
    __ALL         = 'all'
    

        
    def transform(self, json_string, name, path):
        '''
            from json return new json string that has the attribute
            name with the value specified by path such as:
            name="address" path="addresses/igsbnet/[0]/igsbnet/addr"
            
            ...
            "addresses": {
                "igsbnet": [
                    {
                        "version": 4,
                        "addr": "172.16.2.119"
                    }
                ]
            }
            ...
            "address": "172.16.2.119"
        '''
        j_object = self.loads(json_string)
        
        transformed = self.transform_templates(json_string, path)

	#print "TRANSFORMED", transformed
        
        try:
            j_object[name] = self.loads(transformed)
        except ValueError:
            j_object[name] = self.loads('"' + transformed + '"')
        
        return json.dumps(j_object)
    
    
    def loads(self, json_string):
	return json.loads(json_string)
    
    def json_pathlike(self, json_string, path):
        '''
            Performs a transformation that is similar to a subset of JSONPath
            or JPATH essentially XPath for JSON.
            
            The differences are:
                1. This is Zero indexed
                2. This is a very minimal subset of JSONPath
                
            From JSON object and a path return new attribute that matches
            name with the value specified by path such as:
            name="address" path="addresses/igsbnet/[0]/igsbnet/addr"
            
            ...
            "addresses": {
                "igsbnet": [
                    {
                        "version": 4,
                        "addr": "172.16.2.119"
                    }
                ]
            }
            ...
            "172.16.2.119"
            
            or "" if not found                
        '''
        
        new_val = self.loads(json_string)
        
        attrs = path.split(Transformer.__PATH_DEL)
        
        left    = Transformer.__INDEX_LEFT
        right   = Transformer.__INDEX_RIGHT
        
        found = True
        
        for attr in attrs:
            if len(attr) > 0 and attr[0] == left and attr[-1] == right:
                index = int(attr[1:-1])
                new_val = new_val[index]
            
            elif attr in new_val:    
                new_val = new_val[attr]
                
            else:
                found = False
                break
                
        if found:
            return new_val
        
        return ""
        
    
    def transform_templates(self, json_string, template):
        '''
            For each $(rule) replace with the executed rule and then process
            the template.
        '''
        replaced = re.sub('\$\((.*?)\)', lambda match: self.json_pathlike(json_string, match.group(1)), template)
        
        return self.template_to_json(replaced)
    
    def template_to_json(self, template):
        '''
            This JSON template format is the same as JSON with the colons
            removed.  All colons can be inferred because attribute names are
            always surrounded by quotes and the only place a colon exists is
            after an attribute name.
            
            The reason colons are missing in the template JSON is so colonless
            JSON templates can be used in Python config files used by the 
            ConfigParser class.
            
            The regex "\s+("|\{|\[|\w) is matched against the template
            replacing replacing each instance with ": \g<1> 
        '''
        return re.sub('"\s+("|\{|\[|\w)', r'": \g<1>', template)
        
        
    
    def transform_list(self, json_string, name, path):
        '''
            json_string is a json list.
            Returns transform on each element
        '''
        
        j_list = self.loads(json_string)
	#print "JLIST IN", json_string
	#print "J_LIST OBJ", j_list
        new_list = []
        
        for j_obj in j_list:
	    
            j_string = json.dumps(j_obj)
            new_json = self.transform(j_string, name, path)
	    #print "NEW_JSON", new_json
            new_list.append(self.loads(new_json))
            
        return json.dumps(new_list)
    
    def add_attr_list(self, json_string, attr, value):
        '''
            json_string is a json list for each element of 
            that list add the attribute
        '''
        j_objs = self.loads(json_string)

        for j_obj in j_objs:
            j_obj[attr] = value
    
        return json.dumps(j_objs)
    
    def add_attr(self, json_string, attr, value):
        '''
            json_string is json object.  Returns the
            attr with value as a json string
        '''
        
        j_obj = self.loads(json_string)
        j_obj[attr] = value
        
        return json.dumps(j_obj)
        
    
    def strip(self, json_string, value):
        '''
            if the entire json is one object with name value
            this will return that objects attribute.
            Commonly a list of the needed values
        '''
        
        new_j = j_object = self.loads(json_string)
        
        if type(j_object).__name__ != 'dict':
            return json_string
        
        if value in j_object.keys():
            new_j = j_object[value]
            
        return json.dumps(new_j)
    
    
    def empty_none(self):
	'''
	    retturn an empty json list
	'''
	return '[]'

    def empty(self):
        '''
            return a json list with an empty json object string
        '''
        
        return "[{}]"
    
    def encode(self, obj):
        '''
            encode the dictionary in json
        '''
        return json.dumps(obj)
    
    def decode(self, dto_string):
        '''
            decode the dto sring into a dictionary
        '''
        return self.loads(dto_string)
