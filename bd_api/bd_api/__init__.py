import random
import string

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Flask-Admin:
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from bd_api.config import Config

app = Flask(__name__)

# Init database
app.config['SQLALCHEMY_DATABASE_URI'] = Config.db_url + Config.db_user + ':' + Config.db_password + '@' + Config.db_host + '/' + Config.db_name
db = SQLAlchemy(app)

import bd_api.users.models
import bd_api.users.measurements.models

db.create_all()


import bd_api.users.views
import bd_api.users.measurements.views


# Secret key for Flask Admin
app.secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))

# Flask-Admin:
admin = Admin(app, name='Body dimensions', template_mode='bootstrap3')
# administrative views here
admin.add_view(ModelView(bd_api.users.models.User, db.session))
admin.add_view(ModelView(bd_api.users.measurements.models.Measurement, db.session))
