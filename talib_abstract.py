from talib import abstract as taa
from talib import get_function_groups
from datetime import timedelta
#import load_data
#from importlib import reload
#reload(load_data)
#from load_data import load_data
import pandas as pd
import numpy as np
from IPython.display import clear_output, display
from tools import rename_cols_ohlcv

def ind(df, func,  *args, **kwargs):
    def ind2(df, *args, **kwargs):
        return pd.DataFrame(func(df, *args, **kwargs))
    return df.groupby('instrument').apply(ind2, *args, **kwargs)

def default_params(f):
    pass

def fninfo(f):
    pass

def display_info(f):
    pass

def params(f):
    pass

def function_groups():
    get_function_groups()
    for func in get_function_groups():
        print(func, taa.Function(func).info['parameters'])
    
def set_name(func, to_lower = True):
    name = ''
    name += func.info['name']
    
    param_str = ''
    for key, value in func.info['parameters'].items():
        param_str += '_'+str(value)

    if len(func.output_names) > 1:
        names = []
        for s in func.output_names:
            names.append(name + '_' + s + param_str)
        if to_lower:
            names = [s.lower() for s in names]       
        return names
    
    name += param_str
    if to_lower:
        name = name.lower()
    return name

def val_type(func):
    return func.info['group']

def add_ind(df, func, *args, **kwargs):
    #if 'Open' in df.columns:
    #    df.rename(columns={'Open':'open', 'High':'high', 'Low':'low', 'Close':'close', 'Volume':'volume'},inplace=True)
    rename_cols_ohlcv(df, to='lower')
    columns = df.columns
    df[set_name(func)] = ind(df[['open','high','low','close','volume']], func, *args, **kwargs)
    new_cols = list(set(df.columns).difference(set(columns)))
    for col in new_cols:
        attributes = {
            'val_type':func.info['group'],
            'group':func.info['group'],
            'input_names':func.info['input_names'],
            'params':func.info['parameters'],
            'transforms_applied':[]
            
        }
        df.__setattr__('_'+col, attributes)
        df._metadata.append('_'+col)
        #df[col].val_type = func.info['group']
        #df[col].group = func.info['group'] #price, standard_range, price_scaled, etc
