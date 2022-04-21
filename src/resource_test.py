import json
import os
import pytest
import random
import tempfile
import datetime as dt
from datetime import date, datetime
from jsonschema import validate
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError

from app import app, db
from app import User, Sport, Court, Reservation


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# based on http://flask.pocoo.org/docs/1.0/testing/
@pytest.fixture
def client():
    db_fd, db_fname = tempfile.mkstemp()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_fname
    app.config["TESTING"] = True

    db.create_all()
    _populate_db()

    yield app.test_client()

    db.session.remove()
    os.close(db_fd)
    os.unlink(db_fname)


def _populate_db():
    for idx in range(1, 4):
        user = User(
            username=f"User{idx}",
            pwd=f"Testuser35352!{idx}",
            email=f"testuser{idx}@gmail.com"
        )
        sport = Sport(
            name=f"test-sport-{idx}"
        )
        db.session.add(sport)
        db.session.add(user)
        for i in range(1, 3):
            for j in range(0, 2):
                court = Court(
                    court_no=i, date=date.today() + dt.timedelta(days=j),
                    free_slots="9:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,"
                               "17:00,18:00,19:00,20:00,21:00,22:00")
                sport.courts.append(court)
                db.session.add(sport)

        reserve = Reservation(
            court_id=idx,
            start="15:00",
            end="16:00"
        )
        user.reservations.append(reserve)
        db.session.add(user)
    db.session.commit()


def _get_user_json(number=1):
    """
    Creates a valid JSON object to be used for POST tests for UserCollection.
    """

    return {"username": "User{}".format(number), "pwd": "Testu3434!", "email": "test.userx@gmail.com"}


def _get_user_item_json():
    """
    Creates a valid JSON object to be used for PUT test for UserItem.
    """

    return {"pwd": "Testu3434!", "email": "test.userx@gmail.com", "fname": "Bhim", "lname": "Nage"}


class TestUserCollection(object):
    """
    This class implements tests for each HTTP method in UserCollection
    resource.
    """

    RESOURCE_URL = "/api/users/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work. Also checks that all of the items from
        the DB popluation are present, and their controls.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 3
        for item in body:
            assert "username" in item
            assert "pwd" in item
            assert "email" in item


class TestUserItem(object):
    """
    This class implements tests for each HTTP method in UserItem
    resource.
    """

    RESOURCE_URL = "/api/users/User1/"
    DIFFERENT_USER_URL = "/api/users/User18/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work. Also checks that all of the items from
        the DB popluation are present, and their controls.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["username"] == "User1"
        assert body["email"] == "testuser1@gmail.com"

        resp = client.get(self.DIFFERENT_USER_URL)
        assert resp.status_code == 404

    def test_put(self, client):
        """
        Tests the PUT method. Checks all of the possible error codes, and also
        checks that a valid request receives a 204 response. Also tests that
        when name is changed, the sensor can be found from a its new URI.
        """

        valid = _get_user_item_json()

        # test with wrong content type
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

        # test with another user's name
        resp = client.put(self.DIFFERENT_USER_URL, json=valid)
        assert resp.status_code == 404

        # test with valid (only change model)
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204

    def test_delete(self, client):
        """
        Tests the DELETE method. Checks that a valid request receives 204
        response and that trying to GET the sensor afterwards results in 404.
        Also checks that trying to delete a sensor that doesn't exist results
        in 404.
        """

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 201

        # test with another user's name
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404


class TestSportCollection(object):
    """
    This class implements tests for each HTTP method in SportCollection
    resource.
    """

    RESOURCE_URL = "/api/sports/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work. Also checks that all of the items from
        the DB popluation are present, and their controls.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 3
        for item in body:
            assert "name" in item
            assert "courts" in item

    def test_post(self, client):
        """
        Tests the POST method. Checks all of the possible error codes, and
        also checks that a valid request receives a 201 response with a
        location header that leads into the newly created resource.
        """

        valid = {"name": "test-sport-4"}

        # test with wrong content type
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

        # test with valid and see that it exists afterward
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

        # send same data again for 409
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

        # remove model field for 400
        valid.pop("name")
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400


class TestSportItem(object):
    """
    This class implements tests for each HTTP method in SportItem
    resource.
    """

    RESOURCE_URL = "/api/sports/test-sport-1/"

    def test_delete(self, client):
        """
        Tests the DELETE method. Checks that a valid request receives 204
        response and that trying to GET the sensor afterwards results in 404.
        Also checks that trying to delete a sensor that doesn't exist results
        in 404.
        """

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 201

        # send delete request again for same sport
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404


class TestReservationCollection(object):
    """
    This class implements tests for each HTTP method in ReservationCollection
    resource.
    """

    RESOURCE_URL = "/api/reservations/User1/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work. Also checks that all of the items from
        the DB popluation are present, and their controls.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert len(body) == 1
        for item in body:
            assert "reservations" in item
            for val in body[item]:
                assert "book_id" in val
                assert "start" in val
                assert "end" in val
                assert "court_info" in val

    def test_post(self, client):
        """
        Tests the POST method. Checks all of the possible error codes, and
        also checks that a valid request receives a 201 response with a
        location header that leads into the newly created resource.
        """

        valid = {"court_id": 1, "start": "8:00", "end": "10:00"}

        # test with wrong content type
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

        # test with valid and see that it exists afterward
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201

        # send same data again for 409
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

        # remove model field for 400
        valid.pop("court_id")
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400


class TestReservationById(object):
    """
    This class implements tests for each HTTP method in ReservationById
    resource.
    """

    RESOURCE_URL = "/api/reservations/1/"

    def test_delete(self, client):
        """
        Tests the DELETE method. Checks that a valid request receives 204
        response and that trying to GET the sensor afterwards results in 404.
        Also checks that trying to delete a sensor that doesn't exist results
        in 404.
        """

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 201

        # send delete request again for same sport
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 409
