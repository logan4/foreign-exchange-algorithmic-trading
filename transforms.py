import numpy as np
from pandas import to_numeric
from math import pi

''' converts an indicators to the difference from another column'''
def diff(df, cols, col2):
    for col in cols:
        df[col] = df[col] - df[col2]
        add_attr(df, col, 'diff')

''' converts a price value to pips'''
def diff_to_pips(df, cols):
    key0 = np.array([x[0] for x in df.index])
    for col in cols:
        df[col] = np.where( (key0 == 'USD_JPY') | (key0 == 'EUR_JPY') | (key0 == 'CAD_JPY') | (key0 == 'GBP_JPY'), df[col] * 100, df[col] * 10000)
        add_attr(df, col, 'diff_to_pips')
        
''' converts a price value to prcnt'''
def diff_to_prcnt(df, cols, col2):
    for col in cols:
        df[col] = df[col] / df[col2]
        add_attr(df, col, 'diff_to_prcnt')
    
''' converts pips to a price value'''
def pips_to_diff(df, cols):
    key0 = np.array([x[0] for x in df.index])
    for col in cols:
        df[col] = np.where( (key0 == 'USD_JPY') | (key0 == 'EUR_JPY') | (key0 == 'CAD_JPY') | (key0 == 'GBP_JPY'), df[col] / 100, df[col] / 10000)
        add_attr(df, col, 'pips_to_diff')
        
def hour_to_cycle(df):
    df['hourX'] = np.sin(2*pi*df.hour/24)
    df['hourY'] = np.cos(2*pi*df.hour/24)
    attrs = {
        'val_type':'misc',
        'group':'transform',
        'input_names':['hour'],
        'parameters':[],
        'transforms_applied':[]
    }
    for col in ['hourX', 'hourY']:
        df.__setattr__('_'+col, attrs)
    
''' downcast column dtype to free up memory '''
def downcast(df, cols, dtype='integer'):
    for col in cols:
        df[col] = to_numeric(df[col], downcast=dtype)
        add_attr(df, col, 'downcast')
        
def to_category(df, cols):
    for col in cols:
        df[col] = df[col].astype('category')
        add_attr(df, col, 'to_category')
        
''' call this method to add the transform name to the list of applied transforms on the attributes '''
def add_attr(df, col, transform_applied):
    attrs = df.__getattr__('_'+col)
    attrs['transforms_applied'].append(transform_applied)
    df.__setattr__('_'+col,attrs)
    
def undo_transform(df, cols, transform_to_undo, col2 = 'close'):
    for col in cols:
        if transform_to_undo == 'diff':
            df[col] = df[col] + df[col2]
        elif transform_to_undo == 'diff_to_pips':
            key0 = np.array([x[0] for x in df.index])
            df[col] = np.where( (key0 == 'USD_JPY') | (key0 == 'EUR_JPY') | (key0 == 'CAD_JPY') | (key0 == 'GBP_JPY'), df[col] / 100, df[col] / 10000)
        elif transform_to_undo == 'diff_to_prcnt':
            df[col] = df[col] * df[col2]
        elif transform_to_undo == 'pips_to_diff':
            key0 = np.array([x[0] for x in df.index])
            df[col] = np.where( (key0 == 'USD_JPY') | (key0 == 'EUR_JPY') | (key0 == 'CAD_JPY') | (key0 == 'GBP_JPY'), df[col] * 100, df[col] * 10000)
        elif transform_to_undo == 'downcast':
            pass
        elif transform_to_undo == 'to_category':
            pass
        
        remove_attr(df, col, transform_to_undo)

def remove_attr(df, col, transform_to_undo):
    attrs = df.__getattr__('_'+col)
    attrs['transforms_applied'].remove(transform_to_undo)
    df.__setattr__('_'+col,attrs)
        
def remove_all_transforms(df, cols):
    for col in cols:
        attrs = df.__getattr__('_'+col)
        for transform_applied in attrs['transforms_applied']:
            undo_transform(df, [col], transform_applied)