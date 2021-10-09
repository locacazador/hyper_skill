import sys
import os
import requests
from typing import Dict, Any

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_restful import marshal, fields

# Init flask and db
app = Flask(__name__)
API_KEY = os.environ.get('WEATHER_API_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
app.secret_key = os.urandom(24)
db = SQLAlchemy(app)


BASE_URL = 'https://api.openweathermap.org/data/2.5/weather?q='


class City(db.Model):
    """
    City model

    Contains: id
              name - full name of city
              day_state - state of the day. Enum of {evening-morning, day, night}
              temperatue - current temperature in celciyn
              state - current weather state
    """

    __tablename__ = 'city'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    day_state = db.Column(db.String(15), nullable=False)
    temperature = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String(15), nullable=False)


fields = {
    'id': fields.Integer,
    'name': fields.String,
    'temperature': fields.Integer,
    'day_state': fields.String,
    'state': fields.String
}

db.create_all()


def get_day_state(response: Dict[str, Any]) -> str:
    """
    Get state of day by timezone.
    If time between sunrise and sunrise + 4 hours then "evening-morning"
    If time between sunrise + 4 hours and sunset then "day"
    If time between sunset and sunrise then "night"

    :param response: json from weather API
    :Return state of the day: Night, Day or Evening-morning
    """

    n_hours = 4
    shift_for_morning_in_sec = n_hours * 60 * 60
    if response['sys']['sunrise'] < response['dt'] <= response['sys']['sunrise'] + shift_for_morning_in_sec:
        return 'evening-morning'
    elif response['sys']['sunrise'] + shift_for_morning_in_sec < response['dt'] < response['sys']['sunset']:
        return 'day'
    else:
        return 'night'


@app.route('/')
def index():
    """
    Default index page, rendering index.html
    """

    all_data = City.query.all()
    cities = marshal(all_data, fields)
    args = dict()
    for city in cities:
        args[city["name"]] = {'state': city["state"],
                              'degrees': city['temperature'],
                              'state_day': city['day_state'],
                              'id': city['id']}
    return render_template('index.html', args=args)


@app.route('/add', methods=['POST'])
def add_city():
    """
    Add city to database @City
    Expect city_name from input form
    """

    city_name = request.form['city_name']
    db_city = City.query.filter_by(name=city_name).first()

    if db_city:
        flash('The city has already been added to the list!')
    else:
        response = requests.get(BASE_URL + f'{city_name}&appid={API_KEY}&units=metric').json()
        if int(response['cod']) == 404:
            flash("The city doesn't exist!")
        else:
            day_state = get_day_state(response)
            db.session.add(City(name=city_name,
                                temperature=int(response['main']['temp']),
                                day_state=day_state,
                                state=response['weather'][0]['main']))
            db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete/<city_id>', methods=['GET'])
def delete_city(city_id):
    """
    Delete city from database @City

    :param city_id: id of city in database to delete
    """
    city = City.query.filter_by(id=city_id).first()
    if city:
        db.session.delete(city)
        db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg_host, arg_port = sys.argv[1].split(':')
        app.run(host=arg_host, port=arg_port)
    else:
        app.run()
