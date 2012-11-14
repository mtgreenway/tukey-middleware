import sys
import json
import requests

r = requests.get('http://%s:%s/%s' % (sys.argv[1], sys.argv[2], sys.argv[3]))
print json.dumps([json.loads(r.text)['quota_set']])
