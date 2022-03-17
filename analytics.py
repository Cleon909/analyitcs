from base64 import b64decode
import datetime
import json
import os
from urllib.parse import parse_qsl, urlparse
from flask_sqlalchemy import SQLAlchemy
import pymysql

from flask import Flask, Response, abort, request
from peewee import *

# 1 pixel GIF, base64-encoded.
BEACON = b64decode('R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==')

# Simple JavaScript which will be included and executed on the client-side.
JAVASCRIPT = """(function(){
    var d=document,i=new Image,e=encodeURIComponent;
    i.src='%s/a.gif?url='+e(d.location.href)+'&ref='+e(d.referrer)+'&t='+e(d.title);
    })()""".replace('\n', '')


# create database
con = pymysql.connect(host='db', user='root', password='todo')
con.cursor().execute('CREATE DATABASE analytics')
con.close() 

# Flask application settings.
DEBUG = True
SECRET_KEY = 'sadfujhsdf'  # 

app = Flask(__name__)
app.config.from_object(__name__)

db = MySQLDatabase('analytics',host='db', user='root', password='todo')

class JSONField(TextField):
    """Store JSON data in a TextField."""
    def python_value(self, value):
        if value is not None:
            return json.loads(value)

    def db_value(self, value):
        if value is not None:
            return json.dumps(value)

class PageView(Model):
    domain = CharField()
    url = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now, index=True)
    title = TextField(default='')
    ip = CharField(default='')
    referrer = TextField(default='')
    headers = JSONField()
    params = JSONField()

    @classmethod
    def create_from_request(cls):
        parsed = urlparse(request.args['url'])
        params = dict(parse_qsl(parsed.query))

        return PageView.create(
            domain=parsed.netloc,
            url=parsed.path,
            title=request.args.get('t') or '',
            ip=request.headers.get('X-Forwarded-For', request.remote_addr),
            referrer=request.args.get('ref') or '',
            headers=dict(request.headers),
            params=params)

    class Meta:
        database = db


@app.route('/a.gif')
def analyze():
    if not request.args.get('url'):
        abort(404)

    with db.transaction():
        PageView.create_from_request()

    response = Response(app.config['BEACON'], mimetype='image/gif')
    response.headers['Cache-Control'] = 'private, no-cache'
    return response

@app.route('/a.js')
def script():
     return Response(
        app.config['JAVASCRIPT'] % (app.config['DOMAIN']),
        mimetype='text/javascript')

@app.errorhandler(404)
def not_found(e):
    return Response('Not found.')

if __name__ == '__main__':
    db.connect()
    db.create_tables([PageView], safe=True)
    app.run()