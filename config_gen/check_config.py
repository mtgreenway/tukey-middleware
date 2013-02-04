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
#

''' Configuration parsing for temporary config builder script to deal with the
nonsense I have made'''

def log_config_error(error_message):
    ''' Display the error message with a wrapper '''
    print "Parsing config file failed with the following message:"
    print error_message

def _check_required(cloud_dict, required):
    ''' helper function to iterate cloud_dict and make sure all the
    values in required are present '''

    for attr in required:
        if attr not in cloud_dict.keys():
            log_config_error("Required field %s missing" % attr)
            return False
    return True

def _iff_required(attr, value, cloud_dict, required):
    ''' If the attr has value make sure cloud_dict has all the fields in
    required else make sure that it has none of them. '''

    if cloud_dict[attr] == value:
        if not _check_required(cloud_dict, required):
            return False
    else:
        for cloud_attr in cloud_dict.keys():
            if cloud_attr in required:
                log_config_error('Field %s requires "%s" %s' % (cloud_attr,
                    attr, value))
                return False

    return True

def check_config(clouds):
    '''Check the list of dictionaries that have the cloud info to make sure
    that the attributes are expected not duplicated and make sense in terms
    of the "cloud_type".  NOTE: Returns early '''

    # required fields
    required = ["cloud_name", "cloud_id", "cloud_type", "handle_login_keys"]

    # required if and only if "cloud_type" is openstack
    required_openstack = ["nova_host", "nova_port", "keystone_host",
        "keystone_port"]

    # required if and only if "handle_login_keys"
    required_login = ["gpg_fingerprint", "gpg_passphrase", "gpg_login_pubkey",
        "login_host", "login_port"]

    # make sure there is only one true value and at least one
    one_true = ["usage_cloud"]

    have_one_counts = {val: 0 for val in one_true}

    # all of the attributes we have looked at so far
    known_attributes = required + required_openstack + required_login + one_true

    # possible clouds
    cloud_types = ["openstack", "eucalyptus"]

    for cloud in clouds:
        # check required
        if not _check_required(cloud, required):
            return False
        # openstack
        if not _iff_required("cloud_type", "openstack", cloud,
            required_openstack):
            return False
        # login
        if not _iff_required("handle_login_keys", True, cloud, required_login):
            return False

        for attr in cloud.keys():
            if attr not in known_attributes:
                log_config_error("Unknown attribute %s" % attr)
                return False

        if cloud["cloud_type"].lower() not in cloud_types:
            log_config_error("Unknown cloud_type %s" % cloud["cloud_type"])
            return False

        for val in one_true:
            if val in cloud.keys() and cloud[val]:
                have_one_counts[val] += 1

    for (key, count) in have_one_counts.items():
        if count != 1:
            log_config_error("Attribute %s must be true exactly once" % key)
            return False

    return True
