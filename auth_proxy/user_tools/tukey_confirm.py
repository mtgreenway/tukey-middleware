import base64
import hmac
import hashlib
import json
import sys
from time import gmtime, strftime
import urllib


def name_stamp(key, username, identifier, 
	time=strftime("%d%b%Y%H:%M:%S", gmtime())):

    digest_maker = hmac.new(key + time,
         '', hashlib.sha1)

    digest_maker.update(username)
    digest_maker.update(identifier)

    return digest_maker.hexdigest()


def validate_stamp(key, stamp, username, identifier, 
	time=strftime("%d%b%Y%H:%M:%S", gmtime())):
    return stamp == name_stamp(key, username, identifier, time)
