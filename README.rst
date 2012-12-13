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
    $ sudo apt-get build-dep python-psycopg2
    

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


There are three main proxies you will need to start: the authentication
service the nova proxy and the glance proxy
Run the start up scripts for each service::

  $ ./auth.sh
  $ ./nova.sh
  $ ./glance.sh

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
