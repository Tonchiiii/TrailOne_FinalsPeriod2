# TrailOne Project

A Django-based shipment and inventory management system for container truck companies.

## Features

- User authentication (custom login system)
- Account page with role-based data
- Dashboard for shipment tracking
- Password reset and session management

## Installation

Clone the repository:
   git clone https://github.com/yourusername/trailone.git
   cd trailone
   
Create and activate a virtual environment:
  python -m venv env
  source env/bin/activate  # On Windows: env\Scripts\activate

Install dependencies:
  pip install -r requirements.txt

Run migrations:
  python manage.py makemigrations
  python manage.py migrate

Start the server:
  python manage.py runserver
  
Access the app:
  Visit http://localhost:8000/ in your browser.
