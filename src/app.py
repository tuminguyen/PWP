# This is where we define the APIs and redirect/call to display the corresponding HTML pages
import sqlalchemy.types
from flask import Flask
from flask import request, jsonify
from flask import jsonify
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy import event

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../db/byc.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Sport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    courts = db.relationship("Court", backref='sport')


class Court(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey("sport.id"))
    court_no = db.Column(db.Integer, nullable=False)
    free_slots = db.Column(db.String(200), nullable=False)
    reservations = db.relationship("Reservation", backref="court")


class User(db.Model):
    username = db.Column(db.String(64), primary_key=True)
    pwd = db.Column(db.String(64), nullable=False)
    fname = db.Column(db.String(64))
    lname = db.Column(db.String(64))
    phone = db.Column(db.String(64))
    addr = db.Column(db.String(64))
    email = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(128))
    reservations = db.relationship("Reservation", backref="user")


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), db.ForeignKey('user.username'))
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'))
    start = db.Column(db.String(10), nullable=False)
    end = db.Column(db.String(10), nullable=False)


def populate_db():
    passs


@app.route("/", methods=['POST', 'GET'])
def index():
    return render_template('index.html')


@app.route("/sport/add/", methods=['POST'])
def add_sport():
    if request.method != 'POST':
        return "POST method required", 405
    data = request.get_json()
    if data is not None:
        if 'name' in data:
            name = data['name']
            prod_list_id = [s.name.lower() for s in Sport.query.all()]
            if name.lower() in prod_list_id:
                return "Sport already exists", 409
            else:
                sport = Sport(
                    name=name,
                )
                db.session.add(sport)
                db.session.commit()
                return "", 201
        else:
            return "Incomplete request - missing fields", 400
    else:
        return "Request content type must be JSON", 415


db.create_all()
# app.run(debug=True)
