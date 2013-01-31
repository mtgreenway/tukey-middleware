=============================
Tukey Middleware
=============================

Tukey is a console for managing cloud resources particularly IaaS clouds.
Tukey is built on the OpenStack Dashboard, Horizon, and provides the
additional functionality of interacting with ec2 compatible clouds and
authentication via Shibboleth and OpenID.

Tukey Middleware provides access to multiple cloud resources using the 
a subset of the OpenStack Identity and Compute JSON APIs. Clouds currently
supported are Eucalyptus and OpenStack.

Tukey Middleware comes with example configurations for Open Science Data 
Cloud resources Adler and Sullivan, Eucalyptus and OpenStack clouds
respectively.

For info go to:

 * http://opensciencedatacloud.org

Dependencies
============

For Ubuntu use apt to install::

    $ sudo apt-get install python-virtualenv postgresql-9.1 postgresql-server-dev-9.1 swig build-essential memcached
    $ sudo apt-get python-psycopg2
    

Getting Started
===============

Before installing you will need to copy local/local_settings.py.example
to local/local_settings.py and put in the values for your cloud.

For local development, first create a virtualenv for the project.
In the ``tools`` directory there is a script to create one for you.
This script not only creates the virtualenv but it will also call two
additional scripts for setting up the database and the log directories
tools/create_db.sh and tools/create_log.sh respectively.  Both of these
scripts require sudo access and may need to modified to meet the
requirements of your system.::

  $ python tools/install_venv.py

M2Crypto usually has problems so you may need to copy the systemwide so
from somewhere like:
/usr/lib/python2.7/dist-packages/M2Crypto/__m2crypto.so to the the venv
installation.


Newer versions of the Keystone Client automatically send requests to
port 35357
To work with new versions of python-keystoneclient run the iptables.py 
script with root permissions::

  $ sudo python auth_proxy/iptables.py


There are three main proxies you will need to start: the authentication
service the nova proxy and the glance proxy
Run the start up scripts for each service::

  $ ./auth.sh
  $ ./nova.sh
  $ ./glance.sh


SSH Key Creation Service
========================

This requires gnupg.  Generate keyspairs on the tukey server
and the login server.  Put the tukey-server's public key in
tukey_cli/etc/keys.

To run the ssh-key creation service install tukey-middleware on the
login node server then as a user that has write permissions to all
users .ssh directories::

    # source .venv/bin/activate
    # cd auth_proxy 
    # python key_server.py 127.0.0.1 5005 PATH_TO_HOME


Configuration
=============

To modify the middleware to work with your particular resources you
will need to modify local/local_settings.py and the files in
tukey_cli/etc/enabled/

The files in tukey_cli/etc/enabled/ define the configuration for
resources and what rules should be applied to transform the API of 
those resources into the OpenStack JSON API.

A full documentation will be available soon.

Please contact Matthew Greenway mgreenway@uchicago.edu with any 
questions.


Eucalyptus
==========

Eucalyptus requires a directory that contains users euca credentials.
By default this is expected to /var/lib/cloudgui/users/
For example a eucalyptus user mgreenway would need to have
/var/lib/cloudgui/users/mgreenway/.euca/eucarc

Creating Users
==============

There is a create_tukey_user.py script to create and delete users::
    $ python create_tukey_user.py CLOUD METHOD IDENTIFIER USERNAME PASSWORD

Currently method needs to be openid or shibboleth.  For Eucalyptus users
the password will do nothing.

INSTALLING BEHIND APACHE
========================

Install Apache and mod_wsgi::
    $sudo apt-get install apache2 libapache2-mod-wsgi

Link to the configuration files::
    $sudo ln -s $(pwd)/bin/nova-apache.conf /etc/apache2/sites-enabled/nova-apache.conf
    $sudo ln -s $(pwd)/bin/glance-apache.conf /etc/apache2/sites-enabled/glance-apache.conf
    $sudo ln -s $(pwd)/bin/auth-apache.conf /etc/apache2/sites-enabled/auth-apache.conf
