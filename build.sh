#!/usr/bin/env bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input --clear

# Run migrations
python manage.py migrate --no-input

# Create superuser if none exists
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@nacos.com', 'Datapwa@1')" | python manage.py shell

echo "✅ Build completed successfully!"