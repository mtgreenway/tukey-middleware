#!/usr/bin/python

# Grossman Computing Laboratory
# Institute for Genomics and Systems Biology
# The University of Chicago 900 E 57th St KCBD 10146, Chicago, IL 60637
# Tel: +1-773-702-9765. Fax: +1-773-834-2877
# ------------------------------------------
#
# Matthew Greenway <mgreenway@uchicago.edu>

# Handles user account creation within Postgres db

import psycopg2
from optparse import OptionParser

conn_template = "dbname='%s' user='%s' host='%s' password='%s'"
dbname = 'cloudgui'
user = 'cloudgui'
host = 'localhost'
password = 'r3dc0wbluEm$$N'

add_user = "insert into login (username) values ('%s');"

get_id = "select userid from login where username = '%s';"

enable = "insert into login_enabled (userid) values (%s);"

add_shib = "insert into login_shibboleth (userid, eppn) values (%s, '%s');"

del_user = "delete from login where username = '%s';"

disable = "delete from login_enabled where userid = %s;"

del_shib = "delete from login_shibboleth where userid = %s;"

del_openid = "delete from login_openid where userid = %s;"

del_shib_eppn = "delete from login_shibboleth where eppn = '%s';"

def main():

    usage = "usage: %prog [options] username"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--shibboleth", default="",
                      action="store", dest="shib",
                      help="Create user with this Shibboleth eppn")
    parser.add_option("-d", "--delete",
                      action="store_true", dest="delete",
                      help="Delete user with username")
    parser.add_option("-o", "--openid",
                      action="store_true", dest="openid",
                      help="Use with delete to delete users OpenIDs")
    parser.add_option("-e", "--exists",
                      action="store_true", dest="exists",
                      help="Modify existing user")

    (opts, args) = parser.parse_args()

    username = args[0]
    
    conn_str =     conn_template % (dbname,user,host,password)

    # if can't connect to db don't recover
    conn = psycopg2.connect(conn_str)

    cur = conn.cursor()

    if opts.delete:
        if opts.shib != "":
            delete_user_shib(opts.shib, cur)
        elif opts.openid:
            delete_user_openid(username, cur) 
        else:
            delete_user(username, cur)
    elif opts.shib != "":
        if opts.exists:
            add_user_shib(username, opts.shib, cur)
        else:
            create_user_shib(username, opts.shib, cur)
    else:
        create_user(username, cur)
    
    conn.commit()

def get_userid(username, cur):
    cur.execute(get_id % (username))

    rows = cur.fetchall()

    userid = rows[0][0]
    
    return userid
    
def create_user(username, cur):
    '''
        creates a user and then returns their
        user id.
        username is a string that is the name that
        user has in /var/lib/cloudgui/users/
        cur is the db cursor
    '''
    cur.execute(add_user % (username))

    userid = get_userid(username, cur)

    cur.execute(enable % (userid))

    return userid

def create_user_shib(username, eppn, cur):
    '''
        create user with shibboleth login by
        first calling create_user and then inserting
        the eppn.
        The eppn is an email address used in shibboleth
        authentication.
        Returns the user id
    '''
    userid = create_user(username, cur)
    
    cur.execute(add_shib % (userid, eppn))
    
    return userid
    
def add_user_shib(username, eppn, cur):
    '''
        give an existing user this Shibboleth eppn
    '''
    userid = get_userid(username, cur)
    
    cur.execute(add_shib % (userid, eppn))
    
    return userid
    
def delete_user(username, cur):
    '''
       delete all of the users OpenIDs and the 
       users Shibboleth eppns and remove from enabled
       then delete the user
    '''
    userid = get_userid(username, cur)
    
    cur.execute(disable % (userid))
    
    cur.execute(del_openid % (userid))
    
    cur.execute(del_shib % (userid))
    
    cur.execute(del_user % (username))

def delete_user_shib(eppn, cur):
    '''
        delete a users eppn from their shibboleth
        info
    '''
    cur.execute(del_shib_eppn % (eppn))

def delete_user_openid(username, cur):
    '''
        delete all of the OpenIDs registered
        to this user
    '''
    userid = get_userid(username, cur)

    cur.execute(del_openid % (userid))
    
    
if __name__ == "__main__":
    main()

