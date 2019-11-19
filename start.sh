if [[ "$DEBUG" == "yes" ]]
then
  python server.py
else
  gunicorn server:app -w 1 --log-file -
fi
