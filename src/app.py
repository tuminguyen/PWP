# This is where we define the APIs and redirect/call to display the corresponding HTML pages
import datetime
import os.path
import time
import click
from flask.cli import with_appcontext
import sqlalchemy.types
from flask import Flask, make_response
from flask import request, jsonify
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
from werkzeug.exceptions import NotFound
from werkzeug.routing import BaseConverter
from flasgger import Swagger, swag_from

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


# ... SQLAlchemy and Caching setup omitted from here
app.config["SWAGGER"] = {
    "title": "Book Your Court API",
    "openapi": "3.0.3",
    "uiversion": 3,
}
swagger = Swagger(app, template_file="doc/BYC_Open_API_Doc.yaml")


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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


class Sport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    courts = db.relationship("Court", backref='sport')

    def serialize(self, display_all=False):
        doc = {
            "id": self.id,
            "name": self.name,
            "courts": []
        }
        if display_all:
            for c in self.courts:
                doc["courts"].append(c.serialize(display_all=False))
        return doc


class Court(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport_name = db.Column(db.String(32), db.ForeignKey("sport.name"))
    court_no = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    free_slots = db.Column(db.String(200), nullable=True)
    # free_slots = db.Column(db.String(200), nullable=False)
    reservations = db.relationship("Reservation", backref="court")

    def serialize(self, display_all=False):
        doc = {
            "sport_name": self.sport_name,
            "court_no": self.court_no,
            "date": str(self.date)
        }
        if display_all:
            doc['id'] = self.id
            doc['free_slots'] = self.free_slots
        return doc


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), db.ForeignKey('user.username'))
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'))
    start = db.Column(db.String(10), nullable=False)
    end = db.Column(db.String(10), nullable=False)

    def serialize(self, short_form=False):
        doc = {
            "court_id": self.court_id,
            "start": self.start,
            "end": self.end,
        }
        # court = Court.query.filter(id=self.court_id).first()
        # doc["court_info"] = court.serialize(display_all=False)

        if not short_form:
            doc["username"] = self.username
            doc['id'] = self.id
        return doc


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


# edit delete needs to be added
class UserItem(Resource):
    def get(self, user):
        if request.method == 'GET':
            user = User.query(username=user).first()
            return user.serialize(display_all=True), 200
        return "GET method required", 405


class SportCollection(Resource):
    def get(self):
        if request.method == 'GET':
            res = [u.serialize(display_all=True) for u in Sport.query.all()]
            return res, 200
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


class SportItem(Resource):
    def delete(self, sport):
        if request.method != 'DELETE':
            return "DELETE method required", 405
        else:
            # print(sport)
            # sport_uri = api.url_for(SportItem, sport=sport)
            sport_list = [s.name.lower() for s in Sport.query.all()]
            if sport.name.lower() not in sport_list:
                return "Sport doesn't exists", 409
            else:
                Sport.query.filter(Sport.name == sport.name).delete()
                db.session.commit()
                return "Deleted successfully", 201


class CourtCollection(Resource):
    def post(self, sport):
        if request.method != 'POST':
            return "POST method required", 405
        data = request.get_json()
        # print(sport)
        sport_name = sport.name
        if data is not None:
            if 'court_no' and 'date' and 'free_slots' in data:
                court_no = data['court_no']
                court_date = data['date']
                court_date = to_date(court_date)
                free_slots = data['free_slots']
                sport_court_list = [[c.sport_name, c.court_no, c.date] for c in Court.query.all()]
                if [sport_name, court_no, court_date] in sport_court_list:
                    return "Data already exists", 409
                else:
                    court = Court(
                        sport_name=sport.name,
                        court_no=court_no,
                        date=court_date,
                        free_slots=free_slots
                    )
                    db.session.add(court)
                    db.session.commit()
                    return "Court added successfully", 201
            elif 'court_no' and 'date' in data:
                court_no = data['court_no']
                court_date = data['date']
                court_date = to_date(court_date)
                court_list = [[c.sport_name, c.court_no, c.date] for c in Court.query.all()]
                if [sport_name, court_no, court_date] in court_list:
                    return "Data already exists", 409
                else:
                    sport = Court(
                        sport_name=sport.name,
                        court_no=court_no,
                        date=court_date
                    )
                    db.session.add(sport)
                    db.session.commit()
                    return "", 201
            else:
                return "Incomplete request - missing fields", 400
        else:
            return "Request content type must be JSON", 415

    def get(self, sport):
        if request.method == 'GET':
            input_date = request.args['date']
            sport_name = sport.name
            courts_list = Court.query.filter(and_(Court.sport_name == sport_name,
                                                  Court.date == to_date(input_date))).all()
            value = {
                "sport": sport_name,
                "date": input_date,
                "courts": []
            }
            for c in courts_list:
                value["courts"].append({"court_no": c.court_no, "free_slots": c.free_slots})
            return value, 200
        return "GET method required", 405


class CourtItem(Resource):
    def delete(self, sport, court_no):
        if request.method != 'DELETE':
            return "DELETE method required", 405
        else:
            # print(sport)
            # sport_court_uri = api.url_for(CourtById, sport=sport, court_no=court_no)
            sport_list = [s.name.lower() for s in Sport.query.all()]
            if sport.name.lower() not in sport_list:
                return "Sport doesn't exists", 409
            else:
                court_no_list = [c.court_no for c in Court.query.filter(and_(Court.sport_name == sport.name)).all()]
                if court_no not in court_no_list:
                    return "Court number for this sport doesn't exists", 409
                else:
                    Court.query.filter(and_(Court.sport_name == sport.name, Court.court_no == court_no)).delete()
                    db.session.commit()
                    return "Deleted successfully", 201

    def put(self, sport, court_no):
        if request.method != 'PUT':
            return "PUT method required", 405
        data = request.get_json()
        sport_name = sport.name
        input_date = data['date']
        start_time = data['start']
        end_time = data['end']
        court = Court.query.filter(and_(Court.sport_name == sport_name, Court.date == to_date(input_date),
                                        Court.court_no == court_no)).first()
        slot = court.free_slots
        if start_time not in slot:
            return "Time slot not available for the date", 409
        else:
            start = start_time.replace(":00", "")
            end = end_time.replace(":00", "")
            time_range = int(end) - int(start)
            str_to_replace = ""
            for t in range(time_range):
                str_to_replace = str_to_replace + str(int(start) + t) + ":00,"
            slot_updated = slot.replace(str_to_replace, "")
            court.free_slots = slot_updated
            db.session.commit()
            return "Updated free slots for the record", 204


class ReservationCollection(Resource):
    def get(self, username):
        if request.method == 'GET':
            # res = [r.serialize(short_form=False)
            #        for r in Reservation.query.filter(Reservation.username == username).all()]
            reservation_list = Reservation.query.filter(Reservation.username == username).all()
            value = {
                 "reservations": []
            }
            for r in reservation_list:
                value["reservations"].append({"court_id": r.court_id, "start": r.start, "end": r.end})

            return value, 200
        return "GET method required", 405

    def post(self):
        pass


class ReservationById(Resource):
    def delete(self):
        pass


class SportConverter(BaseConverter):

    def to_python(self, sport_name):
        db_sport = Sport.query.filter_by(name=sport_name).first()
        if db_sport is None:
            raise NotFound
        return db_sport

    def to_url(self, db_sport):
        return db_sport.name


@app.route("/", methods=['POST', 'GET'])
def index():
    return render_template('index.html')


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
                court_no=i, date=date(2022, 3, 17 + j),
                free_slots="9:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,"
                           "17:00,18:00,19:00,20:00,21:00,22:00")
            badminton.courts.append(bad_court)
            db.session.add(badminton)

    # 4 courts for tennis
    for i in range(1, 5):
        for j in range(1, 8):
            t_court = Court(
                court_no=i, date=date(2022, 3, 17 + j),
                free_slots="9:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,"
                           "17:00,18:00,19:00,20:00,21:00,22:00")
            tennis.courts.append(t_court)
            db.session.add(tennis)

    # 3 courts for tennis
    for i in range(1, 4):
        for j in range(1, 8):
            bb_court = Court(
                court_no=i, date=date(2022, 3, 17 + j),
                free_slots="11:00,12:00,13:00,14:00,15:00,16:00,"
                           "17:00,18:00,19:00,20:00,21:00,22:00")
            basketball.courts.append(bb_court)
            db.session.add(basketball)

    user1 = User(
        username='van_mj',
        pwd='vAn123456@',
        email='vandana.mj24@gmail.com'
    )
    db.session.add(user1)
    user2 = User(
        username='van_mj2',
        pwd='vAnT123456@',
        email='simmi.vandana@gmail.com'
    )
    db.session.add(user2)

    reserve1 = Reservation(
        court_id=2,
        start="15:00",
        end="16:00"
    )
    user1.reservations.append(reserve1)
    reserve2 = Reservation(
        court_id=3,
        start="11:00",
        end="13:00"
    )
    user2.reservations.append(reserve2)
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()


def to_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d").date()

#
# @click.command("init-db")
# @with_appcontext
# def init_db_cmd():
#     if not os.path.exists("../src/*.db"):
#         db.create_all()
#
#
# @click.command("delete-db")
# @with_appcontext
# def delete_db_cmd():
#     db.drop_all()
#
#
# @click.command("populate-db")
# @with_appcontext
# def populate_db_cmd():
#     populate_db()


# app.cli.add_command(init_db_cmd)
# app.cli.add_command(delete_db_cmd)
# app.cli.add_command(populate_db_cmd)


# db.create_all()
# populate_db()


api.add_resource(UserCollection, "/api/users/")
api.add_resource(SportCollection, "/api/sports/")
app.url_map.converters["sport"] = SportConverter
api.add_resource(SportItem, "/api/sports/<sport:sport>/")
api.add_resource(CourtCollection, '/api/sports/<sport:sport>/courts/')
api.add_resource(CourtItem, "/api/sports/<sport:sport>/courts/<int:court_no>/")
api.add_resource(ReservationCollection, "/api/reservations/<username>/")
