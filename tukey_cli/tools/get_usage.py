import json
import logging
import logging.handlers
import os
import psycopg2
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../../local')
import local_settings

logger = logging.getLogger('tukey-usage')
logger.setLevel(local_settings.LOG_LEVEL)

formatter = logging.Formatter(local_settings.LOG_FORMAT)

log_file_name = local_settings.LOG_DIR + 'tukey-usage.log'

logFile = logging.handlers.WatchedFileHandler(log_file_name)
logFile.setFormatter(formatter)

logger.addHandler(logFile)



def time_to_unix(time_str):
    format_str = '%Y-%m-%dT%H:%M:%S.%f'

    return int(time.mktime(time.strptime(time_str, format_str)))


def time_to_unix(time_str):
    if '.' in time_str:
        format_str = '%Y-%m-%dT%H:%M:%S.%f'
    else:
        format_str = '%Y-%m-%dT%H:%M:%S'

    return int(time.mktime(time.strptime(time_str, format_str)))


def get_usage_attribute(start, stop, resource, username, attr, name, hours=False):

    usage_hours = "select sum(val) / 60 as %(name)s "

    usage_mean = "select sum(val) / count(val) as %(name)s "

    usage_template = """
        from log
        where ts < %(stop)s and ts > %(start)s 
        and res='%(resource)s' 
        and fea='%(username)s-%(attr)s';
    """

    if hours:
        usage_template = usage_hours + usage_template 
    else:
        usage_template = usage_mean + usage_template

    usage_query = usage_template % locals()

    logger.debug(usage_query)

    return usage_query


def get_usages(resources, attributes):

    usages = []

    for name, resource in resources.items():
        for attr in attributes:
            usages.append((resource, attr, name))

    return usages


def main():

    conn_template = "dbname='%s' user='%s' host='%s' password='%s'"
    db_name = local_settings.USAGE_DB_NAME
    db_username = local_settings.USAGE_DB_USERNAME
    db_password =  local_settings.USAGE_DB_PASSWORD
    host = local_settings.USAGE_DB_HOST

    username = sys.argv[2]

    conn_str = conn_template % (db_name,db_username,host,db_password)

    # if can't connect to db don't recover
    conn = psycopg2.connect(conn_str)

    cur = conn.cursor()

    tenant_id = sys.argv[4]

    start = sys.argv[2]
    stop = sys.argv[3]

    _start_unix = time_to_unix(start)
    _stop_unix = time_to_unix(stop)

    total_hours = (_stop_unix - _start_unix) / (60.* 60)

    resources = local_settings.USAGE_RESOURCES

    attributes = local_settings.USAGE_ATTRIBUTES

    usages = []

    for resource_type in resources.keys():
        usages = get_usages(resources[resource_type], 
	    attributes[resource_type])

    logger.debug(usages)

    results = {}

    for resource, attr, name in usages:
	result_key = name + '_' + attr
        query = get_usage_attribute(_start_unix,
            _stop_unix, resource, tenant_id, attr, result_key,
            attr in local_settings.USAGE_HOURS)
        cur.execute(query)
        results[result_key] =  cur.fetchone()[0]

    results =  {key: result if key.endswith("du") or result is None else float(result) for key, result in results.items()}

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

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
