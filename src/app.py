# This is where we define the APIs and redirect/call to display the corresponding HTML pages
import datetime as dt
import os.path
import time
import click
import requests
import json
from flask.cli import with_appcontext
import sqlalchemy.types
from flask import Flask, make_response, redirect
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
            "pwd": self.pwd,
            "first_name": self.fname,
            "last_name": self.lname,
            "phone": self.phone,
            "email": self.email,
            "address": self.addr
        }
        if display_all:
            doc["reservations"] = []
            for r in self.reservations:
                doc["reservations"].append(r.serialize(short_form=False))
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
            return "Username or email already exists", 409
        elif email in user_list_email:
            return "Username or email already exists", 409
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
            return make_response(render_template('after_signup.html'), 201)


class UserItem(Resource):
    def get(self, user):
        if request.method == 'GET':
            user_list = [u.username for u in User.query.all()]
            if user.username not in user_list:
                return "User not found", 404
            user = User.query.filter(User.username == user.username).first()
            return user.serialize(display_all=True), 200
        return "GET method required", 405

    def delete(self, user):
        if request.method != 'DELETE':
            return "DELETE method required", 405
        else:
            user_list = [u.username for u in User.query.all()]
            if user.username not in user_list:
                return "User not found", 404
            else:
                db_user = User.query.filter_by(username=user.username).first()
                db.session.delete(db_user)
                db.session.commit()
                return "Deleted successfully", 201

    def put(self, user):
        if request.method != 'PUT':
            return "PUT method required", 405
        data = request.get_json()
        if data is not None:
            user_list = [u.username for u in User.query.all()]
            if user.username not in user_list:
                return "User doesn't exists", 404
            else:
                u = User.query.filter(User.username == user.username).first()
                if 'pwd' in data:
                    pwd = data['pwd']
                    u.pwd = pwd
                if 'fname' in data:
                    fname = data['fname']
                    u.fname = fname
                if 'lname' in data:
                    lname = data['lname']
                    u.lname = lname
                if 'addr' in data:
                    addr = data['addr']
                    u.addr = addr
                if 'phone' in data:
                    phone = data['phone']
                    u.phone = phone
                db.session.commit()
                return "Updated user profile", 204
        else:
            return "Request content type must be JSON", 415


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
                    return "New sport successfully added", 201
            else:
                return "Incomplete request - missing fields", 400
        else:
            return "Request content type must be JSON", 415


class SportItem(Resource):
    def delete(self, sport):
        if request.method != 'DELETE':
            return "DELETE method required", 405
        else:
            sport_list = [s.name.lower() for s in Sport.query.all()]
            if sport.name.lower() not in sport_list:
                return "Sport not found", 404
            else:
                db_sport = Sport.query.filter_by(name=sport.name).first()
                db.session.delete(db_sport)
                db.session.commit()
                return "Deleted successfully", 201


class CourtCollection(Resource):
    def post(self, sport):
        if request.method != 'POST':
            return "POST method required", 405
        data = request.get_json()
        sport_name = sport.name
        if data is not None:
            if 'court_no' in data and 'date' in data and 'free_slots' in data:
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
            elif 'court_no' in data and 'date' in data:
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
            sport_list = [u.name for u in Sport.query.all()]
            if sport_name in sport_list:
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
            else:
                return "Sport not found", 404
        return "GET method required", 405


class CourtItem(Resource):
    def delete(self, sport, court_no):
        if request.method != 'DELETE':
            return "DELETE method required", 405
        else:
            sport_list = [s.name.lower() for s in Sport.query.all()]
            if sport.name.lower() not in sport_list:
                return "Sport or court not found", 404
            else:
                court_no_list = [c.court_no for c in Court.query.filter(and_(Court.sport_name == sport.name)).all()]
                if court_no not in court_no_list:
                    return "Sport or court not found", 404
                else:
                    Court.query.filter(and_(Court.sport_name == sport.name, Court.court_no == court_no)).delete()
                    db.session.commit()
                    return "Deleted successfully", 201

    def put(self, sport, court_no):
        if request.method != 'PUT':
            return "PUT method required", 405
        data = request.get_json()
        sport_name = sport.name
        if data is not None:
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
        else:
            return "Request content type must be JSON", 415


class ReservationCollection(Resource):
    def get(self, username):
        if request.method == 'GET':
            reservation_list = Reservation.query.filter(Reservation.username == username).all()

            value = {
                "reservations": []
            }
            for r in reservation_list:
                today_date = date.today()
                current_time = datetime.now().strftime("%H:%M")
                current_time = dt.datetime.strptime(current_time, '%H:%M').time()
                court = Court.query.filter(Court.id == r.court_id).first()
                r_start = dt.datetime.strptime(r.start, '%H:%M').time()
                if court.date == today_date:
                    if r_start >= current_time:
                        value["reservations"].append({"book_id": r.id,
                                                      "start": r.start,
                                                      "end": r.end,
                                                      "court_info": {"court_no": court.court_no,
                                                                     "date": str(court.date),
                                                                     "sport": court.sport_name}
                                                      })
                else:
                    value["reservations"].append({"book_id": r.id,
                                                  "start": r.start,
                                                  "end": r.end,
                                                  "court_info": {"court_no": court.court_no,
                                                                 "date": str(court.date),
                                                                 "sport": court.sport_name}
                                                  })

            return value, 200
        return "GET method required", 405

    def post(self, username):
        if request.method != 'POST':
            return "POST method required", 405
        data = request.get_json()
        if data is not None:
            if 'court_id' in data and 'start' in data and 'end' in data:
                court_id = data['court_id']
                start = data['start']
                end = data['end']
                sport_court_list = [[r.court_id, r.start, r.end]
                                    for r in Reservation.query.filter(Reservation.username == username).all()]
                if [court_id, start, end] in sport_court_list:
                    return "Data already exists", 409
                else:
                    reserve = Reservation(
                        username=username,
                        court_id=court_id,
                        start=start,
                        end=end
                    )
                    db.session.add(reserve)
                    db.session.commit()
                    return "Reservation added successfully", 201
            else:
                return "Incomplete request - missing fields", 400
        else:
            return "Request content type must be JSON", 415


class ReservationById(Resource):
    def delete(self, book_id):
        if request.method != 'DELETE':
            return "DELETE method required", 405
        else:
            book_id_list = [r.id for r in Reservation.query.all()]
            if book_id not in book_id_list:
                return "Booking Id doesn't exists", 409
            else:
                db_reserve = Reservation.query.filter_by(id=book_id).first()
                print(db_reserve)
                print(db_reserve.start)
                start = db_reserve.start
                db_court = Court.query.filter(Court.id == db_reserve.court_id).first()
                slot = db_court.free_slots
                print(db_court)
                print(slot)
                new_int_slots = [int(x.split(":")[0]) for x in slot.split(",")]
                new_int_slots.append(int(start.split(":")[0]))
                new_int_slots.sort()
                new_str_slots = [str(x) + ':00' for x in new_int_slots]
                updated_slots = ','.join(new_str_slots)
                db_court.free_slots = updated_slots
                db.session.delete(db_reserve)
                db.session.commit()
                return "Deleted successfully", 201


class SportConverter(BaseConverter):

    def to_python(self, sport_name):
        db_sport = Sport.query.filter_by(name=sport_name).first()
        if db_sport is None:
            raise NotFound
        return db_sport

    def to_url(self, db_sport):
        return db_sport.name


class UserConverter(BaseConverter):

    def to_python(self, user_name):
        db_user = User.query.filter_by(username=user_name).first()
        if db_user is None:
            raise NotFound
        return db_user

    def to_url(self, db_user):
        return db_user.username


@app.route("/", methods=['POST', 'GET'])
def index():
    return render_template('index.html')


@app.route("/booking/booking-front", methods=['POST'])
def login():
    uname = request.form.get('log-name')
    try:
        user = User.query.filter_by(username=uname).first()
        if user.pwd == request.form.get('log-pwd'):
            input_date = date.today().strftime("%Y-%m-%d")
            res_content, is_free_dict = retrieve_schedule("badminton", input_date)
            return render_template("schedule.html", query=res_content, slots_in_dict=is_free_dict,
                                   sport_name="badminton", n_court=len(res_content["courts"]),
                                   input_date=input_date, username=uname)
        else:
            return "Wrong username or password. Please try again!", 409
    except Exception as e:
        return str(e), 500


@app.route("/<username>/booking/<sport>/_/<input_date>", methods=['GET'])
def sport_retrieve(sport, username, input_date):
    if input_date == 'today':
        input_date = date.today().strftime("%Y-%m-%d")
    res_content, is_free_dict = retrieve_schedule(sport, input_date)
    return render_template("schedule.html", query=res_content, slots_in_dict=is_free_dict, sport_name=sport,
                           n_court=len(res_content["courts"]), input_date=input_date, username=username)


@app.route("/<username>/confirm-booking", methods=['POST'])
def confirm_booking(username):
    time_slot = request.form.get('slot').split("-")
    start = time_slot[0]
    end = time_slot[1]
    court = time_slot[-1]
    sport_name = court[0]
    if sport_name == 'B':
        sport_name = "Badminton"
    elif sport_name == 'T':
        sport_name = "Tennis"
    else:
        sport_name = 'Basketball'
    input_date = request.form.get('input-date')
    day_name = datetime.strptime(input_date, "%Y-%m-%d").strftime("%A")
    return render_template('booking_check_confirm.html', start=start, end=end, court=court[-1],
                           sport=sport_name, date=input_date, day=day_name, username=username)


@app.route("/<username>/reservations/", methods=['GET', 'POST'])
def booking_history(username):
    if request.method == 'POST':
        data = request.form
        day_info = data["day-date"]
        date_ = day_info.split(" ")[-1]
        start = data["start"]
        end = data["end"]
        court = data["court"]
        sport = court.split('/')[0][:-1].lower()
        court_id = Court.query.filter(
            and_(Court.sport_name == sport, Court.date == to_date(date_), Court.court_no == court[-1])).first().id
        payload = {'start': start, 'end': end, 'court_id': court_id}
        requests.post("http://127.0.0.1:5000/api/reservations/{}/".format(username), json=payload)
        requests.put("http://127.0.0.1:5000/api/sports/{}/courts/{}".format(sport, court[-1]),
                     json={"date": date_, "start": start, "end": end})
        email = User.query.filter_by(username=username).first().email
        msg = Message('BYC - Booking Information',
                      sender='bookyourcourt.info@gmail.com',
                      recipients=[email])
        msg.html = render_template('mail_booking_info.html', username=username, day=day_info,
                                   sport=sport.capitalize(), court=court[-1], start=start, end=end)
        mail.send(msg)
    query = requests.get("http://127.0.0.1:5000/api/reservations/{}/".format(username))
    content = json.loads(query.content.decode())
    reservations = content['reservations']
    hist = []
    for r in reservations:
        play_date = r['court_info']['date']
        date_info = datetime.strptime(r['court_info']['date'], "%Y-%m-%d").strftime("%A") + " " + play_date
        time_info = r['start'] + ' - ' + r['end']
        sport = r['court_info']['sport']
        court_info = sport.upper() + ' / ' + sport.upper() + " " + str(r['court_info']['court_no'])
        book_id = r['book_id']
        hist.append({'id': book_id, 'court_info': court_info, 'time': time_info, 'date': date_info})
    return render_template("own_reservations.html", booking=hist, username=username)


@app.route("/<username>/reservations/delete/<booking_id>", methods=['POST'])
def delete_booking(booking_id, username):
    requests.delete("http://127.0.0.1:5000/api/reservations/{}/".format(booking_id))
    return redirect("/{}/reservations/".format(username))


@app.route("/<username>/profile/", methods=['GET', 'POST'])
def load_profile(username):
    if request.method == 'POST':
        data = request.form
        fname = data['fname']
        lname = data['lname']
        phone = data['phone']
        addr = data['addr']
        payload = {"fname": fname, "lname": lname, 'phone': phone, 'addr': addr}
        requests.put("http://127.0.0.1:5000/api/users/{}/".format(username), json=payload)
    query = requests.get("http://127.0.0.1:5000/api/users/{}/".format(username))
    content = json.loads(query.content.decode())
    first = content['first_name']
    last = content['last_name']
    uphone = content['phone']
    uaddr = content['address']
    if first is None:
        first = ""
    if last is None:
        last = ""
    if uphone is None:
        uphone = ""
    if uaddr is None:
        uaddr = ""
    return render_template("edit_profile.html", username=username, fname=first, lname=last,
                           phone=uphone, addr=uaddr, email=content['email'])


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


def retrieve_schedule(sport_name, input_date):
    query = requests.get("http://127.0.0.1:5000/api/sports/{}/courts/?date={}".format(sport_name, input_date))
    content = json.loads(query.content.decode())
    full = "8:00,9:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00,19:00,20:00,21:00,22:00".split(",")
    is_free_dict = {}
    for idx in range(len(full) - 1):
        is_free_dict[full[idx] + "-" + full[idx + 1]] = [True] * len(content['courts'])
    for idx in range(len(content["courts"])):
        slot_split = content['courts'][idx]["free_slots"].split(",")
        booked = [x for x in full if x not in slot_split]
        for b in booked:
            b_split = int(b.split(":")[0])
            book_key = "{}:00-{}:00".format(b_split, b_split + 1)
            is_free_dict[book_key][idx] = False
    return content, is_free_dict


def populate_db():
    """
    Auto generate sport, courts and users
    :return:
    """
    badminton = Sport(name='badminton')
    db.session.add(badminton)
    tennis = Sport(name="tennis")
    db.session.add(tennis)
    basketball = Sport(name="basketball")
    db.session.add(basketball)
    current_time = int(datetime.now().strftime("%H:%M")[0:2])
    # if 7:30 then drop :30, doing 7+2 to not allow booking for 7 or 8
    # (8 also bcz if 7:59 then also not allow to book for 8, anyway we can also add 1 instead of 2)
    start = current_time + 1
    end = 22
    time_range = end - start
    # 20+2 is 22 so for 22 cannot book so booking only allowed for current_time<=20
    if current_time <= 20:
        free_slot_today = ""
        for t in range(0, time_range + 1):
            free_slot_today = free_slot_today + str(start + t) + ":00"
            if t != time_range:
                free_slot_today = free_slot_today + ","
        for i in range(1, 7):
            bad_court_today = Court(
                court_no=i,
                date=date.today(),
                free_slots=free_slot_today
            )
            badminton.courts.append(bad_court_today)
            db.session.add(badminton)
        for i in range(1, 5):
            t_court_today = Court(
                court_no=i,
                date=date.today(),
                free_slots=free_slot_today
            )
            tennis.courts.append(t_court_today)
            db.session.add(tennis)
        for i in range(1, 4):
            bb_court_today = Court(
                court_no=i,
                date=date.today(),
                free_slots=free_slot_today
            )
            basketball.courts.append(bb_court_today)
            db.session.add(basketball)
    else:
        for i in range(1, 7):
            bad_court_today = Court(
                court_no=i,
                date=date.today(),
                free_slots=""
            )
            badminton.courts.append(bad_court_today)
            db.session.add(badminton)

        for i in range(1, 5):
            t_court_today = Court(
                court_no=i,
                date=date.today(),
                free_slots=""
            )
            tennis.courts.append(t_court_today)
            db.session.add(tennis)

        for i in range(1, 4):
            bb_court_today = Court(
                court_no=i,
                date=date.today(),
                free_slots=""
            )
            basketball.courts.append(bb_court_today)
            db.session.add(basketball)
    # remaining dates 6 courts for badminton
    for i in range(1, 7):
        for j in range(1, 8):
            bad_court = Court(
                court_no=i, date=date.today() + dt.timedelta(days=j),
                free_slots="9:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,"
                           "17:00,18:00,19:00,20:00,21:00,22:00")
            badminton.courts.append(bad_court)
            db.session.add(badminton)
    # remaining dates 4 courts for tennis
    for i in range(1, 5):
        for j in range(1, 8):
            t_court = Court(
                court_no=i, date=date.today() + dt.timedelta(days=j),
                free_slots="9:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,"
                           "17:00,18:00,19:00,20:00,21:00,22:00")
            tennis.courts.append(t_court)
            db.session.add(tennis)
    # remaining dates 3 courts for bb
    for i in range(1, 4):
        for j in range(1, 8):
            bb_court = Court(
                court_no=i, date=date.today() + dt.timedelta(days=j),
                free_slots="9:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,"
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
        username='mj2',
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
    reserve_u1_2 = Reservation(
        court_id=4,
        start="14:00",
        end="15:00"
    )
    user2.reservations.append(reserve2)
    user2.reservations.append(reserve_u1_2)
    db.session.commit()


def to_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d").date()


@click.command("init-db")
@with_appcontext
def init_db_cmd():
    db.create_all()


@click.command("delete-db")
@with_appcontext
def delete_db_cmd():
    db.drop_all()


@click.command("populate-db")
@with_appcontext
def populate_db_cmd():
    populate_db()


app.cli.add_command(init_db_cmd)
app.cli.add_command(delete_db_cmd)
app.cli.add_command(populate_db_cmd)

api.add_resource(UserCollection, "/api/users/")
api.add_resource(SportCollection, "/api/sports/")
app.url_map.converters["sport"] = SportConverter
app.url_map.converters["user"] = UserConverter
api.add_resource(SportItem, "/api/sports/<sport:sport>/")
api.add_resource(UserItem, "/api/users/<user:user>/")
api.add_resource(CourtCollection, '/api/sports/<sport:sport>/courts/')
api.add_resource(CourtItem, "/api/sports/<sport:sport>/courts/<int:court_no>/")
api.add_resource(ReservationCollection, "/api/reservations/<username>/")
api.add_resource(ReservationById, "/api/reservations/<int:book_id>/")
