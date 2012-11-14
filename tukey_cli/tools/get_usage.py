import json
import sys
import time

import logging
import logging.handlers

import psycopg2


sys.path.append('../local')
import local_settings


logger = logging.getLogger('tukey-usage')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s %(filename)s:%(lineno)d')

log_file_name = local_settings.LOG_DIR + 'tukey-usage.log'

logFile = logging.handlers.WatchedFileHandler(log_file_name)
logFile.setLevel(logging.DEBUG)
logFile.setFormatter(formatter)

logger.addHandler(logFile)



def time_to_unix(time_str):
    format_str = '%Y-%m-%dT%H:%M:%S.%f'

    return int(time.mktime(time.strptime(time_str, format_str)))


def query_usage(query):

    conn_template = "dbname='%s' user='%s' host='%s' password='%s'"
    db_name = 'dashboard'
    db_username = 'console_ro'
    db_password =  local_settings.USAGE_DB_PASSWORD
    host = local_settings.USAGE_DB_HOST

    username = sys.argv[2]

    conn_str = conn_template % (db_name,db_username,host,db_password)

    # if can't connect to db don't recover
    conn = psycopg2.connect(conn_str)

    cur = conn.cursor()

    cur.execute(query)

    results = cur.fetchone()

    cur.close()

    return results


def time_to_unix(time_str):
    if '.' in time_str:
        format_str = '%Y-%m-%dT%H:%M:%S.%f'
    else:
        format_str = '%Y-%m-%dT%H:%M:%S'

    return int(time.mktime(time.strptime(time_str, format_str)))


def get_usage_attribute(start, stop, resource, username, attr, name):

    usage_template = """
        select sum(val) / count(val) as %(name)s
        from log
        where ts < %(stop)s and ts > %(start)s 
        and res='%(resource)s' 
        and fea='%(username)s-%(attr)s';
    """    

    usage_query = usage_template % locals()

    logger.debug(usage_query)

    return query_usage(usage_query)[0]


def get_usages(resources, attributes):

    usages = []

    for name, resource in resources.items():
        for attr in attributes:
            usages.append((resource, attr, name))

    return usages


def main():

    tenant_id = sys.argv[4]

    start = sys.argv[2]
    stop = sys.argv[3]

    _start_unix = time_to_unix(start)
    _stop_unix = time_to_unix(stop)

    total_hours = (_stop_unix - _start_unix) / (60.* 60)

    resources = {
	'cloud': {
	    'adler': 'OSDC Cloud2',
	    'sullivan': 'OSDC-Sullivan'
	},
	'hadoop': {
	name.replace('-','_').lower(): name for name in [
	    'OCC-Y', 'OCC-LVOC-HADOOP']
	}
    }

    attributes = {
	'hadoop': ['jobs', 'hdfsdu'],
	'cloud': ['du', 'cores', 'ram']
    }

    usages = []

    for resource_type in resources.keys():
        usages = get_usages(resources[resource_type], 
	    attributes[resource_type])

    logger.debug(usages)

    results = {}

    for resource, attr, name in usages:
	result_key = name + '_' + attr
        results[result_key] = get_usage_attribute(_start_unix, _stop_unix, resource,
	    tenant_id, attr, result_key)

    results =  {key: result if key.endswith("du") or result is None else float(result) * total_hours for key, result in results.items()}

    results = {key: float(result) for key, result in results.items() if result is not None}

    logger.debug("query result %s", results)

    # create the aggregates
    
    for resource_type in attributes.keys():
        for attribute in attributes[resource_type]:
	    results[resource_type + '_' + attribute] = 0
            for cloud in resources[resource_type].keys():
		if cloud + '_' + attribute in results:
		    results[resource_type + '_' + attribute] += results[cloud + '_' + attribute]

    logger.debug(results)

    final_usages = dict({ 
        "server_usages": [], 
        "start": start, 
        "stop": stop, 
        "tenant_id": tenant_id, 
        "total_hours": total_hours 
    }.items() + results.items())

    logger.debug(final_usages)

    print json.dumps([final_usages])


if __name__ == "__main__":
    main()
