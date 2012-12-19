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


from tukeyCli.tukeyCli import TukeyCli
from jsonTransform.jsonTransform import Transformer as jsonTrans
from webob import exc
from webob import Request, Response

import httplib
import json
import logging
import logging.handlers
import memcache
import sys

sys.path.append('../local')
import local_settings


class OpenStackApiProxy(object):
    '''Proxy between OpenStack clients, in particular Horizon
    and multiple clouds with multiple APIs''' 


    def __init__(self, port, memcache_host, memcache_port, logger):

        self.port = port

        self.logger = logger
        
        # connect to memcached to get authentication 
        # details that cannot be sent through the lowly
        # auth token
        memcache_string = '%s:%s' % (memcache_host, memcache_port)
        self.mc = memcache.Client([memcache_string], debug=0)


    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            
            #TODO: this definitely shouldnt be relative
            conf_dir = 'etc/enabled/'

            # Load default JSON transformer
            cli = TukeyCli(jsonTrans())

            auth_token = req.headers['x-auth-token']

            values = self.mc.get(auth_token)

            self.logger.debug(values)
            
            command = self.__path_to_command(req.path)
            global_values = self.__path_to_params(req.path)

            global_values[TukeyCli.GLOBAL_SECTION].update(values)

            global_values[TukeyCli.GLOBAL_SECTION]['method'] = req.method
            global_values[TukeyCli.GLOBAL_SECTION]['auth-token'] = auth_token
            if 'x-auth-project-id' in req.headers:
                global_values[TukeyCli.GLOBAL_SECTION]['auth-project-id'] = req.headers['x-auth-project-id']
        

            global_values[TukeyCli.GLOBAL_SECTION].update(req.params)

            name, is_single = self.__obj_name(command)

            path = req.path

            post_exception_names = ['server']
            multiplexed_names = ['keypairs']

            if req.method == "POST":
                is_single = True
                if not name in post_exception_names:
                    name = name[:-1]
                
                body_values = json.loads(req.body)[name]
                split_id = body_values['name'].split('-',1)
                cloud = split_id[0]
                new_object_name = split_id[-1]
                body_values['name'] = new_object_name

                self.logger.debug(body_values)
                
                req.body = json.dumps({name: body_values})
                
                global_values[TukeyCli.GLOBAL_SECTION].update(body_values)
                
                cli.load_config_dir(conf_dir + cloud)

            elif req.method == "DELETE" and name in multiplexed_names:
                id = global_values[TukeyCli.GLOBAL_SECTION]['id']
                split_id = id.split('-',1)
                cloud = split_id[0]
                new_id = split_id[-1]
                global_values[TukeyCli.GLOBAL_SECTION]['id'] = new_id
                cli.load_config_dir(conf_dir + cloud)
                path_parts = path.split('/')
                path_parts[-1] = path_parts[-1].split('-',1)[-1]
                path = '/'.join(path_parts)
                logger.debug("earlier path %s", path)

            else:
                cli.load_config_dir(conf_dir)

            values.update(global_values)

            self.logger.debug(values)

            if len(req.query_string) > 0:
                path = "%s?%s" % (path, req.query_string)

            result = cli.execute_commands(command, values, object_name=name,
                single=is_single, 
                proxy_method=self.openstack_proxy(req, path))

            self.logger.debug(result)

            result = self.remove_error(name, result)
            result = self.apply_os_exceptions(command, result)
            
            #print result
            resp = Response(result)

            result_object = json.loads(result)
            
            failure_codes = [409,413,402]

            if 'message' in result_object[name] \
                and 'code' in result_object[name] \
                and result_object[name]['code'] in failure_codes:
                resp.status = result_object[name]['code']

            resp.conditional_response = True

            resp.headers.add('Content-Type','application/json')

        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)


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

        global_values =  {TukeyCli.GLOBAL_SECTION:{}}

        if len(path_segments) > index + 1:
            global_values = {TukeyCli.GLOBAL_SECTION: {'id': path_segments[index + 1]}}

        return global_values


    def __obj_name(self, command):

        os_exceptions = ['os-quota-sets']
        command_segments = command.split("/")

        if 'os-simple-' in command_segments[0]:
            return command_segments[0][10:].replace('-','_'), True
        if 'os-' in command_segments[0]:
            if command_segments[0] not in os_exceptions:
                return command_segments[0][3:].replace('-','_'), False
            else:
                return command_segments[0][3:-1].replace('-','_'), False
        

        if len(command_segments) > 1  and command_segments[1] in OpenStackApiProxy.after_command:
            return command_segments[0], False
        else:
            return command_segments[0][:-1], True

    
    def openstack_proxy(self, req, path):
        return lambda host: str(self.proxy_request(host, req, path))

    def proxy_request(self, host, req, path):
        logger.debug(req.method)
        logger.debug(path)
        conn = httplib.HTTPConnection(host, self.port, False)
        if req.method != "POST":
            del(req.headers['Content-Length'])
        conn.request(req.method, path, req.body, req.headers)
        response = conn.getresponse()
        if response.status == 404:
            res_list = '[]'
        else:
            res_body = response.read()
            self.logger.debug(res_body)
            res_obj = json.loads(str(res_body))
            stripped_res = res_obj[res_obj.keys()[0]]
            if type(stripped_res) is not list:
                stripped_res = [stripped_res]
            res_list = json.dumps(stripped_res)
        conn.close()
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

#    parser.add_option(
#        '-o', '--openstack_host', default='10.103.114.3',
#        dest='openstack_host', type='str',
#        help='OpenStack host (default 10.103.114.3)')

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
