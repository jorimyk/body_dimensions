import random
import string

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from bd_api.config import Config

app = Flask(__name__)

# Secret key
app.secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))


# Flask_cors
from flask_cors import CORS, cross_origin

CORS(app)


# flask_limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address,
    default_limits = ['%s, %s, %s' % (Config.limit_per_day, Config.limit_per_hour, Config.limit_per_minute)])


# Init database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_DATABASE_URI'] = Config.db_url + Config.db_user + ':' + Config.db_password + '@' + Config.db_host + '/' + Config.db_name
db = SQLAlchemy(app)

import bd_api.users.models
import bd_api.users.measurements.models

db.create_all()


# Flask-Admin:
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

admin = Admin(app, name='Body dimensions', template_mode='bootstrap3')
# administrative views here
admin.add_view(ModelView(bd_api.users.models.User, db.session))
admin.add_view(ModelView(bd_api.users.measurements.models.Measurement, db.session))


# import views
import bd_api.users.views
import bd_api.users.measurements.views
