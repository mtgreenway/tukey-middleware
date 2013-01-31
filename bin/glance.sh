source .venv/bin/activate
cd tukey_cli/
python tukey_server.py localhost 9292 -p 9292 -l /var/log/tukey/glance-api.log -d
