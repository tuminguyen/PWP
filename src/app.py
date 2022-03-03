# This is where we define the APIs and redirect/call to display the corresponding HTML pages
import datetime

import sqlalchemy.types
from flask import Flask, make_response
from flask import request, jsonify
from flask import jsonify
from flask import render_template
from flask_restful import Resource
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_restful import Api
from sqlalchemy.engine import Engine
from sqlalchemy import event

app = Flask(__name__)
api = Api(app)
# config db
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../db/byc.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
# config mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'bookyourcourt.info@gmail.com'
app.config['MAIL_PASSWORD'] = 'NguyenYadav@199x'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Sport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    courts = db.relationship("Court", backref='sport')

    def serialize(self):
        doc = {
            "id": self.id,
            "name": self.name,
            "courts": []
        }
        for c in self.courts:
            doc["courts"].append(c.serialize(display_all=True))
        return doc


class Court(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey("sport.id"))
    court_no = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    free_slots = db.Column(db.String(200), nullable=False)
    reservations = db.relationship("Reservation", backref="court")

    def serialize(self, display_all=False):
        doc = {
            "date": self.date,
            "court_no": self.court_no
        }
        sport = Sport.query(id=self.sport_id).first()
        doc["sport"] = sport.name
        if display_all:
            doc['id'] = self.id
            doc['free_slots'] = self.free_slots
        return doc


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

    def serialize(self, display_all=False):
        doc = {
            "username": self.username,
            "first_name": self.fname,
            "last_name": self.lname,
            "phone": self.phone,
            "email": self.email
        }
        if display_all:
            doc["address"] = self.addr
            doc["reservations"] = []
            for r in self.reservations:
                doc["reservations"].append(r.serialize(display_all=False))
        return doc


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), db.ForeignKey('user.username'))
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'))
    start = db.Column(db.String(10), nullable=False)
    end = db.Column(db.String(10), nullable=False)

    def serialize(self, short_form=False):
        doc = {
            "start": self.fname,
            "end": self.lname,
        }
        court = Court.query(id=self.court_id).first()
        doc["court_info"] = court.serialize(display_all=False)
        if not short_form:
            doc["username"] = self.username
            doc['id'] = self.id
        return doc


def populate_db():
    passs


@app.route("/", methods=['POST', 'GET'])
def index():
    return render_template('index.html')


class UserCollection(Resource):
    def get(self):
        if request.method == 'GET':
            res = [u.serialize(display_all=False) for u in User.query.all()]
            return res, 200
        return "GET method required", 405

    def post(self):
        if request.method != 'POST':
            return "POST method required", 405
        id = request.form.get('sign-name')
        pwd = request.form.get('sign-pwd')
        email = request.form.get('sign-email')
        print(id, pwd, email)
        user_list_id = [u.username for u in User.query.all()]
        user_list_email = [u.email for u in User.query.all()]
        if id in user_list_id:
            return "Username already used by others", 409
        elif email in user_list_email:
            return "Email has been registered by other user. Please use another.", 409
        else:
            user = User(
                username=id,
                pwd=pwd,
                fname='',
                lname='',
                phone='',
                addr='',
                email=email,
                avatar=''
            )
            db.session.add(user)
            db.session.commit()
            msg = Message('BYC - Confirm your new account',
                          sender='bookyourcourt.info@gmail.com',
                          recipients=[email])
            msg.html = render_template('mail_confirm_account.html')
            mail.send(msg)
            return make_response(render_template('after_signup.html'), 200)


class UserItem(Resource):
    def get(self, user):
        if request.method == 'GET':
            user = User.query(username=user).first()
            return user.serialize(display_all=True), 200
        return "GET method required", 405


class SportCollection(Resource):
    def get(self, id):
        if request.method == 'GET':
            user = Sport.query(id=id).first()

            return user.serialize(display_all=True), 200
        return "GET method required", 405

    def post(self):
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
api.add_resource(UserCollection, "/api/users/")
app.run(debug=True)
