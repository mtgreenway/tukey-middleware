import os

from subprocess import Popen, PIPE

def apply_iptables_rules():

    iptables = '/sbin/iptables %s'

    rules = [ 
        '-t nat -N tukey_auth_proxy',
        '-t nat -A OUTPUT -j tukey_auth_proxy',
        '-t nat -A tukey_auth_proxy -p tcp -m tcp -s %(host)s -d %(host)s --dport 35357 -j REDIRECT --to-ports %(port)s'
    ]

    # this is brittle where do we get these from??
    # maybe webob can tell us what port and host?
    run_time_settings = {'host': '127.0.0.1', 'port': '5000'}

    for rule in rules:

        process = Popen(iptables % rule % run_time_settings, stdout=PIPE,
            shell=True)
        exit_code = os.waitpid(process.pid, 0)
        print process.communicate()
        print exit_code

if __name__ == "__main__":
    apply_iptables_rules()
