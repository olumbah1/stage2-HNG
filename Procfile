web: gunicorn core.wsgi:application --log-file - --access-logfile - --workers 4
release: python manage.py migrate && python manage.py collectstatic --noinput