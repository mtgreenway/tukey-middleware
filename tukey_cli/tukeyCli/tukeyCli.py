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
Created on Apr 11, 2012

TODO:
Need to decouple from JSON and the jsonTransform:
implement all functionality with json through the Transformer
class and make that an implementation of an interface.

The data format can then be specified in a config file so
that we can combine xml, json or other formats.
so that we could use JSON, XML or some other data scheme.

@author: Matt
'''
from os import path
from glob import glob
from subprocess import call, Popen, PIPE
from ConfigParser import ConfigParser

import os 
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings


class TukeyCli(object):
    '''
    classdocs
    '''

    GLOBAL_SECTION = '/globals'

    __COMMAND_SECTION   = 'commands'
    __ENABLED_SECTION   = 'enabled'
    __PROXY_SECTION     = 'proxy'
    __CHECK_COMMAND     = 'command'
    __VAR_BEG           = '${'
    __VAR_END           = '}'
    __STRIP_SECTION     = 'strip'
    __TRANS_SECTION     = 'transformations:'
    __TAG_SECTION       = 'tag'
    __ERROR_SECTION     = 'errors'
    __DEFAULT_ERROR     = 'error'

    # since config file comments start  with a hash we cant have a
    # legitimate command starting with
    #
    __PROXY_COMMAND     = '#proxy'

    def __init__(self, trans):
        '''
        Constructor
        '''

        #TODO: actually load a Transformer for each site based on
        # config value so that we can have one tool that returns
        # xml and one tool that returns json and then have them both
        # return the same thing which can be specified as an options
        # to execute_commands
        self.trans = trans

    def check_config(self, conf_file):
        '''
            check that the config file exists and if it does
            then check that
        '''

        config = ConfigParser()


        if conf_file not in config.read(conf_file):
            return False


        section = TukeyCli.__ENABLED_SECTION
        option  = TukeyCli.__CHECK_COMMAND

        if section not in config.sections():
            return False

        if option not in config.options(section):
            return False

        return True

    def load_config_file(self, conf):
        '''
            checks if the file is a legit config file
            and then loads it if so
        '''
        if not self.check_config(conf):
            return False

        site = path.split(conf)[1]
        self.configs[site] = ConfigParser()
        self.configs[site].read(conf)

        return True

    def load_config_dir(self, conf_dir):
        '''
            check that all files in the directory are valid
            config files then load them if they are and
            return True else return False
            Clears all configs and sites
        '''

        # clears the configs and sites
        self.configs = dict()

        if path.isfile(conf_dir):
            return self.load_config_file(conf_dir)

        for conf in glob(path.join(conf_dir, '*')):
            if not self.load_config_file(conf):
                return False

        return True

    def get_sites(self):
        '''
            return the names of the "sites" which are loaded
            config files corresponding to tools and what to
            do with them
        '''
        return self.configs.keys()

    def check_enabled(self, site, values):
        '''
            given a string site check if that site is a valid
            site and then run the command in enabled
        '''

        if site not in self.get_sites():
            return False

        config = self.configs[site]

        command = config.get(TukeyCli.__ENABLED_SECTION, TukeyCli.__CHECK_COMMAND)

        command = self.replace_var(command, values)

        return call(command, shell=True) == 0


    def _replace_var(self, token, string, values):
        '''
            to recursively traverse dictionaries and replace the
            sweet value within
        '''
        beg = TukeyCli.__VAR_BEG
        end = TukeyCli.__VAR_END

        for (key, value) in values:
            if hasattr(value, 'items'):
                string = self._replace_var(token + str(key) + '/' , string, value.items())

            new_token = beg + token + str(key) + end

            string = string.replace(new_token, str(value))

        return string


    def replace_var(self, string, values):
        '''
            find for each values.keys() surrounded by begin and end
            symbols then replace it with values[name]
        '''
        beg = TukeyCli.__VAR_BEG
        end = TukeyCli.__VAR_END

        for (key, value) in values.items():
            if hasattr(value, 'items'):
                string = self._replace_var(str(key) + '/', string, value.items())

            token = beg + str(key) + end
            string = string.replace(token, str(value))

        return string

    def generate_commands(self, command, values):
        '''
            for each site see if the site is enabled
            and then return the prepared command
        '''
        commands = dict()
        section  = TukeyCli.__COMMAND_SECTION

        command = command.lower()

        for (site, config) in self.configs.items():
            site_values = self.__site_values(site, values)

            if self.check_enabled(site, site_values):
                if section in config.sections() and command in config.options(section):
                    command_str = config.get(section, command)
                    commands[site] = self.replace_var(command_str, site_values)
                elif TukeyCli.__PROXY_SECTION in config.sections():
                    commands[site] = TukeyCli.__PROXY_COMMAND

        return commands


    def strip(self, result, site, command):
        '''
            given a json string (result) look at the config for site
            and if it has a [strip] section look for the command in
            that section and apply the strip rule
        '''
        config = self.configs[site]

        strip = TukeyCli.__STRIP_SECTION

        command = command.lower()

        if strip in config.sections():
            if command in config.options(strip):
                value = config.get(strip, command)
                return self.trans.strip(result, value)

        return result

    def transform(self, json_string, site, command, values):
        '''
           look at the config transformations:command section
           and apply all the rules specified in there
        '''
        section_name = TukeyCli.__TRANS_SECTION + command
        config = self.configs[site]

        if section_name not in config.sections():
            return json_string

        section = config.options(section_name)

        for option in section:
            path = config.get(section_name, option)
            if ' ' in option:
                split_option = option.split(' ')
                option = ':'.join([split_option[0].upper(), split_option[1]])

            json_string = self.trans.transform_list(json_string, option, path)

        return self.replace_var(json_string, values)


    def tag(self, json_string, site):
        '''
            json_string is the result of command for a particular site
            add the tag attribute to each entry as specified in the conf
            TODO: this is transitioning from the old style config to the
            new this needs to be redone.
        '''
        if site == "all" or json_string == '[{"error": ""}]':
            return json_string

        if site.startswith("login"): 
            name = local_settings.clouds[site[5:]]["name"] + " Login Node"
        elif site.startswith("cluster"):
            name = local_settings.clouds[site[7:]]["name"] + " Cluster Node"
        else:
            name = local_settings.clouds[site]["name"]


        json_string = self.trans.add_attr(json_string, "cloud", name)
        json_string = self.trans.add_attr(json_string, "cloud_name", name)
        json_string = self.trans.add_attr(json_string, "cloud_id", site)

        return json_string


    def set_error(self, site, command_name, error):
        '''
            create an object string with the error
            message as the value of an error attribute defined
            by the config for this site and command name
        '''

        config = self.configs[site]

        section = TukeyCli.__ERROR_SECTION

        new_list = self.trans.empty()

        cmd_lower = command_name.lower()

        if section in config.sections() and cmd_lower in config.options(section):
            error_name = config.get(section, cmd_lower)
        else:
            error_name = TukeyCli.__DEFAULT_ERROR

        new_list = self.trans.add_attr(new_list, error_name, error)

        return new_list




    def execute_commands(self, command_name, values, object_name=None,
                         single=False, proxy_method=None):
        '''
            given a command and values dictionary check which of the
            current sites are active then perform the transformations
            on the command for each site using the values then
            execute the commands and return the result
        '''

        commands = self.generate_commands(command_name, values)

        if single:
            results = {}
        else:
            results = []

        for (site, cmd) in commands.items():
            try:
                result = ''
                stderr = ''

                config = self.configs[site]
                sections = config.sections()

                if cmd == TukeyCli.__PROXY_COMMAND:
                    site_values = self.__site_values(site, values)
                    host = config.get(TukeyCli.__PROXY_SECTION, 'host')
                    raw_output = proxy_method(host, site_values["tokenId"],
                        site_values["tenantId"])
                else:
                    p = Popen(cmd, shell=True, executable='/bin/bash', stdout=PIPE, stderr=PIPE)

                    raw_output, stderr = p.communicate()

                    if raw_output == TukeyCli.__PROXY_COMMAND:
                        site_values = self.__site_values(site, values)
                        host = config.get(TukeyCli.__PROXY_SECTION, 'host')
                        raw_output = proxy_method(host, site_values["tokenId"],
                             site_values["tenantId"])

                result = self.strip(raw_output, site, command_name)

                result = self.transform(result, site, command_name,
                                        self.__site_values(site, values))

            except Exception, e:
                result = self.set_error(site, command_name, str(e))

            finally:

                if result == '':
                    error = raw_output + stderr
                    result = self.set_error(site, command_name, error)

                result = self.tag(result, site)

                if not single:
                    results += self.trans.decode(result)
                elif result != self.trans.empty_none() \
                    and result != self.trans.empty() \
                    and result != '[{"error": ""}]':
                    results = self.trans.decode(result)
                    try:
                        results = results[0]
                    except IndexError:
                        pass
                    except KeyError:
                        pass


        if object_name is not None:
            results = {object_name: results}

        return self.trans.encode(results)


    def __site_values(self, site, values):
        site_values = {}
        if TukeyCli.GLOBAL_SECTION in values:
            site_values = values[TukeyCli.GLOBAL_SECTION]
        if site in values:
            site_values.update(values[site])
        return site_values



    def get_enabled_sites(self, values):
        '''
            for each site check that is enabled and then
            return a dto list of the sites that are enabled
        '''
        enabled = []
        for site in self.get_sites():
            if self.check_enabled(site, self.__site_values(site, values)):
                enabled.append({"name": site})
        return self.trans.encode(enabled)



