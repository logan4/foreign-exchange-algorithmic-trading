import json
with open('config.json','r') as f:
    config = json.load(f)
import MySQLdb
import pandas as pd
from copy import deepcopy

def load_data(pairs,start,end,granularity='H1', columns = 'time,O_m,H_m,L_m,C_m,H_b,H_a,L_b,L_a,O_b,O_a,C_b,C_a,V'):
    conn = MySQLdb.connect(host=config['dbHost'], user=config['dbUser'],passwd=config['dbPass'],db='forexV20')  
    frames = []
    for pair in pairs:
        sql = "SELECT "+columns+" FROM "+pair.lower()+"_"+granularity.lower()+ " where time >= "+start+" and time <= "+end+";"
        df = pd.read_sql(sql,conn).set_index('time')
        df.rename(columns={'C_m':'Close','L_m':'Low','H_m':'High','O_m':'Open','V':'Volume'}, inplace=True)
        #df.fillna(method='ffill',inplace=True)
        #df.dropna(inplace=True)
        df.reset_index(inplace=True)
        df['instrument'] = pair
        df.set_index(['instrument','time'], inplace=True)
        df.name = pair
        df._metadata += ['name']
        frames.append(deepcopy(df))
    conn.close()
    return frames