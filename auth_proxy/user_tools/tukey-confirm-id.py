#!/usr/bin/python
import getpass
import sys
import urllib
import urllib2
import os


from tukey_confirm import name_stamp


def query_string(stamp, username, method, identifier):
    return urllib.urlencode(locals())

if __name__ == "__main__":


    if 'OS_PASSWORD' in os.environ:
        secret = os.environ['OS_PASSWORD']
    elif 'EC2_SECRET_KEY' in os.environ:
        secret = os.environ['EC2_SECRET_KEY']
    else:
        print 'EC2_SECRET_KEY or OS_PASSWORD environment variable must be set.'
        exit(1)

# not present before 2.7, ...
    try:
        import argparse
        parser = argparse.ArgumentParser(description='Register federated identifer for Console.')
        parser.add_argument('method', help='sign in method (example: shibboleth)')
        parser.add_argument('identifier', help='sign in id (example: mgreenway@uchicago.edu)')

        args = parser.parse_args()

    except ImportError:
	if len(sys.argv) != 3:
	    print "Requires two arguments: "
	    print __file__ + " method identifer"
	    exit(1)

        args = lambda: None
        args.method = sys.argv[1]
        args.identifier = sys.argv[2]

    args = parser.parse_args()

    username = getpass.getuser()

    stamp = name_stamp(secret, username, args.identifier)

    query = query_string(stamp, username, args.method, args.identifier)

    response = urllib2.urlopen('http://172.16.1.10:8666?' + query)

    print response.read()

