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

    def authenticate(self, method, identifier, tenant, cloud):
        '''Authenticate a user with a federated method and ifentifier
        like OpenID email attribute or Shibboleth EPPN


        :param method: The authentication method for example 'shibboleth'
                or 'openid'

        :param identifier: the user's email address obtained from OpenID
                metadata or user's Shibboleth EduPerson Principle Name
            see https://wiki.shibboleth.net.  And others...
        '''
        raise NotImplementedError


class FakeId(object):
    '''Mixin for non Keystone authentication methods to return the
    Keystone API for token, tenant and endpoint
    '''

    def __init__(self, api_url, member_role_id, token_lifetime,
        glance_port=9292, nova_port=8774, ec2_port=8773,
        identity_admin_port=35357, identity_port=5000):

        self.token_lifetime = token_lifetime
        self.url = api_url
        self.member_role_id = member_role_id

        self.glance_port = glance_port
        self.nova_port = nova_port
        self.ec2_port = ec2_port
        self.identity_admin_port = identity_admin_port
        self.identity_port = identity_port


    def _expiration(self):
        '''Returns times stamp of token_lifetime from now
        '''
        date_format = '%Y-%m-%dT%H:%M:%SZ'
        current = time.time()
        return str(datetime.datetime.fromtimestamp(current + self.token_lifetime).strftime(date_format))


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


    class Endpoint(object):

        def __init__(self, admin_url, public_url, endpoint_type, name):
            self.admin_url = admin_url
            self.public_url = public_url
            self.endpoint_type = endpoint_type
            self.name = name


    def _format_service_catalog(self, host, tenant_id):
        '''The Keystone API Service Catalog form.
        '''
        proxy_info = locals()

        endpoints = [
            FakeId.Endpoint(
                "".join(["http://%(host)s:", "%d" % self.glance_port , "/v1"]),
                "".join(["http://%(host)s:", "%d" % self.glance_port , "/v1"]),
                "image",
                "Image Service"),
            FakeId.Endpoint(
                "".join(["http://%(host)s:", "%d" % self.nova_port, "/v1.1/%(tenant_id)s"]),
                "".join(["http://%(host)s:", "%d" % self.nova_port, "/v1.1/%(tenant_id)s"]),
                "compute",
                "Compute Service"),
            FakeId.Endpoint(
                "".join(["http://%(host)s:", "%d" % self.ec2_port, "/services/Admin"]),
                "".join(["http://%(host)s:", "%d" % self.ec2_port, "/services/Cloud"]),
                "ec2",
                "EC2 Service"),
            FakeId.Endpoint(
                "".join(["http://%(host)s:", "%d" % self.identity_admin_port, "/v2.0"]),
                "".join(["http://%(host)s:", "%d" % self.identity_port, "/v2.0"]),
                "identity",
                "Identity Service")]

        return [
            {
                "endpoints": [
                    {
                        "adminURL": endpoint.admin_url % proxy_info,
                        "region": "RegionOne",
                        "publicURL": endpoint.public_url % proxy_info,
                        "internalURL": endpoint.public_url % proxy_info,
                    }
                ],
                "endpoints_links": [],
                "type": endpoint.endpoint_type,
                "name": endpoint.name
            } for endpoint in endpoints ]


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
            "serviceCatalog": self._format_service_catalog(url, tenant_id),
            "user": {
                "username": username,
                "roles_links": [],
                "id": user_id,
                "roles": [
                    {
                        #"id": "7cc444dd12f4413c90f1f19e3c109f99",
                        "id": self.member_role_id,
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

class OpenStackAuth(AuthSystem, FakeId):
    '''Contacts database with OpenID or Shibboleth to get
    OpenStack credentials.
    '''

    def set_keystone_info(self, keystone_host, keystone_port):
        ''' I really don't know what to do here: these are vital so I want to
        put them in the constructor however i dont rewrite a bunch and lose the
        niceity of the polymorphic constructor'''

        self.keystone_host = keystone_host
        self.keystone_port = keystone_port


    def authenticate(self, method, identifier, tenant, cloud_name):
        username, password = auth_db.userInfo(method, identifier, cloud_name)

        creds = {
            "username": username,
            "password": password
            }

        wrapped_creds = {
            "auth":
                {
                    "tenantName": tenant,
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

        conn = httplib.HTTPConnection(self.keystone_host, self.keystone_port)
        conn.request("POST", "/v2.0/tokens", body, headers)
        res = conn.getresponse()

        logger = logging.getLogger('tukey-auth')
        logger.debug("status from contacting keystone: %s", res.status)

        if res.status != 200:
            return None

        access = res.read()
        conn.close()

        access_obj = json.loads(access)

        if "access" in access_obj and "serviceCatalog" in access_obj[
            "access"] and "tenant" in access_obj["access"]["token"]:
            tenant_id = access_obj["access"]["token"]["tenant"]["id"]
            access_obj["access"][
                "serviceCatalog"] = self._format_service_catalog(
                    self.url, tenant_id)

        return access_obj


class EucalyptusAuth(AuthSystem, FakeId):

    def authenticate(self, method, identifier, tenant, cloud_name):
        self.username, _ = auth_db.userInfo(method, identifier, cloud_name)

        if self.username == '':
            return None

        fake_id = cloud_name + '-' + self.username
        self.tenant_name = fake_id
        self.token_id = fake_id
        self.tenant_id = fake_id
        self.user_id = fake_id
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


