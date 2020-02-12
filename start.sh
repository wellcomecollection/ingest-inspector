if [[ "$DEBUG" == "yes" ]]
then
  python server.py
else
  gunicorn server:app -w 4 --log-file -
fi
