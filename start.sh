#!/bin/bash
# start.sh

# Collecte les fichiers statiques
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Lancer le serveur
echo "Starting Gunicorn..."
gunicorn SchoolManagement.wsgi:application --bind 0.0.0.0:$PORT
