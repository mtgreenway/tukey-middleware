#  Copyright 2013 Open Cloud Consortium
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

''' A temporary solution until I split the tukey_cli/etc/enabled files clearly
into drivers and configuration '''

import os
import settings
import sys

from check_config import check_config


def write_file(file_name, text):
    ''' Write text to file filename '''
    config_file = open(file_name, 'w')
    config_file.write(text)
    config_file.close()
#    print "writing to file %s" % file_name
#    print text


class ConfigBuilder(object):
    ''' Base configuration builder to handle things such as what do we do if we
    should create a login server configuration file and. Thats pretty much it
    '''

    def build(self, cloud, middleware_dir, config_dir, proxy_host='127.0.0.1',
        nova_proxy_port=8774):
        ''' Generic build sets vars and controls flow '''

        self.cloud = cloud
        self.middleware_dir = middleware_dir
        self.config_dir = config_dir
        self.proxy_host = proxy_host
        self.nova_proxy_port = nova_proxy_port

        self._write_configuration()

        if self.cloud["handle_login_keys"]:
            self._write_login_config()

    def _write_configuration(self):
        ''' Must be called after build.  Calls the method that must be
        implemented configuration'''

        file_name = os.path.join(self.middleware_dir, self.config_dir,
            self.cloud["cloud_id"])

        self._write_file(file_name, self.configuration())

    def _usage(self):
        ''' Return the usgage string tailored to this cloud. Should be
        what would appear after 'os-simple-tenant-usage: ' '''

        if self.cloud["usage_cloud"]:
            return "".join([self.middleware_dir, "/tools/with_venv.sh python ",
                self.middleware_dir,
                "/tukey_cli/tools/get_usage.py ${start} ${end} ${",
                self.cloud["cloud_id"], self.username(), "}"])
        else:
            return "echo [{}]"

    def _write_login_config(self):
        ''' Write the config file for the login node '''
        file_name = os.path.join(self.middleware_dir, self.config_dir,
            "".join(["login", self.cloud["cloud_id"]]))

        login_config = "".join(['''[tag]
cloud: %(cloud_name)s Login Node
cloud_name: %(cloud_name)s Login Node
cloud_id: login%(cloud_id)s

[enabled]
command: if [ '${%(cloud_id)s''', self.username(), "}' = '$'{%(cloud_id)s",
            self.username(), '''} ]; then
        false
    else
        true
    fi

[commands]
basedir=%(middleware_dir)s
gpg_home=%(middleware_dir)s/../.gnupg
fingerprint='%(gpg_fingerprint)s'
passphrase='%(gpg_passphrase)s'
host=%(login_host)s:%(login_port)s
resource=%(cloud_id)s
username=${%(cloud_id)s''', self.username(), '''}
keyname=%(cloud_id)s.pub''']) % {"cloud_id": self.cloud["cloud_id"],
            "cloud_name": self.cloud["cloud_name"],
            "middleware_dir": self.middleware_dir,
            "gpg_fingerprint": self.cloud["gpg_fingerprint"],
            "gpg_passphrase": self.cloud["gpg_passphrase"],
            "login_host": self.cloud["login_host"],
            "login_port": self.cloud["login_port"]}

        login_config = "\n".join([login_config,
            '''command_base=%(basedir)s/tukey_cli/
venv=%(basedir)s/tools/with_venv.sh

keyfile=%(command_base)s/etc/keys/%(keyname)s

script_file=%(basedir)s/auth_proxy/ssh_gen.py
script=%(venv)s python %(script_file)s %(fingerprint)s %(gpg_home)s %(passphrase)s %(host)s %(keyfile)s

os-keypairs: if [ '${method}' = 'POST' ]; then
                if [ '${public_key}'  = '$'{public_key} ]; then
                    %(script)s create %(username)s %(resource)s '${name}' ${password}
                else
                    %(script)s import %(username)s %(resource)s '${name}' '${public_key}'
                fi
        elif [ '${id}' = '$'{id} ];then
            %(script)s list %(username)s %(resource)s
        elif [ '${method}' = 'DELETE' ]; then
            %(script)s delete %(username)s %(resource)s ${id}
        else
            %(script)s get %(username)s %(resource)s '${name}'
        fi
'''])

        self._write_file(file_name, login_config)

    def _write_file(self, file_name, text):
        ''' wrapper for writing to a file so we can test with print'''
        write_file(file_name, text)

    def get_all_statement(self, is_first=False, is_last=False):
        ''' create the portion of the "all" config file where we see if this
        cloud is enabled do to the user tokens appearing. sorry'''

        return "".join(['''if [ '${%(cloud_id)s%(username_pattern)s}' = '$'{%(cloud_id)s%(username_pattern)s} ]; then
        %(echo_command)s ''', "'[" if is_first else "'", ']' if is_last else '', ''''
    else
        %(echo_command)s ''', "'[" if is_first else "',", ' "%(cloud_id)s"', ',"login%(cloud_id)s"' if self.cloud["handle_login_keys"] else '', ']' if is_last else '', ''''
    fi ''']) % {"cloud_id": self.cloud["cloud_id"], "echo_command": "echo -n", "username_pattern": self.username()}


class OpenStackConfigBuilder(ConfigBuilder):
    ''' Configuration builder for openstack clouds '''

    def username(self):
        ''' This clouds username pattern using a JPathlike'''
        return '/access/user/username'

    def configuration(self):
        ''' build the configuration specific to this cloud '''

        return "".join(['''[proxy]
host: %(nova_host)s
port: %(nova_port)s

[auth]
driver: OpenStackAuth
host:   %(keystone_host)s
port:   %(keystone_port)s

[tag]
cloud: %(cloud_name)s
cloud_name: %(cloud_name)s
cloud_id: %(cloud_id)s

[enabled]
command: if [ '${%(cloud_id)s/access/user/username}' = '$'{%(cloud_id)s/access/user/username} ]; then
        false
    else
        true
    fi

[commands]

os-simple-tenant-usage: if [ '${detailed}' = '1' ]; then
        echo "#proxy"
    else
        ''', self._usage(), '''
    fi''']) % self.cloud


class EucalyptusConfigBuilder(ConfigBuilder):
    ''' Configuration builder for eucalyptus clouds.'''

    def username(self):
        ''' JPath like username pattern'''
        return '/username'

    def configuration(self):
        ''' build the configuration specific to this cloud '''

        config = '''[enabled]
command: if [ '${%(cloud_id)s/username}' = '$'{%(cloud_id)s/username} ]; then
        false
    else
        true
    fi

[tag]
cloud:  %(cloud_name)s
cloud_name: %(cloud_name)s
cloud_id: %(cloud_id)s

[commands]
basedir=%(middleware_dir)s''' % {"middleware_dir": self.middleware_dir,
            "cloud_id": self.cloud["cloud_id"],
            "cloud_name": self.cloud["cloud_name"]}

        config = "".join([config, '''
command_base=%(basedir)s/tukey_cli/
venv=%(basedir)s/tools/with_venv.sh
compute=%(venv)s python %(command_base)stools/eucalyptus/compute.py

# This should contain the Eucarc files for the
# Users.
creddir=/var/lib/cloudgui/users/
cred_file=%(creddir)s${username}/.euca/eucarc
creds=--credentials %(cred_file)s

# The commands
servers/detail: %(compute)s %(creds)s --list instances

servers: if [ '${method}' = 'DELETE' ]; then
        %(compute)s %(creds)s --action kill --id ${id}
    elif [ '${method}' = 'POST' ]; then
        if [ '${user_data}'  = '$'{user_data} ]; then
            %(compute)s %(creds)s --action launch --id ${imageRef} --size ${flavorRef} --number ${min_count} --keyname ${key_name}
        else
            %(compute)s %(creds)s --action launch --id ${imageRef} --size ${flavorRef} --number ${min_count} --keyname ${key_name} --userdata ${user_data}
        fi
    else
        %(compute)s %(creds)s --list instances --id ${id}
    fi

flavors/detail: %(venv)s python %(command_base)stools/eucalyptus/flavors.py

flavors: %(venv)s python %(command_base)stools/eucalyptus/flavors.py ${id}

images/detail: if [ "${property-image_type}" = 'snapshot' ];then
        #echo '[{"id":""}]'
        echo ''
        else
        if [ '${marker}' = '$'{marker} ]; then
            %(compute)s %(creds)s --list images --limit ${limit}
        else
            %(compute)s %(creds)s --list images --limit ${limit} --marker ${marker}
        fi
        fi

images:     %(compute)s %(creds)s --list images --id ${id}

os-keypairs: if [ '${method}' = 'POST' ]; then
        if [ '${public_key}'  = '$'{public_key} ]; then
                %(compute)s %(creds)s --action create_keypair --keyname ${name}
        else
            KEY=$(tempfile);echo "${public_key}" > $KEY
            %(compute)s %(creds)s --action import_keypair --keyname ${name} --keyfile $KEY
            rm $KEY
        fi
    elif [ '${id}' = '$'{id} ];then
        %(compute)s %(creds)s --list keys
    elif [ '${method}' = 'DELETE' ]; then
        euca-delete-keypair --config %(cred_file)s  ${id}
    else
        %(compute)s %(creds)s --list keys --id ${id}
    fi

os-quota-sets: %(venv)s python %(command_base)stools/eucalyptus/get_quota.py 10.103.112.3 9402 ${username}

os-simple-tenant-usage: if [ '${detailed}' = '1' ]; then
       echo [{}]
    else
        %(venv)s python %(command_base)stools/get_usage.py ${start} ${end} ${username} ${access/user/username}
    fi

[transformations:listSizes]
id: name

[transformations:servers/detail]
OS-EXT-STS power_state=1
tenant_id: ${username}
username_id: ${username}
name: $(id)
status: $(extra/status)
key_name: $(extra/keyname)
updated: $(launchdatetime)
created: $(launchdatetime)
hostId: ''
progress: 100
accessIPv4:
accessIPv6:
image: {
    "id" "$(extra/imageId)",
    "links" [
    {
        "rel" "self",
        "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/v1.1/${username}/images/$(extra/imageId)"
    },
    {
        "rel" "bookmark",
        "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/${username}/images/$(extra/imageId)"
    }
    ]
    }
flavor: {
    "id" "$(extra/instancetype)",
    "links" [
    {
        "rel" "self",
        "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/v1.1/${username}/flavors/$(extra/instancetype)"
    },
    {
        "rel" "bookmark",
        "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/${username}/flavors/$(extra/instancetype)"
    }
    ]
    }
addresses: {
    "private" [
    {
        "version" 4,
        "addr" "$(extra/private_dns)"
    }
    ]
    }
metadata: {}
links: [
    {
    "rel" "self",
    "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/v1.1/${username}/servers/$(id)"
    },
    {
    "rel" "bookmark",
    "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/${username}/servers/$(id)"
    }
    ]

[transformations:servers]
OS-EXT-STS power_state=1
tenant_id: ${username}
username_id: ${username}
name: $(id)
status: $(extra/status)
key_name: $(extra/keyname)
updated: $(launchdatetime)
created: $(launchdatetime)
hostId: ''
progress: 100
accessIPv4:
accessIPv6:

image: {
    "id" "$(extra/imageId)",
    "links" [
        {
            "rel" "self",
            "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/v1.1/${username}/images/$(extra/imageId)"
        },
        {
            "rel" "bookmark",
            "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/${username}/images/$(extra/imageId)"
        }
    ]
    }

flavor: {
    "id" "$(extra/instancetype)",
    "links" [
        {
            "rel" "self",
            "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/v1.1/${username}/flavors/$(extra/instancetype)"
        },
        {
            "rel" "bookmark",
            "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/${username}/flavors/$(extra/instancetype)"
        }
    ]
    }

addresses: {
    "private" [
        {
            "version" 4,
            "addr" "$(extra/private_dns)"
        }
    ]
    }
metadata: {}

links: [
    {
        "rel" "self",
        "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/v1.1/${username}/servers/$(id)"
    },
    {
        "rel" "bookmark",
        "href" "http://''', self.proxy_host, ''':''', str(self.nova_proxy_port), '''/${username}/servers/$(id)"
    }
    ]

[transformations:images/detail]
properties: { "image_type" "$(extra/imagetype)"}
created:
updated:
container_format: $(extra/container_format)
is_public: extra/ispublic
owner:  extra/ownerid
image_type: $(extra/imagetype)
tenant_id: ${username}
user_id: ${username}
status: $(extra/state)
metadata: {}
links:  [
                {
                    "rel" "self",
                    "href" "http://''', self.proxy_host, '''/v1.1/${username}/images/${id}"                },
                {
                    "rel" "bookmark",
                    "href" "http://''', self.proxy_host, '''/${username}/images/${id}"}
            ]

[transformations:os-keypairs]
keypair:
     {"private_key" "$(keyMaterial)",
     "public_key" "",
     "fingerprint" "$(keyFingerprint)",
     "name" "$(keyName)"}

[errors]
createKeypair:  result
launchVm:   result

[auth]
driver: EucalyptusAuth
''']) 
        return config


def main():
    #for cloud in settings.clouds
    if not check_config(settings):
        print "Invalid configuration file"
        exit(1)
    print "Config file correct!"

    if len(sys.argv) != 2:
        print "Requires middleware_dir argument"
        exit(1)

    middleware_dir = sys.argv[1]
    config_dir = "tukey_cli/etc/enabled"

    os.mkdir(os.path.join(middleware_dir, config_dir))

    host_and_ports = getattr(settings, "host_and_ports",
        {"host": "127.0.0.1", "nova_port": 8874})

    # lets build some config files !
    count = 1
    all_statement = ''
    for cloud in settings.clouds:

        # factory
        if cloud["cloud_type"].lower() == "eucalyptus":
            config_builder = EucalyptusConfigBuilder()
        if cloud["cloud_type"].lower() == "openstack":
            config_builder = OpenStackConfigBuilder()

        config_builder.build(cloud, middleware_dir, config_dir,
            proxy_host=host_and_ports["host"],
            nova_proxy_port=host_and_ports["nova_port"])

        # build the all file
        all_statement += config_builder.get_all_statement(count == 1,
            count == len(settings.clouds)) + '; \\'

        count += 1

    all_statement = "".join(['''[commands]
middledir=''', middleware_dir, '''
venv=%(middledir)s/tools/with_venv.sh
script_file=%(middledir)s/auth_proxy/multiple_keys.py
script=%(venv)s python %(script_file)s ${auth-project-id} ${auth-token} '${name}' $( ''', all_statement[:-3], ''')

os-keypairs: if [ '${public_key}'  = '$'{public_key} ]; then
                    %(script)s
                else
                    %(script)s '${public_key}'
                fi

[tag]
cloud: All Resources

cloud_name: All Resources

cloud_id: all

[enabled]
command: true'''])

    write_file(os.path.join(middleware_dir, config_dir, 'all'), all_statement)

if __name__ == "__main__":
    main()
