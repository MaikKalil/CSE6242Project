from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)
app.secret_key = 'secret_key'
import sqlite3
import pandas as pd
import numpy as np
from pandasql import sqldf
from geopy.distance import great_circle
import hashlib
import os
db_path = os.path.join(os.path.dirname(__file__), 'cs.db')  # get the absolute path of the database file
import pickle

class DatabaseHandler:
    @staticmethod
    def get_table(name):
        if name == 'sizes':
            tbl = ['', 'Small', 'Medium', 'Large']
        elif name == 'types':
            tbl = ['', 'Public', 'Private Nonprofit', 'Private For-Profit']
        elif name == 'urban':
            tbl = ['', 'City', 'Suburban', 'Town', 'Rural']
        elif name == 'missions':
            tbl = ['', 'Men-Only College', 'Women-Only College', 'Alaska Native Native Hawaiian Serving Institution', \
                'Asian American Native American Pacific Islander-Serving Institution', \
                'Hispanic-Serving Institution', 'Historically Black College and University', \
                'Native American Non-Tribal Institution', 'Predominantly Black Institution',
                'Tribal College and University']
        elif name == 'states':
            with sqlite3.connect(db_path) as conn:
                tbl = list(pd.read_sql("SELECT DISTINCT STABBR FROM inst ORDER BY 1", conn).STABBR)
                tbl.insert(0, '')
        elif name == 'fields':
            with sqlite3.connect(db_path) as conn:
                tbl = list(pd.read_sql("SELECT DISTINCT CIPDESC FROM fields ORDER BY 1", conn).CIPDESC)
                tbl.insert(0, '')
        elif name == 'religs':
            with sqlite3.connect(db_path) as conn:
                tbl = list(pd.read_sql("SELECT DISTINCT NAME FROM relig ORDER BY 1", conn).NAME)
                tbl.insert(0, '')
        return tbl

@app.route('/')
def index():
   print('Request for index page received')
   return render_template('index.html')

@app.route('/landing', methods=['POST'])
def login():
   email = request.form.get('email')
   if email and '@' in email:
       default_selected = {'states': [''], 'zip_pref': '10',
                           'degree':'3', 'fields': '', 'field_pref': '10',
                           'hi':'3', 'cost_pref': '10', 'sal_pref': '10',
                           'ar_pref':'10', 'gr_pref':'10',
                           'sizes': '', 'size_pref':'10',
                           'types':'', 'type_pref':'10',
                           'urban':'', 'urban_pref':'10',
                           'missions':[''], 'mission_pref':'10',
                           'religs':[''], 'relig_pref':'10', 'limit_match':'6'}
       print('Request for landing page received with email=%s' % email)
       username = email.split('@')[0]  # split the email at "@" and return only the first part
       user_id = int(hashlib.sha256(email.lower().encode('utf-8')).hexdigest(), 16) % 10**8 # generate a unique numeric ID
       session['user'] = username
       #Log email to user_id relationship to user table to later identify user rankings
       with sqlite3.connect(db_path) as conn:
           cur = conn.cursor()
           if pd.read_sql(f"SELECT * FROM user WHERE user_id ={user_id}", conn).empty:
               cur.execute(f"INSERT INTO user values('{email}',{user_id})")
           states = DatabaseHandler.get_table('states')
           fields = DatabaseHandler.get_table('fields')
           religs = DatabaseHandler.get_table('religs')
           sizes = DatabaseHandler.get_table('sizes')
           types = DatabaseHandler.get_table('types')
           urban = DatabaseHandler.get_table('urban')
           missions = DatabaseHandler.get_table('missions')

       return render_template('landing.html', user =username, user_id=user_id, default_selected=default_selected,
                              states =states, fields =fields, sizes =sizes, types =types, urban=urban,
                              missions =missions, religs=religs)
   else:
       print('Request for landing page received with no or invalid email -- redirecting')
       return redirect(url_for('index'))

@app.route('/landing/update', methods=['GET', 'POST'])
def update():
    user = session.get('user')
    states = DatabaseHandler.get_table('states')
    fields = DatabaseHandler.get_table('fields')
    religs = DatabaseHandler.get_table('religs')
    sizes = DatabaseHandler.get_table('sizes')
    types = DatabaseHandler.get_table('types')
    urban = DatabaseHandler.get_table('urban')
    missions = DatabaseHandler.get_table('missions')

    sat_math = request.form.get('sat_math')
    sat_cr = request.form.get('sat_cr')
    act = request.form.get('act')
    input_zip = request.form.get('zip')
    max_dist = request.form.get('zip_dist')
    max_cost = request.form.get('max_cost')
    salary = request.form.get('salary')
    ar = request.form.get('ar')
    gr = request.form.get('gr')

    default_selected = {'states': request.form.getlist('states'),
                        'zip_pref': request.form.get('zip_pref'),
                        'degree': request.form.get('degree'),
                        'fields': request.form.get('fields'),
                        'field_pref': request.form.get('field_pref'),
                        'hi': request.form.get('hi'),
                        'cost_pref': request.form.get('cost_pref'),
                        'sal_pref': request.form.get('sal_pref'),
                        'ar_pref': request.form.get('ar_pref'),
                        'gr_pref': request.form.get('gr_pref'),
                        'sizes': request.form.getlist('sizes'),
                        'size_pref': request.form.get('size_pref'),
                        'types': request.form.getlist('types'),
                        'type_pref': request.form.get('type_pref'),
                        'urban': request.form.getlist('urban'),
                        'urban_pref': request.form.get('urban_pref'),
                        'missions': request.form.getlist('missions'),
                        'mission_pref': request.form.get('mission_pref'),
                        'religs': request.form.getlist('religs'),
                        'relig_pref': request.form.get('relig_pref'),
                        'limit_match': request.form.get('limit_match')
                        }
    #Create nested dictionary for ranking algo
    data = {'user': user,
            'limit_match': default_selected['limit_match'],
            'degree': {'pref':10,'val': default_selected['degree'],'multi': 'N'},
            'sat_math': {'pref':10,'val': sat_math,'multi': 'N'},
            'sat_cr': {'pref': 10, 'val': sat_cr, 'multi': 'N'},
            'act': {'pref': 10, 'val': act, 'multi': 'N'},
            'states': {'pref': 10, 'val': default_selected['states'], 'multi': 'Y'},
            'input_zip': {'pref': default_selected['zip_pref'], 'val': [input_zip, max_dist], 'multi': 'N'},
            'field': {'pref': default_selected['field_pref'], 'val': default_selected['fields'], 'multi': 'N'},
            'cost': {'pref': default_selected['cost_pref'], 'val': [max_cost, default_selected['hi']], 'multi': 'N'},
            'salary': {'pref': default_selected['sal_pref'], 'val': salary, 'multi': 'N'},
            'ar': {'pref': default_selected['ar_pref'], 'val': ar, 'multi': 'N'},
            'gr': {'pref': default_selected['gr_pref'], 'val': gr, 'multi': 'N'},
            'sizes': {'pref': default_selected['size_pref'], 'val': default_selected['sizes'], 'multi': 'Y'},
            'types': {'pref': default_selected['type_pref'], 'val': default_selected['types'], 'multi': 'Y'},
            'urban': {'pref': default_selected['urban_pref'], 'val': default_selected['urban'], 'multi': 'Y'},
            'missions': {'pref': default_selected['mission_pref'], 'val': default_selected['missions'], 'multi': 'Y'},
            'religs': {'pref': default_selected['relig_pref'], 'val': default_selected['religs'], 'multi': 'Y'}
            }

    filename = os.path.join(os.path.dirname(db_path), "data.pickle")
    with open(filename, "wb") as file:
        pickle.dump(data, file)

    return render_template('landing.html', user =user, default_selected= default_selected,
                           states=states, fields = fields, zip =input_zip, zip_dist=max_dist, max_cost =max_cost,
                           sat_math =sat_math, sat_cr = sat_cr, act = act, salary = salary, ar= ar, gr =gr,
                           sizes = sizes, types=types, urban =urban, missions=missions, religs=religs)


if __name__ == '__main__':
   app.run()