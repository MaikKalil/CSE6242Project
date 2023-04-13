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
        elif name == 'relig':
            with sqlite3.connect(db_path) as conn:
                tbl = pd.read_sql("SELECT * FROM relig", conn)
        elif name == 'inst':
            with sqlite3.connect(db_path) as conn:
                tbl = pd.read_sql("""SELECT UNITID, INSTNM, ZIP, CITY, STABBR, LATITUDE, LONGITUDE, TUITIONFEE_IN, TUITIONFEE_OUT,
                                                    cast(NPT41_PUB as int) NPT41_PUB, cast(NPT42_PUB as int) NPT42_PUB, cast(NPT43_PUB as int) NPT43_PUB, 
                                                    cast(NPT44_PUB as int) NPT44_PUB, cast(NPT45_PUB as int) NPT45_PUB, cast(NPT4_PUB as int) NPT4_PUB, 
                                                    cast(NPT4_PRIV as int) NPT4_PRIV, cast(NPT41_PRIV as int) NPT41_PRIV, cast(NPT42_PRIV as int) NPT42_PRIV, 
                                                    cast(NPT43_PRIV as int) NPT43_PRIV, cast(NPT44_PRIV as int) NPT44_PRIV, cast(NPT45_PRIV as int) NPT45_PRIV, 
                                                    cast(MD_EARN_WNE_P10 as int) MD_EARN_WNE_P10,
                                                    cast(SATMT25 as int) SATMT25, cast(SATMT75 as int) SATMT75, cast(SATVR25 as int) SATVR25, 
                                                    cast(SATVR75 as int) SATVR75, cast(ACTCM25 as int) ACTCM25, cast(ACTCM75 as int) ACTCM75,
                                                    ADM_RATE, C150_4, C150_L4, cast(UGDS as int) UGDS, 
                                                    case when CONTROL=1 then 'Public' when CONTROL=2 then 'Private Nonprofit' else 'Private For-Profit' end CONTROL, 
                                                    case when LOCALE like '1%' then 'City' when LOCALE like '2%' then 'Suburban' when LOCALE like '3%' then 'Town' else 'Rural' end LOCALE, 
                                                    cast(RELAFFIL as int) RELAFFIL, cast(HBCU as int) HBCU, cast(PBI as int) PBI, cast(ANNHI as int) ANNHI, cast(TRIBAL as int) TRIBAL, 
                                                    cast(AANAPII as int) AANAPII, cast(HSI as int) HSI, cast(NANTI as int) NANTI, cast(MENONLY as int) MENONLY, cast(WOMENONLY as int) WOMENONLY
                                             FROM inst""", conn)
        elif name == 'field':
            with sqlite3.connect(db_path) as conn:
                tbl = pd.read_sql(
                    "SELECT UNITID, CREDLEV, CIPDESC, cast(EARN_NE_MDN_3YR as int) EARN_NE_MDN_3YR FROM fields", conn)
        elif name == 'geo':
            with sqlite3.connect(db_path) as conn:
                tbl = pd.read_sql("SELECT * FROM geo", conn)

        return tbl

class rankHandler:
    @staticmethod
    def determine_constraint_type(data_dict):
        hard_list = ['degree', 'states']  # these features are always hard
        soft_list = ['sat_math', 'sat_cr', 'act', 'input_zip', 'field', 'cost', 'salary', 'ar', 'gr', 'sizes', 'types',
                     'urban', 'missions',
                     'religs']  # these features can be hard if user sets them at 10. Need to check
        full_list = ['degree', 'sat_math', 'sat_cr', 'act', 'states', 'input_zip', 'field', 'cost', 'salary', 'ar',
                     'gr', 'sizes', 'types', 'urban', 'missions', 'religs']
        # Create empty list to store features to be removed from soft_list
        to_remove = []
        for feat in soft_list:
            # Determine which soft contraints to add to hard list if any
            if (int(data_dict[feat]['pref']) == 10) and (
                    (data_dict[feat]['val'] != ['']) or (data_dict[feat]['val'] != '') or (
                    data_dict[feat]['val'] != '0')):
                hard_list.append(feat)
                to_remove.append(feat)
            # Determine which soft contraints to remove if no input was provided
            if (data_dict[feat]['val'] == ['']) or (data_dict[feat]['val'] == '') or (data_dict[feat]['val'] == '0'):
                if feat not in to_remove:
                    to_remove.append(feat)
            if feat == 'cost':
                if (data_dict[feat]['val'][0] == '0') and (feat not in to_remove):
                    to_remove.append(feat)
            if feat == 'input_zip':
                if (data_dict[feat]['val'][1] == '0') and (feat not in to_remove):
                    to_remove.append(feat)

        # Remove features from soft_list that were added to to_remove list
        for feat in to_remove:
            soft_list.remove(feat)

        to_remove = []
        for feat in hard_list:
            # Determine which hard contraints to remove if no input was provided
            if (data_dict[feat]['val'] == ['']) or (data_dict[feat]['val'] == '') or (data_dict[feat]['val'] == '0'):
                to_remove.append(feat)
            if feat == 'cost':
                if data_dict[feat]['val'][0] == '0':
                    to_remove.append(feat)
            if feat == 'input_zip':
                if data_dict[feat]['val'][1] == '0':
                    to_remove.append(feat)

        for feat in to_remove:
            hard_list.remove(feat)

        return full_list, hard_list, soft_list

    @staticmethod
    def calc_dist(input_zip):
        geo = DatabaseHandler.get_table('geo')
        inst = DatabaseHandler.get_table('inst')[['UNITID', 'LATITUDE', 'LONGITUDE']]
        # Get lat lon of input zip
        lat = float(list(geo[geo['zip'] == input_zip]['lat'])[0])
        lon = float(list(geo[geo['zip'] == input_zip]['lng'])[0])
        # Get distance between each inst and input zip
        idx = inst.apply(lambda x: great_circle((x["LATITUDE"], x["LONGITUDE"]), (lat, lon)).miles, axis=1)
        return inst.loc[:, ['UNITID']].assign(DISTANCE_MI=idx)

    @staticmethod
    def apply_constraints(data_dict, full_list):
        filtered = DatabaseHandler.get_table('inst')
        for constraint in full_list:
            if constraint == 'input_zip':
                if int(data_dict[constraint]['val'][1]) != 0:
                    inst_dist = rankHandler.calc_dist(data_dict[constraint]['val'][0])
                    filtered = filtered.merge(inst_dist, on='UNITID')
                    filtered['input_zip'] = (filtered['DISTANCE_MI'] <= int(data_dict[constraint]['val'][1])).astype(
                        int)
                else:
                    filtered['input_zip'] = 1
                    filtered['DISTANCE_MI'] = None
            elif constraint == 'states':
                if data_dict[constraint]['val'] != ['']:
                    filtered['states'] = (filtered['STABBR'].isin(data_dict[constraint]['val'])).astype(int)
                else:
                    filtered['states'] = 1
            elif constraint == 'cost':
                if data_dict['types']['val'] == 'Public':
                    if data_dict[constraint]['val'][1] == '1':  # if HI 0-$30K
                        filtered = filtered.rename(columns={'NPT41_PUB': 'NPT'})  # To identify the column to display
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    elif data_dict[constraint]['val'][1] == '2':  # if HI >$30K <=$48K
                        filtered = filtered.rename(columns={'NPT42_PUB': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    elif data_dict[constraint]['val'][1] == '3':  # if HI >$48K <=$75K
                        filtered = filtered.rename(columns={'NPT43_PUB': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    elif data_dict[constraint]['val'][1] == '4':  # if HI >$75K <=$110K
                        filtered = filtered.rename(columns={'NPT44_PUB': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    else:  # HI >$110k
                        filtered = filtered.rename(columns={'NPT45_PUB': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                else:  # Private
                    if data_dict[constraint]['val'][1] == '1':  # if HI 0-$30K
                        filtered = filtered.rename(columns={'NPT41_PRIV': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    elif data_dict[constraint]['val'][1] == '2':  # if HI >$30K <=$48K
                        filtered = filtered.rename(columns={'NPT42_PRIV': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    elif data_dict[constraint]['val'][1] == '3':  # if HI >$48K <=$75K
                        filtered = filtered.rename(columns={'NPT43_PRIV': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    elif data_dict[constraint]['val'][1] == '4':  # if HI >$75K <=$110K
                        filtered = filtered.rename(columns={'NPT44_PRIV': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
                    else:  # HI >$110k
                        filtered = filtered.rename(columns={'NPT45_PRIV': 'NPT'})
                        if int(data_dict[constraint]['val'][0]) != 0:
                            filtered['cost'] = (filtered['NPT'] <= int(data_dict[constraint]['val'][0])).astype(int)
                        else:
                            filtered['cost'] = 1
            elif constraint == 'field':
                if data_dict[constraint]['val'] != '':  # Ignore filter on Field if none specified by user
                    # First merge on degree/field constraint to get valid UNITIDs or universities that offer major
                    fields_tbl = DatabaseHandler.get_table('field')[['UNITID', 'CIPDESC']].drop_duplicates()
                    offered = fields_tbl[fields_tbl['CIPDESC'] == data_dict[constraint]['val']]
                    filtered['field'] = filtered['UNITID'].isin(offered['UNITID']).astype(int)
                else:
                    filtered['field'] = 1
            elif constraint == 'degree':
                # First merge on degree/field constraint to get valid UNITIDs or universities that offer degree
                degree_tbl = DatabaseHandler.get_table('field')[['UNITID', 'CREDLEV']].drop_duplicates()
                offered = degree_tbl[degree_tbl['CREDLEV'] == data_dict[constraint]['val']]
                filtered['degree'] = filtered['UNITID'].isin(offered['UNITID']).astype(int)
            elif constraint == 'sat_math':
                filtered['sat_math'] = (filtered['SATMT25'] <= int(data_dict[constraint]['val'])).astype(int)
            elif constraint == 'sat_cr':
                filtered['sat_cr'] = (filtered['SATVR25'] <= int(data_dict[constraint]['val'])).astype(int)
            elif constraint == 'act':
                filtered['act'] = (filtered['ACTCM25'] <= int(data_dict[constraint]['val'])).astype(int)
            elif constraint == 'salary':
                if int(data_dict[constraint]['val']) != 0:
                    # 3yr Median earnings is dependent on degree and major
                    if data_dict['field'] != '':
                        earn_tbl = DatabaseHandler.get_table('field')
                        reported = earn_tbl[(earn_tbl['CIPDESC'] == data_dict['field']['val'])
                                            & (earn_tbl['CREDLEV'] == data_dict['degree']['val'])
                                            & (earn_tbl['EARN_NE_MDN_3YR'] >= int(data_dict[constraint]['val']))]
                        filtered = filtered.merge(reported[['UNITID', 'EARN_NE_MDN_3YR']], on='UNITID', how='left')
                        filtered['salary3'] = filtered['UNITID'].isin(reported['UNITID']).astype(int)
                        filtered['salary10'] = (
                                    filtered['MD_EARN_WNE_P10'] >= int(data_dict[constraint]['val'])).astype(int)
                    else:
                        filtered['EARN_NE_MDN_3YR'] = None
                        filtered['salary3'] = 0
                        filtered['salary10'] = (
                                    filtered['MD_EARN_WNE_P10'] >= int(data_dict[constraint]['val'])).astype(int)
                else:
                    filtered['EARN_NE_MDN_3YR'] = None
                    filtered['salary3'] = 0
                    filtered['salary10'] = 1
            elif constraint == 'ar':
                if int(data_dict[constraint]['val']) != 0:
                    filtered['ar'] = (filtered['ADM_RATE'] >= int(data_dict[constraint]['val'])).astype(int)
                else:
                    filtered['ar'] = 1
            elif constraint == 'gr':
                if int(data_dict[constraint]['val']) != 0:
                    if int(data_dict['degree']['val']) >= 3:
                        filtered['gr'] = (filtered['C150_4'] >= int(data_dict[constraint]['val'])).astype(int)
                        filtered = filtered.rename(columns={'C150_4': 'GRAD_RATE'})
                    else:
                        filtered['gr'] = (filtered['C150_L4'] >= int(data_dict[constraint]['val'])).astype(int)
                        filtered = filtered.rename(columns={'C150_L4': 'GRAD_RATE'})
                else:
                    filtered['gr'] = 1
                    filtered = filtered.rename(columns={'C150_4': 'GRAD_RATE'})
            elif constraint == 'sizes':
                if data_dict[constraint]['val'] != ['']:
                    filtered['quantiles'] = pd.qcut(filtered['UGDS'], q=3, labels=['Small', 'Medium', 'Large'])
                    filtered['sizes'] = (filtered['quantiles'].isin(data_dict[constraint]['val'])).astype(int)
                else:
                    filtered['sizes'] = 1
            elif constraint == 'types':
                filtered['types'] = (filtered['CONTROL'] == data_dict[constraint]['val']).astype(int)
            elif constraint == 'urban':
                if data_dict[constraint]['val'] != ['']:
                    filtered['urban'] = (filtered['LOCALE'].isin(data_dict[constraint]['val'])).astype(int)
                else:
                    filtered['urban'] = 1
            elif constraint == 'religs':
                relig = DatabaseHandler.get_table('relig').rename(columns={'NAME': 'RELIGION'})
                filtered = filtered.merge(relig, on='RELAFFIL', how='left')
                if data_dict[constraint]['val'] != ['']:
                    filtered['religs'] = (filtered['RELIGION'].isin(data_dict[constraint]['val'])).astype(int)
                else:
                    filtered['religs'] = 1
            else:
                if data_dict[constraint]['val'] != ['']:
                    # Form list of columns to reference
                    col_list = []
                    for i in data_dict[constraint]['val']:
                        if i == 'Men-Only College':
                            col_list.append('MENONLY')
                        elif i == 'Women-Only College':
                            col_list.append('WOMENONLY')
                        elif i == 'Alaska Native Native Hawaiian Serving Institution':
                            col_list.append('ANNHI')
                        elif i == 'Asian American Native American Pacific Islander-Serving Institution':
                            col_list.append('AANAPII')
                        elif i == 'Hispanic-Serving Institution':
                            col_list.append('HSI')
                        elif i == 'Historically Black College and University':
                            col_list.append('HBCU')
                        elif i == 'Native American Non-Tribal Institution':
                            col_list.append('NANTI')
                        elif i == 'Predominantly Black Institution':
                            col_list.append('PBI')
                        elif i == 'Tribal College and University':
                            col_list.append('TRIBAL')
                    filtered['mission_check'] = filtered[col_list].sum(axis=1, skipna=True)
                    filtered['missions'] = (filtered['mission_check'] > 0).astype(int)
                else:
                    filtered['missions'] = 1

        columns = ['UNITID', 'INSTNM', 'ZIP', 'CITY', 'STABBR', 'LATITUDE', 'LONGITUDE', 'NPT', 'NPT4_PUB', 'NPT4_PRIV',
                   'DISTANCE_MI',
                   'SATMT25', 'SATMT75', 'SATVR25', 'SATVR75', 'ACTCM25', 'ACTCM75', 'EARN_NE_MDN_3YR',
                   'MD_EARN_WNE_P10', 'ADM_RATE',
                   'GRAD_RATE', 'UGDS', 'CONTROL', 'LOCALE', 'RELIGION',
                   'input_zip', 'states', 'cost', 'field', 'degree', 'sat_math', 'sat_cr', 'act', 'salary3', 'salary10',
                   'ar', 'gr', 'sizes', 'types',
                   'urban', 'religs', 'missions']
        return filtered[columns]

    @staticmethod
    def apply_hard(base_table, hard_list):
        accept_thres = len(hard_list)
        # Transform salary column
        base_table['salary_selected'] = base_table.apply(
            lambda row: 'salary3' if row['salary3'] != 0 else 'salary10', axis=1)
        # Consolidate salary3 and salary10 to simply salary
        base_table['salary'] = base_table.apply(
            lambda row: row[row['salary_selected']], axis=1)
        # Consolidate salary amount columns to 1
        base_table['salary_amt'] = base_table.apply(
            lambda row: row['EARN_NE_MDN_3YR'] if row['salary_selected'] == 'salary3' else row['MD_EARN_WNE_P10'],
            axis=1
        )
        base_table['num_hard_met'] = base_table[hard_list].sum(axis=1, skipna=True)
        filtered = base_table[base_table['num_hard_met'] == accept_thres]
        del filtered['num_hard_met']
        del filtered['EARN_NE_MDN_3YR']
        del filtered['MD_EARN_WNE_P10']
        del filtered['salary3']
        del filtered['salary10']
        return filtered

    @staticmethod
    def output_csv(df, data_dict, filename):
        if data_dict['limit_match'] == '1':
            limit_match = 5
        elif data_dict['limit_match'] == '2':
            limit_match = 10
        elif data_dict['limit_match'] == '3':
            limit_match = 15
        elif data_dict['limit_match'] == '4':
            limit_match = 20
        elif data_dict['limit_match'] == '5':
            limit_match = 25
        else:
            limit_match = 30
        query = f"""SELECT RANK() OVER (ORDER BY UNITID) as RANKING, INSTNM as [NAME], [ZIP], 
           CITY, STABBR as STATE, DISTANCE_MI as [DISTANCE IN MILES], LATITUDE, LONGITUDE,
           NPT as [AVG COST BASED ON HI], coalesce(NPT4_PUB, NPT4_PRIV) [OVERALL AVG COST], SATMT25 as [SAT MATH 25TH PCTL], 
           SATMT75 as [SAT MATH 75th PCTL], SATVR25 as [SAT CR 25TH PCTL], SATVR75 as [SAT CR 75TH PCTL], 
           ACTCM25 as [ACT 25TH PCTL], ACTCM75 as [ACT 75TH PCTL], ADM_RATE [ADMISSION RATE], GRAD_RATE [GRADUATION RATE],
           UGDS [ENROLLMENT SIZE], CONTROL [SCHOOL TYPE], LOCALE, RELIGION, case when field = '1' then 'Y' else 'N' end [FIELD OFFERED],
           case when degree = '1' then 'Y' else 'N' end [DEGREE OFFERED], case when missions = '1' then 'Y' else 'N' end [RELIGIOUS AFFILIATION], 
           case when salary_selected = 'salary3' then '3YR MEDIAN EARNINGS' else '10YR MEDIAN EARNINGS' end [SALARY REPORTED], salary_amt [SALARY]
           FROM df
           ORDER BY UNITID
           LIMIT {limit_match}"""
        sqldf(query).to_csv(filename, index=False)
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
                           'sat_math_pref':'10', 'sat_cr_pref':'10', 'act_pref':'10',
                           'ar_pref':'10', 'gr_pref':'10',
                           'sizes': '', 'size_pref':'10',
                           'types':'Public', 'type_pref':'10',
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
                        'sat_math_pref': request.form.get('sat_math_pref'),
                        'sat_cr_pref': request.form.get('sat_cr_pref'),
                        'act_pref': request.form.get('act_pref'),
                        'ar_pref': request.form.get('ar_pref'),
                        'gr_pref': request.form.get('gr_pref'),
                        'sizes': request.form.getlist('sizes'),
                        'size_pref': request.form.get('size_pref'),
                        'types': request.form.getlist('types')[0],
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
            'sat_math': {'pref':default_selected['sat_math_pref'],'val': sat_math,'multi': 'N'},
            'sat_cr': {'pref': default_selected['sat_cr_pref'], 'val': sat_cr, 'multi': 'N'},
            'act': {'pref': default_selected['act_pref'], 'val': act, 'multi': 'N'},
            'states': {'pref': 10, 'val': default_selected['states'], 'multi': 'Y'},
            'input_zip': {'pref': default_selected['zip_pref'], 'val': [input_zip, max_dist], 'multi': 'N'},
            'field': {'pref': default_selected['field_pref'], 'val': default_selected['fields'], 'multi': 'N'},
            'cost': {'pref': default_selected['cost_pref'], 'val': [max_cost, default_selected['hi']], 'multi': 'N'},
            'salary': {'pref': default_selected['sal_pref'], 'val': salary, 'multi': 'N'},
            'ar': {'pref': default_selected['ar_pref'], 'val': ar, 'multi': 'N'},
            'gr': {'pref': default_selected['gr_pref'], 'val': gr, 'multi': 'N'},
            'types': {'pref': default_selected['type_pref'], 'val': default_selected['types'], 'multi': 'N'},
            'sizes': {'pref': default_selected['size_pref'], 'val': default_selected['sizes'], 'multi': 'Y'},
            'urban': {'pref': default_selected['urban_pref'], 'val': default_selected['urban'], 'multi': 'Y'},
            'missions': {'pref': default_selected['mission_pref'], 'val': default_selected['missions'], 'multi': 'Y'},
            'religs': {'pref': default_selected['relig_pref'], 'val': default_selected['religs'], 'multi': 'Y'}
            }

    filename = os.path.join(os.path.dirname(db_path), "data.pickle")
    with open(filename, "wb") as file:
        pickle.dump(data, file)

    full_list, hard_list, soft_list = rankHandler.determine_constraint_type(data)
    base = rankHandler.apply_constraints(data, full_list)
    reduced = rankHandler.apply_hard(base, hard_list)
    file = os.path.join(os.path.dirname(db_path),'static','landing','ranked_results.csv')
    rankHandler.output_csv(reduced, data, file)

    return render_template('landing.html', user =user, default_selected= default_selected,
                           states=states, fields = fields, zip =input_zip, zip_dist=max_dist, max_cost =max_cost,
                           sat_math =sat_math, sat_cr = sat_cr, act = act, salary = salary, ar= ar, gr =gr,
                           sizes = sizes, types=types, urban =urban, missions=missions, religs=religs)


if __name__ == '__main__':
   app.run()