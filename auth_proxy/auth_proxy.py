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


from auth_system import OpenStackAuth, EucalyptusAuth
from webob import exc
from webob import Request, Response
from ConfigParser import ConfigParser
from glob import glob
from os import path, sep

import httplib
import json
import memcache
import logging
import logging.handlers

import sys
sys.path.append('../local')
import local_settings



class AuthProxy(object):
    '''Proxy to sit between Horizon and Keystone.
    
    This proxy provides two main features:
    
    1. Creates an association between keystone auth-tokens and auth
    details of other cloud authentication systems as well as creating
    fake keystone auth information when the current user has only 
    authenticated against other cloud systems.
    
    2. Authenticates users to Keystone and other cloud auth systems
    using identifiers  provided by systems such as OpenID and Shibboleth
    
    Assumes that each Keystone token request will be 
    {"auth":{"passwordCredentials":{"username":identifier,"password":method}}}
    
    for example:
    {"auth":{"passwordCredentials":
        {"username":test@yahoo.com,"password":openid}
    }}
    
    Uses memcached to store the associations which can then be used by
    other middle ware between Horizon and cloud services.
    '''

    TOKEN_EXPIRATION = 24*60*60

    def __init__(self, keystone_host, keystone_port, memcache_host, 
        memcache_port, conf_dir, logger):
        '''
        Define any auth systems here in self.auth_systems with the config
        site name to match that in the tukey_cli config
        Eventually fetch these from a config file.
        '''

        self.logger = logger
        
        self.keystone_host = keystone_host
        self.keystone_port = keystone_port

        self.auth_systems = dict()

        for conf in glob(path.join(conf_dir, '*')):

            config = ConfigParser()
            config.read(conf)

            if config.has_section('auth'):

                driver_object = None
                driver = config.get('auth', 'driver')

                if driver == 'OpenStackAuth':

                    host = config.get('auth', 'host')
                    port = config.get('auth', 'port')

                    driver_object = OpenStackAuth(local_settings.API_HOST,
                        local_settings.MEMBER_ROLE_ID, 
                        AuthProxy.TOKEN_EXPIRATION, host, port)

                if driver == 'EucalyptusAuth':
                    driver_object = EucalyptusAuth(local_settings.API_HOST,
                        local_settings.MEMBER_ROLE_ID,
                        AuthProxy.TOKEN_EXPIRATION)

                self.auth_systems[conf.split(sep)[-1]] = driver_object

        memcache_string = '%s:%s' % (memcache_host, memcache_port)
                
        self.mc = memcache.Client([memcache_string], debug=0)


    def __is_openstack(self, user_info):

        for key in user_info.keys():
            if key in self.auth_systems.keys() and isinstance(
                self.auth_systems[key], OpenStackAuth):
                return True

        return False


    def __tenant_request(self, req):
        '''
        :param req:    webob Request
        
        Use the auth token from Horizon to to either forward request to 
        Keystone if the user has an authorized OpenStack account otherwise
        return the fake tenant data
        '''

        token = None

        if 'x-auth-token' in req.headers:
            token = req.headers['x-auth-token']
        else:
            method = req.headers["x-auth-key"]
            identifier = req.headers["x-auth-user"]
            _, token = self.__authenticate(method, identifier)

        
        user_info = self.mc.get(str(token))

        if self.__is_openstack(user_info):
            del(req.headers['Content-Length'])
            resp = self.__forward("GET", req.path, "", req.headers)
        else:
            resp = self.__json_response(user_info['fake_tenant'])
        
        return resp
        
    
    def __token_request(self, req):
        '''
        :param req:    webob Request 
        
        Assumes Horizon is contacting Keystone with passwordCredentials auth
        message.  However the "username" attribute will be equal to the identifier
        string and the "password" attribute will be equal to  auth method.
        '''
        req_body = json.loads(req.body)
        auth_method = req_body["auth"]["passwordCredentials"]["password"]
        identifier = req_body["auth"]["passwordCredentials"]["username"]
        tenant = None

        if "tenantName" in req_body["auth"]:
            tenant = req_body["auth"]["tenantName"]


        self.logger.debug("auth_method %s", auth_method)
        self.logger.debug("identifier %s", identifier)

        user_info, _ = self.__authenticate(auth_method, identifier, tenant)

        resp = self.__json_response(user_info)
    
        if 'error' in user_info:
            resp.status = 401
        
        return resp
        
        
    def __endpoint_request(self, req):
        '''
        :param req:    webob Request
        
        Returns the massive endpoint info JSON.
        '''
        #if 'x-auth-token' not in req.headers:

        #    auth_method = req.headers["x-auth-key"]
        #    identifier = req_body["auth"]["passwordCredentials"]["username"]
        #    self.__authenticate
            
        user_info = self.mc.get(req.headers['x-auth-token'])

        if self.__is_openstack(user_info):
            resp = self.__forward("POST", req.path, req.body, req.headers)
        else:
            resp = self.__json_response(user_info['fake_endpoint'])
        
        return resp
        
        
    def __authenticate(self, auth_method, identifier, tenant):
        '''
        :param auth_method: the authentication method "openid", "shibboleth"
        :param identifier: id string could be shib EPPN like 
            "mgreenway@uchicago.edu"
            
        Iterates through the auth systems stored in auth_systems dictionary
        authenticating the id string against the method for that 
        system.  If the user was not authenticated on an OpenStack auth
        then we store "fake" info from another cloud system to use in 
        tenant and endpoint requests.
        '''
        user_info = dict()
        has_openstack = False

        #token = "guest"
        id_info = {"error": {
                "message": "Invalid user / password",
                "code": 401, "title": "Not Authorized"}}

        for name, auth in self.auth_systems.items():

            auth_creds = auth.authenticate(auth_method, identifier, tenant, name)

            if auth_creds is not None:
                self.logger.debug( "Auth creds: %s", auth_creds)
                user_info[name] = auth_creds

                if isinstance(auth, OpenStackAuth) and not has_openstack:
                    self.logger.debug("false positive")
                    has_openstack = True
                    token = auth_creds["access"]["token"]["id"]
                    id_info = auth_creds

        if not has_openstack and len(user_info.keys()) > 0:
            auth = self.auth_systems[user_info.keys()[0]]

            id_info = auth.fake_token()
            token = id_info['access']['token']['id']
            user_info['fake_tenant'] = auth.fake_tenant()
            user_info['fake_endpoint'] = auth.fake_endpoint()

        if "error" in id_info:
            self.logger.info("login for %s FAIL", identifier)
            return id_info

        self.logger.debug(user_info)

        self.logger.info("login for %s SUCCESS", identifier)

        self.mc.set(str(token), user_info, AuthProxy.TOKEN_EXPIRATION)

        return id_info, token
        
        
    # HTTP, Proxy and JSON helper methods
    
    def __call__(self, environ, start_response):
        '''Webob boiler plate calls action_view_GET and POST.
        '''
        req = Request(environ)
        action = req.params.get('action', 'view')
        try:
            try:
                meth = getattr(self, 'action_%s_%s' % (action, req.method))
            except AttributeError:
                raise exc.HTTPBadRequest('No such action %r' % action)
            resp = meth(req)
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

        
    def __forward(self, method, path, body, headers):
        '''Send an HTTP request and return its webob Response.
        
        :param method: the http request method "GET", "POST"
        :param path: the path of the request
        :param body: body data string
        :param headers: dictionary like object of request headers
        '''
        conn = httplib.HTTPConnection(self.keystone_host,self.keystone_port, False)
        conn.request(method, path, body, headers)
        res = conn.getresponse().read()
        conn.close()
        res_object = json.loads(res)
        if 'access' in res_object and 'token' in res_object['access']:
            old = self.mc.get(headers['x-auth-token'])
            self.mc.set(str(res_object['access']['token']['id']), old,
                AuthProxy.TOKEN_EXPIRATION)
        
        res = res.replace(self.keystone_host, '127.0.0.1')
        self.logger.debug( "Forwarded request")
        self.logger.debug( res)
        resp = Response(res)
        resp.conditional_response = True
        return resp

        
    def __json_response(self, serial_obj):
        '''Serialize an object into JSON then return as webob Response
        
        :param serial_obj: object acceptable by json.dumps()
        '''
        resp = Response(json.dumps(serial_obj))
        self.logger.debug( json.dumps(serial_obj))
        resp.conditional_response = True
        return resp

        
    def action_view_GET(self, req):
        '''All GETs are request for tenant info
        '''
        return self.__tenant_request(req)

        
    def action_view_POST(self, req):
        '''POST requests will be either endpoint or token requests.
        '''
        if 'x-auth-token' in req.headers:
            resp = self.__endpoint_request(req)
        else:
            resp = self.__token_request(req)
        return resp        
    
        
if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(
        usage='%prog --port=PORT --keystone_host=HOST'
        )
    parser.add_option(
        '-p', '--port', default='5000',
        dest='port', type='int',
        help='Port to serve on (default 5000)')

    parser.add_option(
        '-k', '--keystone_host', default=local_settings.KEYSTONE_HOST,
        dest='keystone_host', type='str',
        help='Keystone host (default %s)' % local_settings.KEYSTONE_HOST)

    parser.add_option(
        '-c', '--config_dir', default='../tukey_cli/etc/enabled',
        dest='config_dir', type='str',
        help='Directory containing Tukey site configs (default ../tukey_cli/etc/enabled)')

    parser.add_option(
        '-d', '--debug', default=False,
        action="store_true", dest='debug')

    options, args = parser.parse_args()

    #logging settings 
    logger = logging.getLogger('tukey-auth')

    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s %(filename)s:%(lineno)d')

    log_file_name = local_settings.LOG_DIR + 'tukey-auth.log'

    logFile = logging.handlers.WatchedFileHandler(log_file_name)
    logFile.setFormatter(formatter)

    logger.addHandler(logFile)

    app = AuthProxy(options.keystone_host, options.port, '127.0.0.1',
        11211, options.config_dir, logger)

    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', options.port, app)
    print 'Serving on http://localhost:%s' % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print '^C'
