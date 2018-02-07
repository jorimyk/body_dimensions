import os

class Config:
    # database
    db_url = os.environ['DB_URL']
    db_host = os.environ['DB_HOST']
    db_user = os.environ['DB_USER']
    db_password = os.environ['DB_PASSWORD']
    db_name = os.environ['DB_NAME']

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask_limiter
    # default limits:
    limit_per_day = "1000 per day"
    limit_per_hour = "600 per hour"
    limit_per_minute = "60 per minute"

    #  itsdangerous
    expiration = 600 # Access token expiration time in seconds

    # admin
    admin_password = os.environ['ADMIN_PASSWORD']
    admin_email = os.environ['ADMIN_EMAIL']
