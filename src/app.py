# This is where we define the APIs and redirect/call to display the corresponding HTML pages
import datetime
import time

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
from datetime import date, datetime
from sqlalchemy import and_, or_

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
    name = db.Column(db.String(32), nullable=False, unique=True)
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
    sport_name = db.Column(db.String(32), db.ForeignKey("sport.name"))
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
            "start": self.start,
            "end": self.end,
        }
        court = Court.query(id=self.court_id).first()
        doc["court_info"] = court.serialize(display_all=False)

        if not short_form:
            doc["username"] = self.username
            doc['id'] = self.id
        return doc


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
                email=email
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


@app.route("/login", methods=['POST'])
def login():
    uname = request.form.get('log-name')
    try:
        user = User.query.filter_by(username=uname).first()
        if user.pwd == request.form.get('log-pwd'):
            return render_template("booking_check_confirm.html")
        else:
            return "Wrong username or password. Please try again!", 409
    except Exception as e:
        return str(e), 500


@app.route("/forgot-password", methods=['GET'])
def forgot_pwd():
    return render_template('forgot_pwd.html')


@app.route("/resend-password", methods=['POST'])
def resend_pwd():
    email = request.form.get('log-email')
    try:
        user = User.query.filter_by(email=email).first()
        msg = Message('BYC - Restore your password',
                      sender='bookyourcourt.info@gmail.com',
                      recipients=[email])
        msg.html = render_template('mail_forgot_pwd.html', pwd=user.pwd)
        mail.send(msg)
        return render_template('index.html')
    except Exception as e:
        return str(e), 500


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


class SportByName(Resource):
    def get(self):
        pass

    def delete(self):
        pass


class SportByCourt(Resource):
    def get(self):
        pass


def populate_db():
    """
    Auto generate sport and courts
    :return:
    """
    badminton = Sport(name='badminton')
    db.session.add(badminton)
    tennis = Sport(name="tennis")
    db.session.add(tennis)
    basketball = Sport(name="basketball")
    db.session.add(basketball)

    # add courts
    # 6 courts for badminton
    for i in range(1, 7):
        for j in range(1, 8):
            bad_court = Court(
                court_no=i, date=date(2022, 3, 17 + j), free_slots="9-10-11-12-13-14-15-16-17-18-19-20-21-22-23")
            badminton.courts.append(bad_court)
            db.session.add(badminton)

    # 4 courts for tennis
    for i in range(1, 5):
        for j in range(1, 8):
            t_court = Court(
                court_no=i, date=date(2022, 3, 17 + j), free_slots="7-8-11-12-13-14-15-16-17-18-19-20-21-22-23")
            tennis.courts.append(t_court)
            db.session.add(tennis)

    # 3 courts for tennis
    for i in range(1, 4):
        for j in range(1, 8):
            bb_court = Court(
                court_no=i, date=date(2022, 3, 17 + j), free_slots="7-8-9-10-11-12-13-14-15-16-17-18-19-20-21-22-23")
            basketball.courts.append(bb_court)
            db.session.add(basketball)
    db.session.commit()


class CourtsById(Resource):
    def get(self):
        pass

    def put(self):
        pass

    def delete(self):
        pass


class CourtsByInputDateCollection(Resource):
    # get free_slots for sport_id and date,
    # returns slot_list: contains slots for each court of chosen sport & date
    def get(self):
        if request.method == 'GET':
            input_date = request.args['input_date']
            sport_id = request.args['sport_name']
            input_date = datetime.strptime(input_date, '%d/%m/%Y').date()
            courts_list = Court.query.filter(and_(Court.sport_id == int(sport_id), Court.date == input_date)).all()
            slots_list = []
            for i in range(len(courts_list)):
                slots_list.append(courts_list[i].free_slots)
                print(courts_list[i].free_slots)
            return {sport_id: slots_list}, 200
        # serialize(self, display_all=True)
        return "GET method required", 405


class CourtByInputDateItem(Resource):
    # after selection, update the free_slots in the db for specific court_no of chosen sport and date.
    def put(self):
        if request.method != 'PUT':
            return "PUT method required", 405
        data = request.get_json()
        sport_id = data['sport_id']
        input_date = data['input_date']
        input_date = datetime.strptime(input_date, '%d/%m/%Y').date()
        court_no = data['court_no']
        chosen_time = data['chosen_time']
        court = Court.query.filter(and_(Court.sport_id == sport_id, Court.date == input_date,
                                        Court.court_no == court_no)).first()
        slot = court.free_slots
        print(slot)
        slot_updated = slot.replace(chosen_time + "-", "")
        court.free_slots = slot_updated
        print(slot_updated)
        db.session.commit()
        print(court.free_slots)
        return "Success", 204


class ReservationCollection(Resource):
    # get all reservations for view history of logged-in user
    def get(self, user):
        if request.method == 'GET':
            book_user_list = Reservation.query(username=user).all()
            return book_user_list.serialize(display_all=True), 200
        return "GET method required", 405

    def post(self):
        pass


class ReservationById(Resource):
    def get(self):
        pass

    def delete(self):
        pass


db.create_all()
populate_db()
api.add_resource(UserCollection, "/api/users/")
api.add_resource(CourtsByInputDateCollection, "/api/sports/")
