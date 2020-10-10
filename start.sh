pip3 install -r requirements.txt

if [[ "$DEBUG" == "yes" ]]
then
  python3 server.py
else
  gunicorn server:app -w 4 --log-file -
fi
