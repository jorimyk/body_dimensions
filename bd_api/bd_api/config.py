import os

class Config:
    db_url = os.environ['DB_URL']
    db_host = os.environ['DB_HOST']
    db_user = os.environ['DB_USER']
    db_password = os.environ['DB_PASSWORD']
    db_name = os.environ['DB_NAME']

    #SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
