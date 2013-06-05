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


from jsonTransform.jsonTransform import Transformer as jsonTrans
from tukeyCli.tukeyCli import TukeyCli
from webob import exc, Request, Response

import httplib
import json
import logging
import logging.handlers
import memcache
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

GLOBAL = TukeyCli.GLOBAL_SECTION

class OpenStackApiProxy(object):
    '''Proxy between OpenStack clients, in particular Horizon
    and multiple clouds with multiple APIs'''

    def __init__(self, port, memcache_host, memcache_port, logger):
        self.port = port
        self.logger = logger

        # connect to memcached to get auth details that can't be sent w/token
        memcache_string = '%s:%s' % (memcache_host, memcache_port)
        self.mc = memcache.Client([memcache_string], debug=0)


    def __call__(self, environ, start_response):
        req = Request(environ)
        auth_token = req.headers['x-auth-token']

        try:
            values = self.mc.get(auth_token)
            if values == None:
                 values = {}
            resp = self.handle_openstack_api(req, auth_token, values)

        except memcache.Client.MemcachedKeyNoneError:  
            pass

        return resp(environ, start_response)


    def path(self, path, method, query, name):
        ''' Format the path the way we need it '''
        if method == "DELETE" and name in ['keypairs']:
            path_parts = path.split('/')
            path_parts[-1] = path_parts[-1].split('-',1)[-1]
            path = '/'.join(path_parts)

        if len(query) > 0:
            path = "%s?%s" % (path, query)

        return path


    def split_cloud_name(self, oldname):
        ''' Separate the cloud name from the real name
        we are curretnly using a scheme of cloudname-thingname'''
        split_id = oldname.split('-',1)
        return split_id[0], split_id[-1]


    def get_name(self, command, method):
        ''' Get the name of the command'''
        name, _ = self.__obj_name(command)
        if method == "POST" and name not in ['server']:
            name = name[:-1]
        return name


    def is_single(self, command, method):
        ''' Whether this command is return a plural '''
        if method == "POST":
            return True
        _, is_single = self.__obj_name(command)
        return is_single


    def handle_openstack_api(self, req, auth_token, values):
        ''' Handle against the OpenStack API be translating and aggregating
        the results of lots of messed up nonsense '''
        try:
            global_values = self.__path_to_params(req.path)
            global_values[GLOBAL].update(values)
            global_values[GLOBAL]['auth-token'] = auth_token
            global_values[GLOBAL]['method'] = req.method

            if 'x-auth-project-id' in req.headers:
                global_values[GLOBAL]['auth-project-id'] = req.headers[
                    'x-auth-project-id']

            global_values[GLOBAL].update(req.params)

            command = self.__path_to_command(req.path)
            self.logger.debug("The command is %s", command)

            name = self.get_name(command, req.method)

            if req.method == "POST":
                body_values = json.loads(req.body)
                if name in body_values:
                    body_values = json.loads(req.body)[name]
                    cloud, body_values['name'] = self.split_cloud_name(
                        body_values['name'])
                    req.body = json.dumps({name: body_values})
                    global_values[GLOBAL].update(body_values)

            elif req.method == "DELETE" and name in ['keypairs']:
                cloud, global_values[GLOBAL]['id'] = self.split_cloud_name(
                    global_values[GLOBAL]['id'])

            values.update(global_values)

            if "master_tenantId" in global_values[GLOBAL]:
                default_tenant = global_values[GLOBAL]["master_tenantId"]
            else:
                default_tenant = getattr(global_values[GLOBAL], "project_id",
                    None)

            cli = TukeyCli(jsonTrans())
            try:
                cli.load_config_dir(local_settings.CONF_DIR + cloud)
            except NameError:
                cli.load_config_dir(local_settings.CONF_DIR)

            return_headers = {"headers": []}

            result = cli.execute_commands(command, values, object_name=name,
                single=self.is_single(command, req.method),
                    proxy_method=self.openstack_proxy(req, self.path(req.path,
                            req.method, req.query_string, name),
                        return_headers, default_tenant))

            result = self.remove_error(name, result)
            result = self.apply_os_exceptions(command, result)

            logger.debug(result)

            resp = Response(result)
            resp.conditional_response = True

            result_object = json.loads(result)

            if 'message' in result_object[name] \
                and 'code' in result_object[name] \
                and result_object[name]['code'] in [409,413,402]:
                resp.status = result_object[name]['code']

            resp.headers.add('Content-Type','application/json')

            if req.method == "HEAD":
                for header, value in return_headers["headers"]:
                    resp.headers.add(header, value)

        except exc.HTTPException, e:
            resp = e

        return resp

    def apply_os_exceptions(self, command, result):
        if command == 'os-quota-sets':
            res_obj = json.loads(result)
            #res_obj['quota_set'] = {quota_set['cloud']: quota_set for
            #                    quota_set in res_obj['quota_set']}
            res_obj['quota_set'] = {quota_set['cloud']:
                {key: value for key, value in quota_set.items()
                        if key not in ["cloud_name", "cloud_id"]
                        } for quota_set in res_obj['quota_set']}

            result = json.dumps(res_obj)
        if command == 'os-simple-tenant-usage':
            res_obj = json.loads(result)
            if hasattr(res_obj['tenant_usage'], "iteritems"):
                return result
            else:
                res_obj['tenant_usage'] = {}
                return json.dumps(res_obj)

        return result


    def remove_error(self, name, result):
        if '"error":' in result:
            res_obj = json.loads(result)[name]
            new_res = [item for item in res_obj if not ('error'in item)]
            return json.dumps({name: new_res})
        return result


    def __parse_path(self, full_path):

        before_tenant = ['images', 'flavors', 'servers', 'shared-images',
            'extensions', 'tokens', 'tenants']

        path_segments = full_path[1:].split("/")

        index = 1

        if path_segments[index] not in before_tenant:
            index = 2

        return path_segments, index


    def __path_to_command(self, full_path):

        OpenStackApiProxy.after_command = ['detail','details','ip','metadata']

        path_segments, index = self.__parse_path(full_path)

        if len(path_segments) > index + 1 and \
           path_segments[index + 1] in OpenStackApiProxy.after_command:
            return "/".join(path_segments[index:index + 2])

        return path_segments[index]


    def __path_to_params(self, full_path):

        path_segments, index = self.__parse_path(full_path)

        global_values =  {GLOBAL:{}}

        if len(path_segments) > index + 1:
            global_values = {GLOBAL: {'id': path_segments[index + 1]}}

        return global_values


    def __obj_name(self, command):
        ''' There is probably some nice regex that can go here '''

        command_segments = command.split("/")

        if 'os-simple-' in command_segments[0]:
            return command_segments[0][10:].replace('-','_'), True
        if 'os-' in command_segments[0]:
            if command_segments[0] not in ['os-quota-sets']:
                return command_segments[0][3:].replace('-','_'), False
            else:
                return command_segments[0][3:-1].replace('-','_'), False

        if len(command_segments) > 1  and command_segments[1] in OpenStackApiProxy.after_command:
            return command_segments[0], False
        else:
            return command_segments[0][:-1], True


    def openstack_proxy(self, req, path, return_headers, default_tenant):
        return lambda host, token_id, tenant_id: str(self.proxy_request(host,
            token_id, tenant_id, req, path, return_headers, default_tenant))

    def proxy_request(self, host, token_id, tenant_id, req, path,
            return_headers, default_tenant):
        conn = httplib.HTTPConnection(host, self.port, False)
        # EnvironHeaders has no copy method
        headers = {key: value for key, value in req.headers.items()}
        if req.method != "POST" and 'Content-Length' in headers:
            del(headers['Content-Length'])
        # Capitlizatoin matters in dict
        headers["X-Auth-Token"] = token_id
        headers["X-Auth-Project-Id"] = tenant_id
        if default_tenant is not None:
            path = path.replace(default_tenant, tenant_id)
        conn.request(req.method, path, req.body, headers)
        response = conn.getresponse()
        if response.status == 404:
            res_list = '[]'
        else:
            res_body = response.read()
            try:
                res_obj = json.loads(str(res_body))
                stripped_res = res_obj[res_obj.keys()[0]]
                if type(stripped_res) is not list:
                    stripped_res = [stripped_res]
                res_list = json.dumps(stripped_res)
            except ValueError:
                res_list = res_body
        conn.close()
        return_headers["headers"] = response.getheaders()
        return res_list


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(
        usage='%prog --port=PORT'
        )
    parser.add_option(
        '-p', '--port', default='8774',
        dest='port', type='int',
        help='Port to serve on (default 8774)')

    parser.add_option(
        '-d', '--debug', default=False,
        action="store_true", dest='debug')

    log_file_name = local_settings.LOG_DIR + 'tukey-api.log'

    parser.add_option(
        '-l', '--log', default=log_file_name,
        dest='log', type='str',
        help='Log file to write to (default %s)' % log_file_name)

    options, args = parser.parse_args()

    #logging settings
    logger = logging.getLogger('tukey-api')

    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s %(filename)s:%(lineno)d')

    logFile = logging.handlers.WatchedFileHandler(options.log)
    logFile.setFormatter(formatter)

    logger.addHandler(logFile)

    app = OpenStackApiProxy(options.port, '127.0.0.1', 11211, logger)
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', options.port, app)
    print 'Serving on http://localhost:%s' % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print '^C'

else:
    log_file_name = local_settings.LOG_DIR + 'tukey-api.log'

    logger = logging.getLogger('tukey-api')

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s %(filename)s:%(lineno)d')

    logFile = logging.handlers.WatchedFileHandler('/var/log/tukey/tukey-api.log')
    #logFile = logging.handlers.WatchedFileHandler('/dev/null')
    logFile.setFormatter(formatter)

    logger.addHandler(logFile)
    logger.setLevel(logging.DEBUG)

    application = OpenStackApiProxy(8774, '127.0.0.1', 11211, logger)

