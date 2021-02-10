import numpy as np
import random
import pandas as pd
from tools import rename_cols_ohlcv
            
attrs = {}

def ind(df, func,  *args, **kwargs):
    def ind2(df, *args, **kwargs):
        return pd.DataFrame(func(df, *args, **kwargs))
    return df.groupby('instrument').apply(ind2, *args, **kwargs)

'''add indicator without returning, assigns column name using set_name'''
def add_label_df(df, func, *args, **kwargs):
    #if 'open' in df.columns:
    #    df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'},inplace=True)
    rename_cols_ohlcv(df, to='upper')
    indicator_df = ind(df[['Open','High','Low']], func, *args, **kwargs)
    df[indicator_df.columns] = indicator_df
    
    for col in indicator_df.columns:
        attributes = {
            'val_type':'n_bars',
            'group':attrs['group'],
            'input_names':attrs['input_names'],
            'params':attrs['parameters'],
            'transforms_applied':[] 
        }
        df.__setattr__('_'+col, attributes)
        df._metadata.append('_'+col)

''' Triple Barrier labeling method '''
def tb_label(df, target, verticle_barrier = 400, target_type = 'prcnt'):
    param_str = '_'+str(target)+'_'+str(verticle_barrier)+'_'+target_type
    attrs['group'] = 'label'
    attrs['input_names'] = {'prices':['open','high','low']}
    attrs['parameters'] = {'target':target,
                            'verticle_barrier':verticle_barrier,
                            'target_type':target_type
                           }
    divisor = 10000
    num_decimals = 5
    pair = df.index.get_level_values(0)[0]
    if 'JPY' in pair:
        num_decimals = 3
        divisor = 100
    if target > 0:
        label = 'label_'+target_type+'_up_'+str(abs(target))+'_vb_'+str(verticle_barrier)
    elif target < 0:
        label = 'label_'+target_type+'_dwn_'+str(abs(target))+'_vb_'+str(verticle_barrier)
    lbl = np.empty(len(df))
    lbl[:] = np.nan
    n_shifts = 0
    if target_type == 'pips':
        targets = np.round(df.Open.shift(-1) + target/divisor, num_decimals)
    elif target_type == 'prcnt':
        targets = df.Open.shift(-1) + np.round(df.Open.shift(-1)*target*.01, num_decimals)
    while n_shifts < verticle_barrier:
        if target > 0:
            lbl = np.where((np.isnan(lbl)) & (df.High.shift(-(n_shifts+1)) >= targets), n_shifts, lbl)
        elif target < 0:
            lbl = np.where((np.isnan(lbl)) & (df.Low.shift(-(n_shifts+1)) <= targets), n_shifts, lbl)
        n_shifts += 1
    '''change NaN to -1 where barrier is hit'''
    lbl = np.where((np.isnan(lbl)) & (~np.isnan(df.Open.shift(-(n_shifts+1)))), -1.0, lbl)
    return pd.DataFrame(data = {label:lbl}, index = df.index)