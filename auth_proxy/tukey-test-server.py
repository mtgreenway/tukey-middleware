import sys
import json

from user_tools.tukey_confirm import validate_stamp

from time import gmtime, strftime

from webob import Request

from auth_db import get_key_from_db, enable_identifier


def get_secret_key(username):
    rcfile = open("/var/lib/cloudgui/users/%s/.euca/eucarc" % username)
    for line in rcfile.readlines():
	if line.startswith('export EC2_SECRET_KEY='):
	    print line.split('=')[1][1:-2]
	    return line.split('=')[1][1:-2]


def app(environ, start_response):

    time = strftime("%d%b%Y%H:%M:%S", gmtime())

    req = Request(environ)

    print req.params

    sullivan_key = get_key_from_db('sullivan', req.params['username'])

    if sullivan_key is not None:
	key = sullivan_key
    else:
	key = get_secret_key(req.params['username'])

    print get_key_from_db('sullivan', 'demo')

    if validate_stamp(key, req.params['stamp'], 
	req.params['username'], req.params['identifier'],
	time):

	try:
	    if enable_identifier(req.params['username'], 
		    req.params['identifier'],
		    req.params['method'].lower()):

		message = 'Success'
	    else:
		message = 'Identifier not registered with console.'
	except:
	    message = 'Error with registration'

    else:
	message = 'Not Authorized. Please try again.'

    start_response('200 OK', [('Content-Type', 'text/html')])
    from time import sleep
    return [message]

    
if __name__ == "__main__":
    from server_init import init_server

    init_server(app)
