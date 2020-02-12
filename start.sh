if [[ "$DEBUG" == "yes" ]]
then
  python server.py
else
  gunicorn server:app -w 3 --log-file -
fi
