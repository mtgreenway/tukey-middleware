. install_settings.sh

# Warning this is a dangerous script probably shouldnt use it
# just for me for testing 

# remove temp dir
rm -rf $TEMP_DIR

sudo rm -rf $MIDDLEWARE_DIR

for site_name in auth glance nova
do
    sudo a2dissite $site_name
    sudo rm $APACHE_SITES_AVAILABLE/${site_name}
done

