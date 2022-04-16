import os
import pytest
import tempfile
import datetime as dt
from datetime import date
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError

import app
from app import User, Sport, Court, Reservation

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# based on http://flask.pocoo.org/docs/1.0/testing/
# we don't need a client for database testing, just the db handle
@pytest.fixture
def db_handle():
    db_fd, db_fname = tempfile.mkstemp()
    app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_fname
    app.app.config["TESTING"] = True

    with app.app.app_context():
        app.db.create_all()

    yield app.db

    app.db.session.remove()
    os.close(db_fd)
    os.unlink(db_fname)


def _get_user():
    return User(
        username="alpha21",
        pwd="Alp232312@",
        fname="Aarav",
        lname="Kapoor",
        phone="+358436547701",
        addr="KL Street",
        email="aarav.kapoor@gmail.com"
    )


def _get_sport():
    return Sport(
        name="badminton"
    )


def _get_court():
    return Court(
        court_no=1,
        sport_name="badminton",
        date=date.today() + dt.timedelta(days=1),
        free_slots="12:00,13:00,14:00,15:00,19:00"
    )


def _get_reservation():
    return Reservation(
        court_id=1,
        start="20:00",
        end="21:00"
    )


def test_create_instances(db_handle):
    """
    Tests that we can create one instance of each model and save them to the
    database using valid values for all columns. After creation, test that
    everything can be found from database, and that all relationships have been
    saved correctly.
    """

    # Create everything
    user = _get_user()
    sport = _get_sport()
    court = _get_court()
    reservation = _get_reservation()

    user.reservations.append(reservation)
    sport.courts.append(court)
    court.reservations.append(reservation)

    db_handle.session.add(user)
    db_handle.session.add(sport)
    db_handle.session.add(court)
    db_handle.session.add(reservation)
    db_handle.session.commit()

    # Check that everything exists
    assert User.query.count() == 1
    assert Sport.query.count() == 1
    assert Court.query.count() == 1
    assert Reservation.query.count() == 1
    db_user = User.query.first()
    db_sport = Sport.query.first()
    db_court = Court.query.first()
    db_reservation = Reservation.query.first()

    # Check all relationships (both sides)
    assert db_reservation in db_user.reservations
    assert db_court in db_sport.courts
    assert db_reservation in db_court.reservations


def test_user_columns(db_handle):
    """
    Tests user columns' restrictions. Username must be unique, and pwd and model
    must be mandatory.
    """

    user_1 = _get_user()
    user_2 = _get_user()
    db_handle.session.add(user_1)
    db_handle.session.add(user_2)
    with pytest.raises(IntegrityError):
        db_handle.session.commit()

    db_handle.session.rollback()

    user = _get_user()
    user.pwd = None
    db_handle.session.add(user)
    with pytest.raises(IntegrityError):
        db_handle.session.commit()

    db_handle.session.rollback()

    user = _get_user()
    user.email = None
    db_handle.session.add(user)
    with pytest.raises(IntegrityError):
        db_handle.session.commit()


def test_sport_columns(db_handle):
    """
    Tests sport columns' restrictions. Sport name must be unique
    """

    sport_1 = _get_sport()
    sport_2 = _get_sport()
    db_handle.session.add(sport_1)
    db_handle.session.add(sport_2)
    with pytest.raises(IntegrityError):
        db_handle.session.commit()

    db_handle.session.rollback()

