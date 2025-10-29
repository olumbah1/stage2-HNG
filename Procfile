web: gunicorn core.wsgi:application --log-file -
release: python manage.py migrate
worker: python manage.py refresh_countries