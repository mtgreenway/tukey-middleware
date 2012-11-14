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


import auth_db
import datetime
import httplib
import json
import logging
import time



class AuthSystem(object):
    '''Authentication interface for mapping Shibboleth and OpenID attributes
    to internal authentication attributes.
    '''

    def authenticate(self, method, identifier):
        '''Authenticate a user with a federated method and ifentifier 
	like OpenID email attribute or Shibboleth EPPN


	:param method: The authentication method for example 'shibboleth'
		or 'openid'

        :param identifier: the user's email address obtained from OpenID
                metadata or user's Shibboleth EduPerson Principle Name
            see https://wiki.shibboleth.net.  And others...
        '''
        return None


class FakeId(object):
    '''Mixin for non Keystone authentication methods to return the 
    Keystone API for token, tenant and endpoint
    '''
    
    def _expiration(self):
	'''Returns times stamp of one day from now
	'''
	date_format = '%Y-%m-%dT%H:%M:%SZ'
	day = 24*60*60
	current = time.time()
	return str(datetime.datetime.fromtimestamp(current + day).strftime(date_format))


    def _format_token(self, username, user_id, token_id, expires):
        '''The Keystone API token format.
        '''
        token = {
            "expires": expires,
            "id":    token_id
            }

        user = {
            "username": username,
            "roles_links": [],
            "id": user_id,
            "roles": [],
            "name": username
            }

        return {
            "access":
                {
                    "token": token,
                    "serviceCatalog": {},
                    "user": user
                }
            }

    def _format_tenant(self, tenant_name, id):
        '''The Keystone API tenants format.
        '''
        return {
            "tenants_links": [],
            "tenants": [
                {
                "enabled": True,
                "description": None,
                "name": tenant_name,
                "id": id
                }
                ]
            }


    def _format_endpoint(self, token_id, tenant_id, user_id, tenant_name,
        username, expires, url):
        '''The Keystone API endpoints format.
        '''
        return {
        "access": {
            "token": {
                "expires": self._expiration(),
                "id": token_id,
                "tenant": {
                    "description": None,
                    "enabled": True,
                    "id": tenant_id,
                    "name": tenant_name
                }
            },
            "serviceCatalog": [
                {
                    "endpoints": [
                        {
                            "adminURL": "http://%s:9292/v1" % url,
                            "region": "RegionOne",
                            "publicURL": "http://%s:9292/v1" % url,
                            "internalURL": "http://%s:9292/v1" % url
                        }
                    ],
                    "endpoints_links": [],
                    "type": "image",
                    "name": "Image Service"
                },
                {
                    "endpoints": [
                        {
                            "adminURL": "http://%s:8774/v1.1/%s" % (url, tenant_id),
                            "region": "RegionOne",
                            "publicURL": "http://%s:8774/v1.1/%s" % (url, tenant_id),
                            "internalURL": "http://%s:8774/v1.1/%s" % (url, tenant_id)
                        }
                    ],
                    "endpoints_links": [],
                    "type": "compute",
                    "name": "Compute Service"
                },
#                {
#                    "endpoints": [
#                        {
#                            "adminURL": "http://%s:8773/services/Admin" % url,
#                            "region": "RegionOne",
#                            "publicURL": "http://%s:8773/services/Cloud" % url,
#                            "internalURL": "http://%s:8773/services/Cloud" % url
#                        }
#                    ],
#                    "endpoints_links": [],
#                    "type": "ec2",
#                    "name": "EC2 Service"
#                },
                {
                    "endpoints": [
                        {
			    # we may need to add this in the future
			    # for our admin stuff
                            #"adminURL": "http://%s:35357/v2.0" % url,
                            "region": "RegionOne",
                            "publicURL": "http://%s:5000/v2.0" % url,
                            "internalURL": "http://%s:5000/v2.0" % url
                        }
                    ],
                    "endpoints_links": [],
                    "type": "identity",
                    "name": "Identity Service"
                }
            ],
            "user": {
                "username": username,
                "roles_links": [],
                "id": user_id,
                "roles": [
                    {
                        "id": "7cc444dd12f4413c90f1f19e3c109f99",
                        "name": "Member"
                    }
                ],
                "name": username
            }
        }
    }


    def fake_token(self):
        '''Returns a JSON serializable object that is equivalent to what
        Keystone will return when requesting an auth token.
        '''
        pass

    def fake_tenant(self):
        '''Returns a JSON serializable object that is equivalent to what
        Keystone will return when requesting tenant info.
        '''    
        pass

    def fake_endpoint(self):
        '''Returns a JSON serializable object that is equivalent to what
        Keystone will return when requesting endpoint info.
        '''    
        pass

class OpenStackAuth(AuthSystem):
    '''Contacts database with OpenID or Shibboleth to get 
    OpenStack credentials.    
    '''

    def __init__(self, keystone_host, keystone_port):
        self.keystone_host = keystone_host
        self.keystone_port = keystone_port


    def authenticate(self, method, identifier, cloud_name):
        username, password = auth_db.userInfo(method, identifier, cloud_name)

        creds = {
            "username": username,
            "password": password
            }

        wrapped_creds = {
            "auth":
                {
                    "passwordCredentials": creds
                }
            }

        body = json.dumps(wrapped_creds)

        headers = {
            'Content-Length': len(body),
            'Host': self.keystone_host + ':' + str(self.keystone_port),
            'User-Agent': 'python-keystoneclient',
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
            }

        conn = httplib.HTTPConnection(self.keystone_host,self.keystone_port)
        conn.request("POST", "/v2.0/tokens", body, headers)
        res = conn.getresponse()

	logger = logging.getLogger('tukey-auth')
        logger.debug("status from contacting keystone: %s", res.status)

        if res.status != 200:
            return None

        access = res.read()
        conn.close()

        return json.loads(access)


class EucalyptusAuth(AuthSystem, FakeId):

    def authenticate(self, method, identifier, cloud_name):
        self.username, _ = auth_db.userInfo(method, identifier, cloud_name)

	if self.username == '':
	    return None

        fake_id = 'Eucalyptus-' + self.username
        self.tenant_name = fake_id
        self.token_id = fake_id
        self.tenant_id = fake_id
        self.user_id = fake_id
        self.url = '127.0.0.1'
        self.expires = self._expiration()

        return {"username": self.username}	

    def fake_token(self):
        return self._format_token(self.username, self.user_id,
            self.token_id, self.expires)

    def fake_tenant(self):
        return self._format_tenant(self.tenant_name, self.tenant_id)

    def fake_endpoint(self):
        return self._format_endpoint(self.token_id, self.tenant_id,
            self.user_id, self.tenant_name, self.username, self.expires,
            self.url)


