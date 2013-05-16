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

import psycopg2
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings


def connect():
    conn_template = "dbname='%s' user='%s' host='%s' password='%s'"
    db_name = 'federated_auth'
    db_username = 'cloudgui'
    db_password = local_settings.AUTH_DB_PASSWORD
    host = local_settings.AUTH_DB_HOST


    conn_str = conn_template % (db_name,db_username,host,db_password)

    # if can't connect to db don't recover
    return psycopg2.connect(conn_str)


def connect_and_query(query):

    try:
        conn = connect()

        cur = conn.cursor()

        cur.execute(query)

        results = cur.fetchone()

        conn.commit()

        cur.close()
        conn.close()

    except:
        cur.close()
        conn.close()
        raise

    return results



def userInfo(method, id, cloud_name):
    logger = logging.getLogger('tukey-auth')

    pre_query = '''
        select username, password from
        login join login_enabled on login.id = login_enabled.login_id
        join login_identifier on login.userid = login_identifier.userid
        join login_identifier_enabled on login_identifier.id =
            login_identifier_enabled.login_identifier_id
        join login_method on login_method.method_id = login_identifier.method_id
        join cloud on cloud.cloud_id = login.cloud_id
        where cloud_name='%(cloud)s' and login_method.method_name='%(meth)s'
            and login_identifier.identifier='%(id)s';
    '''

    query = pre_query % {"meth": method, "id":id, "cloud": cloud_name}

    creds = connect_and_query(query)

    if creds is None:
        logger.debug("creds is none")
        creds = '', ''

    logger.debug(query)
    logger.debug(creds)

    return creds


def get_key_from_db(cloud, username):

    query = """
        select password from login, cloud where
        login.cloud_id = cloud.cloud_id and cloud_name='%(cloud)s'
        and username='%(username)s'
    """ % locals()

    result = connect_and_query(query)

    if result is not None:
        return result[0]
    return None


def enable_identifier(username, identifier, method):

    insert_and_query = """
        insert into login_identifier_enabled (login_identifier_id)
        select login_identifier.id from login_identifier
        join login on login_identifier.userid=login.userid
        join login_method on login_identifier.method_id = login_method.method_id
        where username='%(username)s' and identifier='%(identifier)s'
            and method_name='%(method)s';
        select login_identifier_id from login_identifier_enabled
        join login_identifier on login_identifier_enabled.login_identifier_id =
            login_identifier.id
        join login_method on login_identifier.method_id = login_method.method_id
        join login on login_identifier.userid=login.userid
        where username='%(username)s' and identifier='%(identifier)s'
            and method_name='%(method)s';

    """ % locals()

    return connect_and_query(insert_and_query)


def insert_sshkey(cloud, username, pubkey, fingerprint, keyname):
    logger = logging.getLogger('tukey-auth')

    insert_and_query = """
        insert into keypair (pubkey, fingerprint, name, userid, cloud_id)
        select '%(pubkey)s', '%(fingerprint)s', '%(keyname)s', userid, cloud.cloud_id
        from cloud, login where username='%(username)s' and
            cloud_name='%(cloud)s' and login.cloud_id=cloud.cloud_id;
        select id from keypair where fingerprint='%(fingerprint)s';
    """ % locals()

    return connect_and_query(insert_and_query)


def delete_sshkey(cloud, username, keyname):

    logger = logging.getLogger('tukey-auth')
    delete_keypair = """
        delete from keypair using cloud, login
        where name='%(keyname)s' and keypair.userid=login.userid and
        cloud.cloud_name='%(cloud)s' and cloud.cloud_id=login.cloud_id
        and keypair.cloud_id = cloud.cloud_id
        and login.username='%(username)s';
    """ % locals()

    logger.debug(delete_keypair)
    result = True
    try:
        conn = connect()

        cur = conn.cursor()
        cur.execute(delete_keypair)

        conn.commit()

    except:
        result = False

    finally:
        cur.close()
        conn.close()

    return result


def get_keypairs(cloud, username):
    logger = logging.getLogger('tukey-auth')

    query = """
        select name, fingerprint, pubkey from keypair, login, cloud
        where cloud_name='%(cloud)s' and cloud.cloud_id = keypair.cloud_id
        and login.cloud_id = cloud.cloud_id
        and login.username='%(username)s' and login.userid=keypair.userid;
    """ % locals()

    results = []

    try:
        conn = connect()

        cur = conn.cursor()

        cur.execute(query)

        results = cur.fetchall()

    except:
        pass

    finally:
        cur.close()
        conn.close()

    attributes = ['name', 'fingerprint', 'public_key']

    logger.debug(query)
    logger.debug(results)

    return [ {"keypair": {attributes[i]: row[i]
        for i in range(0,len(row)) }}  for row in results]


def get_keypair(cloud, username, keyname):
    logger = logging.getLogger('tukey-auth')

    select_keypair = """
        select pubkey, fingerprint from keypair, cloud, login
        where name='%(keyname)s' and username='%(username)s' and
        cloud_name='%(cloud)s' and cloud.cloud_id = login.cloud_id
        and login.userid = keypair.userid;
    """ % locals()

    logger.debug(select_keypair)
    return connect_and_query(select_keypair)
