#!/usr/bin/python
import logging
import psycopg2
import sys
import optparse

from local import local_settings

logger = logging.getLogger(__name__)

def connect():
    conn_template = "dbname='%s' user='%s' host='%s' password='%s'"
    db_name = 'federated_auth'
    db_username = 'cloudgui'
    db_password = local_settings.AUTH_DB_PASSWORD
    host = 'localhost'

    connection = None

    try:
        conn_str = conn_template % (db_name,db_username,host,db_password)
        connection = psycopg2.connect(conn_str)

    except psycopg2.Warning, e:
        logger.warning(e.pgerror)

    except psycopg2.Error, e:
        logger.error(e.pgerror)

    finally:
        return connection


def connect_and_query(cur, query):
    # only for queries no commit/rollback
    try:
        cur.execute(query)
        results = cur.fetchone()

    except StandarError:
        logger.error(e.pgerror)
    
    return results


def exists_query(cur, query):
    
    print query

    return connect_and_query(cur, query)[0] > 0

def account_exists(cur, cloud, username):

    exists = """
    SELECT COUNT(id) FROM login, cloud 
    where cloud_name='%(cloud)s' and username='%(username)s'
    and login.cloud_id = cloud.cloud_id;
    """ % locals()

    return exists_query(cur, exists)


def update_account(cloud, username, password):
    condition = """
    WHERE username='%(username)s' and 
    cloud_id=(SELECT cloud_id FROM cloud WHERE cloud_name='%(cloud)s');
    """
    
    return [ 
        ("UPDATE login SET password='%(password)s' " + condition) % locals()
    ]


def account_enabled(cur, cloud, username):

    exists = """
    SELECT COUNT(id) FROM login_enabled, cloud, login
    where cloud_name='%(cloud)s' and username='%(username)s'
    and login.cloud_id = cloud.cloud_id
    and login.id = login_enabled.login_id;
    """ % locals()

    return exists_query(cur, exists)



def login_enabled(cur, method, identifier):

    exists = """SELECT COUNT(login_identifier_id) FROM 
    login_identifier_enabled 
    JOIN login_identifier ON login_identifier.id = login_identifier_enabled.login_identifier_id
    JOIN login_method ON login_method.method_id = login_identifier.method_id 
    WHERE method_name='%(method)s' and identifier='%(identifier)s';""" % locals()

    return exists_query(cur, exists)



def enable_account(cloud, username):
    condition = """
    WHERE username='%(username)s' and 
    cloud_id=(SELECT cloud_id FROM cloud WHERE cloud_name='%(cloud)s');
    """

    return [
        ("INSERT INTO login_enabled (login_id) SELECT id FROM login " + condition) % locals()
    ]

def create_account(cloud, username, password):
    
    return [
    "INSERT INTO userid DEFAULT VALUES;",
    """INSERT INTO login (userid, cloud_id, username, password) 
    VALUES (currval('userid_userid_sequence'),
    (SELECT cloud_id FROM cloud WHERE cloud_name='%(cloud)s'),
    '%(username)s', '%(password)s');""" % locals()
    ]


def login_exists(cur, method, identifier):
    
    exists = """SELECT COUNT(id) FROM login_identifier 
    JOIN login_method ON login_method.method_id = login_identifier.method_id 
    WHERE method_name='%(method)s' and identifier='%(identifier)s';""" % locals()

    return exists_query(cur, exists)


def enable_login(method, identifier):
    return [
    """INSERT INTO login_identifier_enabled (login_identifier_id) 
    SELECT id FROM login_identifier JOIN login_method 
    ON login_method.method_id = login_identifier.method_id 
    WHERE method_name='%(method)s' and identifier='%(identifier)s';""" % locals()
    ]


def create_login(method, identifier, cloud, username):
    return [
    """INSERT INTO login_identifier (userid, method_id, identifier) 
    VALUES ((SELECT userid FROM login JOIN cloud ON login.cloud_id = cloud.cloud_id
        WHERE cloud_name='%(cloud)s' and username='%(username)s'),
    (SELECT method_id FROM login_method where method_name='%(method)s'),
     '%(identifier)s');""" % locals(),
    """INSERT INTO login_identifier_enabled (login_identifier_id) 
    VALUES (currval('login_identifier_id_sequence'));""" % locals()
    ]


def add_account(cloud, username, password, method, identifier):

    return [
    """INSERT INTO login (userid, cloud_id, username, password) 
    VALUES (SELECT userid from login_identifier
    JOIN login_method on login_method.method_id = login_identifier.method_id
    WHERE method_name='%(method)s' and identifier='%(identifier)s'),
    (SELECT cloud_id FROM cloud WHERE cloud_name='%(cloud)s'),
    '%(username)s', '%(password)s');""" % locals()
    ]



def run_statements(statements):
    conn = connect()
    cur = conn.cursor()

    try:
        for statement in statements:
            print statement
            cur.execute(statement)

        conn.commit()

    except psycopg2.Warning, e:
        logger.warning(e.pgerror)

    except psycopg2.Error, e:
        logger.error(e.pgerror)

    finally:
      cur.close()
      conn.close()


def process_account(cloud, method, identifier, username, password):

    statements = []

    conn = connect()
    cur = conn.cursor()

    try:
        if account_exists(cur, cloud, username):
            # allow for changing password
            statements += update_account(cloud, username, password)
            if not account_enabled(cur, cloud, username):
                statements += enable_account(cloud, username)
        else:
            if login_exists(cur, method, identifier):
                add_account(cloud, username, password, method, identifier)
            else:
                statements += create_account(cloud, username, password)
            statements += enable_account(cloud, username)

        if login_exists(cur, method, identifier):
            if not login_enabled(cur, method, identifier):
                statements += enable_login(method, identifier)
        else:
            statements += create_login(method, identifier, cloud, username)
            enable_login(method, identifier)

    except psycopg2.Warning, e:
        logger.warning(e.pgerror)

    except psycopg2.Error, e:
        logger.error(e.pgerror)

    finally:
      cur.close()
      conn.close()

    run_statements(statements)


def disable_all():

    run_statements(["DELETE FROM login_enabled;",
        "DELETE FROM login_identifier_enabled;"])

def disable_login(username, cloud):

    run_statements(["""DELETE FROM login_enabled
        USING login, cloud WHERE login.id=login_enabled.login_id
        and login.cloud_id=cloud.cloud_id
        and login.username='%(username)s' and cloud.name='%(cloud)s'"""
        % locals()])

def delete_login(username, cloud):

    run_statements(["""DELETE FROM login
        USING cloud WHERE login.cloud_id=cloud.cloud_id
        and login.username='%(username)s' and cloud.name='%(cloud)s'"""
        % locals()])

def disable_identifier(identifier):

    run_statements(["""DELETE FROM login_identifier_enabled
        USING login_identifier WHERE
        login_identifier.identifier='%(identifier)s'
        and login_identifier.id = login_identifier_enabled.login_identifier_id;"""
        % locals()])

def delete_identifier(identifier):

    run_statements(["""DELETE FROM login_identifier
        WHERE login_identifier.identifier='%(identifier)s'"""
        % locals()])



if __name__ == "__main__":

    usage = """usage: %prog [options] [cloud method identifer username password]
use: %prog -d to disable all accounts"""

    parser = optparse.OptionParser(usage)

    parser.add_option("-d", "--disable-all",
        action="store_true", dest="disable_all")

#    parser.add_option("-d", "--disable",
#        action="store_true", dest="disable")

    (options, args) = parser.parse_args()

    if options.disable_all:
        disable_all()
    
    else:
        if len(args) != 5:
            parser.error("incorrect number of arguments")
            exit(1)

        process_account(args[0], args[1], args[2], args[3], args[4])
