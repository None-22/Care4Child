#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing requirements..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Seeding the database with Admin, Vaccines, and Governorates..."
# Create superuser if it doesn't exist
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='Sarovic').exists() or User.objects.create_superuser('Sarovic', 'sarovic@care4child.com', 'sarovic1922')"

# Populate static data
python populate_db_vaccines.py
python populate_governorates.py
python populate_directorates.py

echo "Build process finished!"
