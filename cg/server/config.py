# -*- coding: utf-8 -*-
import os

# flask
SECRET_KEY = 'unsafe!!!'
TEMPLATES_AUTO_RELOAD = True

# sqlalchemy
SQLALCHEMY_DATABASE_URI = os.environ['CG_SQL_DATABASE_URI']
SQLALCHEMY_POOL_RECYCLE = 7200
SQLALCHEMY_TRACK_MODIFICATIONS = 'FLASK_DEBUG' in os.environ

# server
CG_ENABLE_ADMIN = ('FLASK_DEBUG' in os.environ) or (os.environ.get('CG_ENABLE_ADMIN') == '1')
