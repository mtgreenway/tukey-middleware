#!/bin/bash

# Somewhat sloppy but hopefully complete script for installing the 
# tukey middleware.  Meant mostly for thourough documentation.

. install_settings.sh

if $INSTALL_PRE
then
    sudo apt-get update
    sudo apt-get install -y \
    git \
    apache2 \
    libapache2-mod-wsgi \
    python-virtualenv \
    postgresql-9.1 \
    postgresql-server-dev-9.1 \
    postgresql-server-dev-all \
    swig \
    build-essential \
    memcached \
    python-dev \
    euca2ools
    
    # this can probably go on the line above
    sudo apt-get install -y python-psycopg2
fi

if $CLONE_MIDDLEWARE;
then
	git clone $MIDDLEWARE_REPO $TEMP_DIR
	sudo cp -r $TEMP_DIR $MIDDLEWARE_DIR
	sudo chown -R $TUKEY_USER:$TUKEY_GROUP $MIDDLEWARE_DIR
	cd $MIDDLEWARE_DIR
fi

# Need to symlink this 
ln -s $LOCAL_SETTINGS_FILE $MIDDLEWARE_DIR/local/local_settings.py

cd $MIDDLEWARE_DIR

# the parameters we can pass to this script to prevent it from installing
# the database is:		--no-database
# Dont install the logdir: 	--no-logdir
# No apache:			--no-apache

# do the apache stuff ourself
python tools/install_venv.py --no-apache --no-database



# need to configure these bad boys first 

# The auth site
echo "# Generated by install_tukey_middleware.sh 
NameVirtualHost localhost:$AUTH_PORT

<Virtualhost localhost:$AUTH_PORT>

WSGIScriptAlias / $MIDDLEWARE_DIR/auth_proxy/auth_wsgi.py

WSGIDaemonProcess tukey_auth user=$TUKEY_USER group=$TUKEY_GROUP processes=3 threads=2 python-path=$MIDDLEWARE_DIR/local:$MIDDLEWARE_DIR/auth_proxy:$MIDDLEWARE_DIR/.venv/lib/python2.7/site-packages:$MIDDLEWARE_DIR/.venv/local/lib/python2.7/site-packages

WSGIProcessGroup tukey_auth

<Directory $MIDDLEWARE_DIR/auth_proxy>
  Order allow,deny
  Allow from all
</Directory>

</virtualhost>" > $MIDDLEWARE_DIR/bin/auth-apache.conf

# The nova site
echo "# Generated by install_tukey_middleware.sh 
NameVirtualHost localhost:$NOVA_PORT

<Virtualhost localhost:$NOVA_PORT>

WSGIScriptAlias / $MIDDLEWARE_DIR/tukey_cli/nova_wsgi.py

WSGIDaemonProcess tukey-api user=$TUKEY_USER group=$TUKEY_GROUP processes=3 threads=2 python-path=$MIDDLEWARE_DIR/local:$MIDDLEWARE_DIR/tukey_cli:$MIDDLEWARE_DIR/.venv/lib/python2.7/site-packages:$MIDDLEWARE_DIR/.venv/local/lib/python2.7/site-packages

WSGIProcessGroup tukey-api

<Directory $MIDDLEWARE_DIR/tukey_cli>
  Order allow,deny
  Allow from all
</Directory>

</virtualhost>" > $MIDDLEWARE_DIR/bin/nova-apache.conf

# The glance site
echo "# Generated by install_tukey_middleware.sh 
NameVirtualHost localhost:$GLANCE_PORT

<Virtualhost localhost:$GLANCE_PORT>

WSGIScriptAlias / $MIDDLEWARE_DIR/tukey_cli/glance_wsgi.py

WSGIDaemonProcess glance-api user=ubuntu group=ubuntu processes=3 threads=1 python-path=$MIDDLEWARE_DIR/local:$MIDDLEWARE_DIR/tukey_cli:$MIDDLEWARE_DIR/.venv/lib/python2.7/site-packages:$MIDDLEWARE_DIR/.venv/local/lib/python2.7/site-packages

WSGIProcessGroup glance-api

<Directory $MIDDLEWARE_DIR/tukey_cli>
  Order allow,deny
  Allow from all
</Directory>

</virtualhost>" > $MIDDLEWARE_DIR/bin/glance-apache.conf

for site_name in auth glance nova
do
    sudo ln -s $MIDDLEWARE_DIR/bin/${site_name}-apache.conf $APACHE_SITES_AVAILABLE/${site_name}
    sudo a2ensite $site_name
done

# Create configuration files from templates
ln -s $CONFIG_GEN_SETTINGS_FILE $MIDDLEWARE_DIR/config_gen/settings.py
python $MIDDLEWARE_DIR/config_gen/config_gen.py $MIDDLEWARE_DIR

# linking pgp public keys 

ln -s $PGP_KEYDIR $MIDDLEWARE_DIR/tukey_cli/etc/keys

echo "Please edit auth_proxy/iptables.py to have proper settings then RUN!!!"
