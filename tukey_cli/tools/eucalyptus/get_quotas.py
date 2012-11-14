#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from ConfigParser import ConfigParser
import json
import sys


CONF_DIR    = '/etc/euca-quota/'
QUOTA_CONF  = 'quotas'

class QuotaProxy(BaseHTTPRequestHandler):


    def address_string(self):
        host, port = self.client_address[:2]
        return '%s (no getfqdn)' % host #used to call: socket.getfqdn(host)


    def do_GET(self):
        username = self.path[1:]

        if 'quota:' + username in quota.sections():
            section = 'quota:' + username
        else:
            section = 'quota'

        cpu = self.check_section('cpu', section)
        ram = self.check_section('ram', section)


        self.send_response(200)
        self.end_headers()

        self.wfile.write(json.dumps({
            "quota_set": {
                "metadata_items": 0,
                "injected_file_content_bytes": 0,
                "injected_files": 0,
                "gigabytes": 0,
                "ram": ram,
                "floating_ips": 0,
                "security_group_rules": 0,
                "instances": cpu,
                "volumes": 0,
                "cores": cpu,
                "security_groups": 0
            }}))


    def check_section(self, res, section):
	rack_limit = {'cpu':288, 'ram': 1032192}	

        if res in quota.options(section):
            limit = int(quota.get(section, res))
        else:
            limit = rack_limit[res]
	return limit


def run(server_class=HTTPServer,
        handler_class=QuotaProxy):
    server_address = (sys.argv[1], int(sys.argv[2]))
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


quota = ConfigParser()
quota.read(CONF_DIR + QUOTA_CONF)

if __name__ == "__main__":

    run()

