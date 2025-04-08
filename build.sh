#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate

# Create superuser if it doesn't exist (optional)
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(email='daijikuriakose50@gmail.com').exists():
    User.objects.create_superuser('daijikuriakose50@gmail.com', 'daijikuriakose50@gmail.com', 'your-password')
"