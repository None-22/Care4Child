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
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')"

# Populate vaccines and directorates automatically
python populate_db_vaccines.py
python add_ibb_dirs.py
python add_other_dirs.py

echo "Build process finished!"
