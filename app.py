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
@app.route('/')
def index():
   print('Request for index page received')
   return render_template('index.html')

@app.route('/landing', methods=['POST'])
def login():
   email = request.form.get('email')
   if email and '@' in email:
       default_selected = {'states': [''], 'zip_pref': '10',
                           'degree':'3', 'degree_pref': '10',
                           'fields': '', 'field_pref': '10',
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
           states = list(pd.read_sql("SELECT DISTINCT STABBR FROM inst ORDER BY 1", conn).STABBR)
           states.insert(0, '')
           fields = list(pd.read_sql("SELECT DISTINCT CIPDESC FROM fields ORDER BY 1", conn).CIPDESC)
           fields.insert(0, '')
           religs = list(pd.read_sql("SELECT DISTINCT NAME FROM relig ORDER BY 1", conn).NAME)
           religs.insert(0, '')
           sizes = ['','Small','Medium','Large']
           types = ['', 'Public', 'Private Nonprofit', 'Private For-Profit']
           urban = ['', 'City', 'Suburban', 'Town', 'Rural']
           missions =['','Men-Only College','Women-Only College','Alaska Native Native Hawaiian Serving Institution',\
               'Asian American Native American Pacific Islander-Serving Institution',\
               'Hispanic-Serving Institution','Historically Black College and University',\
               'Native American Non-Tribal Institution','Predominantly Black Institution','Tribal College and University']

       return render_template('landing.html', user =username, user_id=user_id, default_selected=default_selected,
                              states =states, fields =fields, sizes =sizes, types =types, urban=urban,
                              missions =missions, religs=religs)
   else:
       print('Request for landing page received with no or invalid email -- redirecting')
       return redirect(url_for('index'))

@app.route('/landing/update', methods=['GET', 'POST'])
#Helper function to calculate distance between universities and a given zip code.
# def inst_dist (lat,lon, inst_tbl):
#     idx = inst_tbl.apply(lambda x: great_circle((x["LATITUDE"], x["LONGITUDE"]), (lat, lon)).miles, axis=1)
#     return inst_tbl.loc[:, ['UNITID']].assign(DISTANCE_MI=idx)
def update():
    #Re-establish variable lists that could not be added to session due to size (limit 4 kb)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        states = list(pd.read_sql("SELECT DISTINCT STABBR FROM inst ORDER BY 1", conn).STABBR)
        states.insert(0, '')
        fields = list(pd.read_sql("SELECT DISTINCT CIPDESC FROM fields ORDER BY 1", conn).CIPDESC)
        fields.insert(0, '')
        religs = list(pd.read_sql("SELECT DISTINCT NAME FROM relig ORDER BY 1", conn).NAME)
        religs.insert(0, '')
    user = session.get('user')
    sat_math = request.form.get('sat_math')
    sat_cr = request.form.get('sat_cr')
    act = request.form.get('act')
    input_zip = request.form.get('zip')
    max_dist = request.form.get('zip_dist')
    max_cost = request.form.get('max_cost')
    salary = request.form.get('salary')
    ar = request.form.get('ar')
    gr = request.form.get('gr')
    sizes = ['', 'Small', 'Medium', 'Large']
    types = ['', 'Public', 'Private Nonprofit', 'Private For-Profit']
    urban = ['', 'City', 'Suburban', 'Town', 'Rural']
    missions = ['', 'Men-Only College', 'Women-Only College', 'Alaska Native Native Hawaiian Serving Institution', \
               'Asian American Native American Pacific Islander-Serving Institution', \
               'Hispanic-Serving Institution', 'Historically Black College and University', \
               'Native American Non-Tribal Institution', 'Predominantly Black Institution',
               'Tribal College and University']

    default_selected = {'states': request.form.getlist('states'),
                        'zip_pref': request.form.get('zip_pref'),
                        'degree': request.form.get('degree'),
                        'degree_pref': request.form.get('degree_pref'),
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

    print(default_selected['sizes'], input_zip, max_dist, max_cost, salary)
    return render_template('landing.html', user =user, default_selected= default_selected,
                           states=states, fields = fields, zip =input_zip, zip_dist=max_dist, max_cost =max_cost,
                           sat_math =sat_math, sat_cr = sat_cr, act = act, salary = salary, ar= ar, gr =gr,
                           sizes = sizes, types=types, urban =urban, missions=missions, religs=religs)
    # with sqlite3.connect(db_path) as conn:
    #     geo = pd.read_sql("SELECT * FROM geo", conn)
    #     inst = pd.read_sql("SELECT UNITID, LATITUDE, LONGITUDE FROM inst", conn)
    #     lat = float(list(geo[geo['zip'] == input_zip]['lat'])[0])
    #     lon = float(list(geo[geo['zip'] == input_zip]['lng'])[0])
    #     print(f"lat, lon: ({lat}, {lon})")
    #     zip_all_dist = inst_dist(lat, lon, inst)

# def features_dict(feature1, feature2, feature3):
#     featuresDict = {}
#     featuresDict['feature1']= 'OMENRUP_PELL_NFT_POOLED_SUPP'
#     featuresDict['feature2']= 'OMENRYP_PELL_FT_POOLED_SUPP'
#     featuresDict['feature3']= 'OMENRAP_PELL_FT_POOLED_SUPP'
#     return featuresDict


if __name__ == '__main__':
   app.run()