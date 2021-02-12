
import MySQLdb
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve

with open('config.json','r') as f:
    config = json.load(f)

conn = MySQLdb.connect(host=config['dbHost'], user=config['dbUser'],passwd=config['dbPass'],db='forexV20')
instruments = [
               'AUD_USD',
               'CAD_JPY',
               'EUR_CHF',
               'EUR_GBP',
               'EUR_JPY', 
               'EUR_USD',
               'GBP_CHF',
               'GBP_JPY',
               'NZD_USD',
               'USD_CAD',
               'USD_CHF',
               'USD_JPY',
               'EUR_AUD',
               'GBP_USD',
               ]

def rate(instrument, time):
    x = conn.cursor()
    #sql = "SELECT C_m FROM m1 where instrument = \'" + instrument + "\' and time = \'"+str(time)+"\';"
    if time.minute == 30:
        granularity = 'm30'
    elif time.minute == 15:
        granularity = 'm15'
    else:
        granularity = 'h1'
    granularity = 'm5'

    table = instrument.lower()+'_'+granularity
    if instrument == 'CAD_USD':
        table = 'usd_cad_'+granularity
    sql = "SELECT O_m, H_m, L_m FROM "+table+" where time = \'"+str(time)+"\';"
    x.execute(sql)
    result = x.fetchone()
    if not result:
        print('error: no result in tools.rate, returned 1 as replacement value',sql)
        return float(1)
    if instrument == 'CAD_USD':
        return 1.0/float(result[0])
    return float(result[0])

def pip_value(instrument, units, time, price):
	units = float(units)
	if instrument[4:] == 'USD':
		return units/10000
	inst = instrument[4:]+'_USD'
	if inst not in instruments:
		inst = 'USD_'+inst[:3]
		price2 = 1/rate(inst,time)
	else:
		price2 = rate(inst,time)
	if 'JPY' in instrument:
		price2 *= 100
	return price2 * units/10000


def num_pips(price1, price2):
	if price1 >= 10:
		return abs(price1 - price2)*100
	return abs(price1 - price2)*10000

'''
	Returns profit or loss of a trade without the commission accounted for
	https://www.oanda.com/forex-trading/analysis/profit-calculator/
'''
def trade_pnl(instrument, trade_price, direction, units, closing_price, time):
	if direction == 1:
		if closing_price >= trade_price:
			return num_pips(closing_price, trade_price) * pip_value(instrument, units, time, trade_price)
		return -num_pips(closing_price, trade_price) * pip_value(instrument, units, time, trade_price)
	elif direction == 0:
		if closing_price <= trade_price:
			return num_pips(closing_price, trade_price) * pip_value(instrument, units, time, trade_price)
		return -num_pips(closing_price, trade_price) * pip_value(instrument, units, time, trade_price)
	return 'Error'

def plot_balance(balance):
    balance_vals = [d['balance'] for d in balance]
    plt.plot(balance_vals)
    plt.show()
    monthly_returns = []
    month = balance[0]['index'].month
    starting_balance = balance[0]['balance']
    for i,b in enumerate(balance):
        if (b['index'].month != month) or (i == len(balance)-1):
            ret = round((b['balance']-starting_balance) / starting_balance,4)
            monthly_returns.append(ret)
            month = b['index'].month
            starting_balance = b['balance']
    avg_monthly_ret = sum(monthly_returns)/len(monthly_returns)
    print(monthly_returns)
    print('Avg monthly return: ', round(avg_monthly_ret,4))
    
    
def plot_calibration_curve(model, X_test,Y_test,n_bins=10):  
    fraction_of_positives, mean_predicted_value = calibration_curve(Y_test, model.predict_proba(X_test)[:,1],n_bins=n_bins )
    plt.plot([0, 1], [0, 1],  label="Perfectly calibrated")
    plt.plot(mean_predicted_value, fraction_of_positives,'-+' )
    plt.show()

def plot_predictions_dist(model,X_test,bins=30):
    probs = model.predict_proba(X_test)
    plt.hist(probs[:,1],bins=bins)
    plt.show()
    
def prcnt_hit_barrier(m, x_data, y_data, target=0, threshold=.5):
    correct = 0
    hit_barrier = 0
    above_threshold = 0
    for i,p in enumerate(m.predict_proba(x_data)[:,target+1]):
        if p > threshold:
            above_threshold += 1
            if y_data[i] == target:
                correct += 1
            if y_data[i] == -1:
                hit_barrier += 1
    print('TARGET:',target, 'THRESHOLD:',threshold)
    print('N correct:\t',correct)
    print('N hit barr:\t',hit_barrier)
    print('N above',str(threshold)+':\t',above_threshold)
    if above_threshold != 0:
        print('% correct:\t',round(correct/above_threshold, 3))
        print('% hit barrier:\t', round(hit_barrier/above_threshold, 3))
    if target+1 <= 1:
        prcnt_hit_barrier(m, x_data, y_data, target+1, threshold)
        

def plot_calibration_curve_tb(m, X_test,Y_test, target=-1, n_bins=10):
    Y_test2 = np.where(Y_test == target, 1, 0)
    fraction_of_positives, mean_predicted_value = calibration_curve(Y_test2, m.predict_proba(X_test)[:,target+1],n_bins=n_bins )
    plt.figure(figsize = (16,4))
    plt.subplot(1,3,1)
    plt.plot([0, 1], [0, 1],  label="Perfectly calibrated")
    plt.plot(mean_predicted_value, fraction_of_positives,'-+' )
    
    target += 1
    Y_test2 = np.where(Y_test == target, 1, 0)
    fraction_of_positives, mean_predicted_value = calibration_curve(Y_test2, m.predict_proba(X_test)[:,target+1],n_bins=n_bins )
    plt.subplot(1,3,2)
    plt.plot([0, 1], [0, 1],  label="Perfectly calibrated")
    plt.plot(mean_predicted_value, fraction_of_positives,'-+' )
    
    target += 1
    Y_test2 = np.where(Y_test == target, 1, 0)
    fraction_of_positives, mean_predicted_value = calibration_curve(Y_test2, m.predict_proba(X_test)[:,target+1],n_bins=n_bins )
    plt.subplot(1,3,3)
    plt.plot([0, 1], [0, 1],  label="Perfectly calibrated")
    plt.plot(mean_predicted_value, fraction_of_positives,'-+' )
    plt.show()
    
def plot_predictions_dist_tb(m,X_test,target=-1, bins=30):
    probs = m.predict_proba(X_test)
    plt.figure(figsize = (16,4))
    plt.subplot(1,3,1)
    plt.hist(probs[:,target+1],bins=bins)
    plt.xticks(np.arange(0, 1.1, step=0.2))
    target += 1
    plt.subplot(1,3,2)
    plt.hist(probs[:,target+1],bins=bins)
    plt.xticks(np.arange(0, 1.1, step=0.2))
    target += 1
    plt.subplot(1,3,3)
    plt.hist(probs[:,target+1],bins=bins)
    plt.xticks(np.arange(0, 1.1, step=0.2))
    plt.show()

def multiplier(granularity):
    if granularity == 'H1':
        return 1
    elif granularity == 'M30':
        return 2
    elif granularity == 'M15':
        return 4
    elif granulatiy == 'M5':
        return 12
    
def label_col_names(columns):
    label_cols = []
    for col in columns:
        if 'label' in col:
            label_cols.append(col)
    return label_cols

def mp_col_names(columns):
    mp_cols = []
    for col in columns:
        if 'init_balance' in col:
            mp_cols.append(col)
        elif 'open_range' in col:
            mp_cols.append(col)
        elif 'poc_' in col:
            mp_cols.append(col)
        elif 'profile_range' in col:
            mp_cols.append(col)
        elif 'value_area' in col:
            mp_cols.append(col)
        elif 'balanced_target' in col:
            mp_cols.append(col)
    return mp_cols
            
def group(df, inst):
    return df.groupby('instrument').get_group(inst)
    

from IPython.display import display_html
def display_side_by_side(*args):
    html_str=''
    for df in args:
        html_str+=df.to_html()
    display_html(html_str.replace('table','table style="display:inline"'),raw=True)

def margin(inst, units, time):
	margin_required = {'AUD_USD':.03, 'USD_JPY':.04, 'EUR_USD':.02, 
                       'GBP_USD':.05, 'USD_CAD':.02, 'EUR_JPY':.04, 
                       'NZD_USD':.03, 'GBP_CHF':.05, 'CAD_JPY':.04,
                       'USD_CHF':.03, 'EUR_AUD':.03, 'GBP_JPY':.05, 'EUR_GBP':.05, 'EUR_CHF':.03,}
	if inst[:3] == 'USD':
		return units * margin_required[inst]
	return units * rate(inst[:3]+'_USD',time) * margin_required[inst]

def margin_available(positions, balance):
	margin_used = 0
	for inst in positions:
		margin_used += positions[inst]['margin']
	return balance - margin_used

def units_available(instrument, margin_available, time, price):
	margin_required = {'AUD_USD':.03, 'USD_JPY':.04, 'EUR_USD':.02, 
                       'GBP_USD':.05, 'USD_CAD':.02, 'EUR_JPY':.04, 
                       'NZD_USD':.03, 'GBP_CHF':.05, 'CAD_JPY':.04,
                       'USD_CHF':.03, 'EUR_AUD':.03, 'GBP_JPY':.05, 'EUR_GBP':.05, 'EUR_CHF':.03, }
	if instrument[:3] == 'USD':
		return margin_available * (1.0/margin_required[instrument])
	return margin_available * (1.0/margin_required[instrument]) /  rate(instrument[:3]+'_USD',time)


#balance = [{"balance":initial_balance, "index":times[0]}]
def avg_monthly_return(balance):
	pass



def commission(units):
	return float(units) / 12500

def swap():
	#https://www.oanda.com/forex-trading/analysis/financing-calculator
	pass

def position_size():
	#https://www.thebalance.com/how-to-determine-proper-position-size-when-forex-trading-1031023
	#https://www.babypips.com/tools/position-size-calculator
	pass

def stats():
	pass

def value_types_cols(df, val_type ):
    #value types = 'price', 'scale', 'category', 'misc', etc
    val_groups = {}
    no_attr = []
    for col in df.columns:
        if hasattr(df, '_'+col):
            val_groups[col] = df.__getattr__('_'+col)['val_type']
        else:
            no_attr.append(col)
    val_types = {}
    for col,val_type in val_groups.items():
        if val_type in val_types:
            val_types[val_type].append(col)
        else:
            val_types[val_type] = [col]
    return val_types, no_attr
    
def col_groups(df):
    col_groups = {}
    no_attr = []
    for col in df.columns:
        if hasattr(df, '_'+col):
            col_groups[col] = df.__getattr__('_'+col)['group']
        else:
            no_attr.append(col)
    groups = {}
    for col,group in col_groups.items():
        if group in groups:
            groups[group].append(col)
        else:
            groups[group] = [col]
    return groups, no_attr

def add_attributes(df):
    prices = ['Open', 'High', 'Low', 'Close', 'H_b', 'H_a', 'L_b', 'L_a', 'O_b', 'O_a', 'C_b', 'C_a']
    for col in df.columns:
        if col in prices:
            attributes = {
                'val_type':'price',
                'group':'prices',
                'input_names':[col],
                'params':[],
                'transforms_applied':[]    
            }
            df.__setattr__('_'+col, attributes)
            df._metadata.append('_'+col)
        if col == 'Volume':
            attributes = {
                'val_type':'volume',
                'group':'volume',
                'input_names':[col],
                'params':[],
                'transforms_applied':[]    
            }
            df.__setattr__('_'+col, attributes)
            df._metadata.append('_'+col)
            
def rename_cols_ohlcv(df, to='upper'):
    lower_case_cols = ['open','high','low','close','volume']
    upper_case_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if to == 'upper':
        for i,col in enumerate(lower_case_cols):
            if col in df.columns:
                new_name = upper_case_cols[i]
                df.rename(columns={col:new_name},inplace=True)
                attributes = {
                        'val_type':df.__getattr__('_'+col)['val_type'],
                        'group':df.__getattr__('_'+col)['group'],
                        'input_names':[new_name],
                        'params':df.__getattr__('_'+col)['params'],
                        'transforms_applied':df.__getattr__('_'+col)['transforms_applied']    
                }
                df.__setattr__('_'+new_name, attributes)
                df._metadata.append('_'+new_name)
    if to == 'lower':
        for i,col in enumerate(upper_case_cols):
            if col in df.columns:
                new_name = lower_case_cols[i]
                df.rename(columns={col:new_name},inplace=True)
                attributes = {
                        'val_type':df.__getattr__('_'+col)['val_type'],
                        'group':df.__getattr__('_'+col)['group'],
                        'input_names':[new_name],
                        'params':df.__getattr__('_'+col)['params'],
                        'transforms_applied':df.__getattr__('_'+col)['transforms_applied']    
                }
                df.__setattr__('_'+new_name, attributes)
                df._metadata.append('_'+new_name)

def func_val_type(func):
    val_types = {}


    if hasattr(func, 'info'):
        if func.info['group'] == 'Momentum Indicators':
            return 'range'
        if func.info['group'] == 'Pattern Recognition':
            return 'pattern'
        if func.info['group'] == 'Overlap Studies':
            return 'price'
        if func.info['group'] == 'Volume Indicators':
            return '?'
        if func.info['group'] == 'Volatility Indicators':
            return '?'
        if func.info['group'] == 'Statistic Functions':
            return '?'
        if func.info['group'] == 'Cycle Indicators':
            return '?'
        if func.info['group'] == 'Price Transform':
            return 'price'
        return '?'
    return '?'