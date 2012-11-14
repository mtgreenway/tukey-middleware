source .venv/bin/activate
cd tukey_cli/
python tukeyServer.py localhost 9292 -p 9292 -l /var/log/tukey/glance-api.log
