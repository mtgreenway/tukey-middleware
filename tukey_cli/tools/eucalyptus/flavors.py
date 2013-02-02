import json
import sys

flavors = {
    "m1.small": {
        "name": "m1.small",
        "id": "m1.small",
        "vcpus": 1,
        "ram": 3584,
        "disk": 20,
        "swap": "",
        "OS-FLV-EXT-DATA:ephemeral": 0
    },
    "c1.medium": {
        "name": "c1.medium",
        "id": "c1.medium",
        "vcpus": 2,
        "ram": 7168,
        "disk": 20,
        "swap": "",
        "OS-FLV-EXT-DATA:ephemeral": 0
    },
    "m1.large": {
        "name": "m1.large",
        "id": "m1.large",
        "vcpus": 4,
        "ram": 14336,
        "disk": 20,
        "swap": "",
        "OS-FLV-EXT-DATA:ephemeral": 0
    },
    "m1.xlarge": {
        "name": "m1.xlarge",
        "id": "m1.xlarge",
        "vcpus": 8,
        "ram": 28672,
        "disk": 20,
        "swap": "",
        "OS-FLV-EXT-DATA:ephemeral": 0
    },
    "c1.xlarge": {
        "name": "c1.xlarge",
        "id": "c1.xlarge",
        "vcpus": 8,
        "ram": 28672,
        "disk": 20,
        "swap": "",
        "OS-FLV-EXT-DATA:ephemeral": 0
    }
}

if len(sys.argv) > 1:
    if sys.argv[1] in flavors:
        print json.dumps([flavors[sys.argv[1]]])
    else:
        print '[]'
else:
    print  json.dumps(flavors.values())
