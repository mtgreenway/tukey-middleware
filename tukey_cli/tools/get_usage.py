import json
import logging
import logging.handlers
import os
import psycopg2
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../../local')
import local_settings


LOGGER = logging.getLogger('tukey-usage')
LOGGER.setLevel(local_settings.LOG_LEVEL)

FORMATTER = logging.Formatter(local_settings.LOG_FORMAT)

LOG_FILE_NAME = local_settings.LOG_DIR + 'tukey-usage.log'

LOG_FILE = logging.handlers.WatchedFileHandler(LOG_FILE_NAME)
LOG_FILE.setFormatter(FORMATTER)

LOGGER.addHandler(LOG_FILE)


def time_to_unix(time_str):
    if '.' in time_str:
        format_str = '%Y-%m-%dT%H:%M:%S.%f'
    else:
        format_str = '%Y-%m-%dT%H:%M:%S'

    return int(time.mktime(time.strptime(time_str, format_str)))

        
def get_usage_batch(start, stop, username):
    ''' Get all of the users usage attributes at once using a single 
    powerful query.  One query to rule them all'''

    return ''.join(["""select res, fea, sum(val), count(val)
        from log where ts < %(stop)s and ts > %(start)s
        and fea like '%(username)s-""" % locals(), "%' group by res, fea;"])


def get_usages(resources, attributes):

    usages = []

    for name, resource in resources.items():
        for attr in attributes:
            usages.append((resource, attr, name))

    return usages


def main():

    conn_template = "dbname='%s' user='%s' host='%s' password='%s' port=%s"
    db_name = local_settings.USAGE_DB_NAME
    db_username = local_settings.USAGE_DB_USERNAME
    db_password = local_settings.USAGE_DB_PASSWORD
    host = local_settings.USAGE_DB_HOST
    port = local_settings.USAGE_DB_PORT

    conn_str = conn_template % (db_name, db_username, host, db_password, port)

    # if can't connect to db don't recover
    conn = psycopg2.connect(conn_str)

    cur = conn.cursor()

    start = sys.argv[1]
    stop = sys.argv[2]

    tenant_id = sys.argv[3]

    _start_unix = time_to_unix(start)
    _stop_unix = time_to_unix(stop)

    total_hours = (_stop_unix - _start_unix) / (60. * 60)

    resources = local_settings.USAGE_RESOURCES

    attributes = local_settings.USAGE_ATTRIBUTES

    usages = []

    for resource_type in resources.keys():
        usages = get_usages(resources[resource_type],
            attributes[resource_type])

    LOGGER.debug(usages)

    results = {}

    # run the master query and then query that for what we would like
    cur.execute(get_usage_batch(_start_unix, _stop_unix, tenant_id))
    batch_results = cur.fetchall()

    # possibly make this into a dict comprehension
    formatted = {}
    for result in batch_results:
        attr = result[1].split('-')[1]

        if result[0] not in formatted:
            formatted[result[0]] = {}

        if attr in local_settings.USAGE_HOURS:
            formatted[result[0]][attr] = result[2] / 60
        else:
            formatted[result[0]][attr] = result[2] / result[3]

    for resource, attr, name in usages:
        result_key = name + '_' + attr
        try:
            results[result_key] = formatted[resource][attr]
        except KeyError:
            results[result_key] = None


    results = {key: result if key.endswith("du") or result is None else float(
        result) for key, result in results.items()}

    results = {key: float(result) for key, result in results.items()
        if result is not None}

    LOGGER.debug("query result %s", results)

    # create the aggregates

    for resource_type in attributes.keys():
        for attribute in attributes[resource_type]:
            results[resource_type + '_' + attribute] = 0
            for cloud in resources[resource_type].keys():
                if cloud + '_' + attribute in results:
                    results[resource_type + '_' + attribute] += results[
                        cloud + '_' + attribute]

    LOGGER.debug(results)

    final_usages = dict({
        "server_usages": [],
        "start": start,
        "stop": stop,
        "tenant_id": tenant_id,
        "total_hours": total_hours
    }.items() + results.items())

    LOGGER.debug(final_usages)

    print json.dumps([final_usages])

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
