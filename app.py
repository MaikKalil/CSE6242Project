from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory
app = Flask(__name__)
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
       text_default = ''
       default_selected = {'zip_pref': '0', 'degree_pref': '0'}
       print('Request for landing page received with email=%s' % email)
       username = email.split('@')[0]  # split the email at "@" and return only the first part
       user_id = int(hashlib.sha256(email.lower().encode('utf-8')).hexdigest(), 16) % 10**8 # generate a unique numeric ID
       #Log email to user_id relationship to user table to later identify user rankings
       with sqlite3.connect(db_path) as conn:
           cur = conn.cursor()
           if pd.read_sql(f"SELECT * FROM user WHERE user_id ={user_id}", conn).empty:
               cur.execute(f"INSERT INTO user values('{email}',{user_id})")
       return render_template('landing.html', user =username, user_id=user_id,
                              text_default =text_default, default_selected=default_selected)
   else:
       print('Request for landing page received with no or invalid email -- redirecting')
       return redirect(url_for('index'))

@app.route('/landing/update', methods=['POST'])
#Helper function to calculate distance between universities and a given zip code.
# def inst_dist (lat,lon, inst_tbl):
#     idx = inst_tbl.apply(lambda x: great_circle((x["LATITUDE"], x["LONGITUDE"]), (lat, lon)).miles, axis=1)
#     return inst_tbl.loc[:, ['UNITID']].assign(DISTANCE_MI=idx)
def update():
    default_value = 'False'
    input_zip = request.form.get('zip')
    max_dist = request.form.get('zip_dist')
    default_selected = {'zip_pref': request.form.get('zip_pref'),
                        'degree_pref': request.form.get('degree_pref')}
    degree = request.form.get('degree')
    print(input_zip, max_dist, degree)
    return render_template('landing.html', default_value =default_value, default_selected= default_selected,
                           zip =input_zip, zip_dist=max_dist,
                           degree= degree)
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