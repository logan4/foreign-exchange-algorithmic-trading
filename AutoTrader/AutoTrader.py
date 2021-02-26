import json
import os

import math

import time
from oandapyV20 import API
from oandapyV20.exceptions import V20Error, StreamTerminated
from oandapyV20.endpoints.pricing import PricingStream
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts
from oandapyV20.contrib.requests import TakeProfitOrderRequest, StopLossOrderRequest

from requests.exceptions import ChunkedEncodingError

from sendEmail import sendEmail

import datetime
from datetime import timedelta
from dateutil.parser import parse
from getDataV20 import getData, transform, transform2
import pandas as pd
import pickle

import logging
logging.basicConfig(
    filename="v20.log",
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
)


probability = 0.0 

class AutoTrader(PricingStream):
	def __init__(self,instruments,granularity,prob_threshold,target,account_name, *args, **kwargs):
		PricingStream.__init__(self,*args, **kwargs)
		print "loading model..."
		self.model = pickle.load(open('mpv12_0025_const.sav','rb'))
		self.instruments = instruments.split(',')
		self.target = target
		self.connected = False
		self.account_name = account_name
		self.granularity = granularity
		self.prob_threshold = prob_threshold
		self.status = {}
		for inst in self.instruments:
			self.status[inst] = {
				"bid":None,
				"ask":None,
				"time":None,
				"trade_pred":None,
				"current_pred":None,
				"long":0,
				"short":0,
				"unrealizedPL":0,
				"pending_order":None,
				"made_prediction":False,
				"tradeID":None
			}
			
		print "connecting..."
		self.client = API(access_token=access_token,environment=environment)

	def on_success(self, tick):

		if tick['type'] == 'PRICE':


			inst = tick['instrument']
			timestamp = parse(tick['time'])
			if self.status[inst]['time'] != None and timestamp.second == parse(self.status[inst]['time']).second:
				#skip processing tick, only need to process one per second
				return

			precision = 5
			stops = self.target
			if 'JPY' in inst:
				stops *= 100
				precision = 3		

			account_details = self.get_account_details()
			self.update_status(tick, account_details['account']['trades'])
			self.display_status() 
			
			if ( timestamp.minute == 0 and not self.status[inst]['made_prediction'] ): 	
				df = getData(inst, self.granularity, 500)
				prediction = self.make_prediction(df,inst)
				self.status[inst]['current_pred'] = prediction
				self.status[inst]['made_prediction'] = True				
				
				midPrice = round((float(tick['asks'][0]['price']) + float(tick['bids'][0]['price'])) / 2,precision)
				if ( self.status[inst]['short'] == 0 and self.status[inst]['long'] == 0 ):

						
					balance = float(account_details['account']['balance'])
					margin_available = float(account_details['account']['marginAvailable'])
					gtdTime = timestamp + timedelta(minutes=5)
					units_available = self.units_available(inst, margin_available)
					units = math.ceil(balance*6)
					if units > units_available:
						units = int(round(units_available*.9))

					if ( prediction[0][1] > self.prob_threshold and units > 1000):
						stopLoss = round(midPrice - stops,precision)
						takeProfit = round(midPrice + stops,precision)
						self.send_order(instrument=inst, limit_price=midPrice, units=units, stopLoss = stopLoss, takeProfit = takeProfit, gtdTime=gtdTime)
						self.send_notification(instrument=inst, direction = 'buy', units = units, limit = midPrice, probability = prediction[0][1])
						self.status[inst]['trade_pred'] = prediction[0]

					elif ( prediction[0][0] > self.prob_threshold and units > 1000 ):
						stopLoss = round(midPrice + stops,precision)
						takeProfit = round(midPrice - stops,precision)
						self.send_order(instrument=inst,limit_price=midPrice, units=-units, stopLoss = stopLoss, takeProfit = takeProfit,gtdTime=gtdTime)
						self.send_notification(instrument=inst, direction = 'sell', units = -units, limit = midPrice, probability = prediction[0][0])
						self.status[inst]['trade_pred'] = prediction[0]

				else:		
					'''if trade is in the money and current prediction still holds, adjust targets '''
					if (self.status[inst]['unrealizedPL'] > 0):
						if (self.status[inst]['long'] != 0 and prediction[0][1] > self.prob_threshold):						
							self.adjust_targets(inst, takeProfit = round(midPrice + stops,precision), stopLoss = round(midPrice - stops,precision))
						elif (self.status[inst]['short'] != 0 and prediction[0][0] > self.prob_threshold):
							self.adjust_targets(inst, takeProfit = round(midPrice - stops,precision), stopLoss = round(midPrice + stops,precision))
					'''if opposite prediction is made and greater than .54, close position'''
					if (self.status[inst]['long'] != 0 and prediction[0][0] > .54) or (self.status[inst]['short'] != 0 and prediction[0][1] > .54):
						self.close_position(inst)

			elif timestamp.minute != 0:
				self.status[inst]['made_prediction'] = False
		#elif tick['type'] == 'ORDER_FILL':
			#update positions

	def request(self, r):
		#attempts to handle V20 rate limit errors
		try:
			self.client.request(r)
		except V20Error as e:
			sendEmail('AutoTrader', recipient, self.account_name+'\n'+'V20Error '+str(e))
			if 'Requests per second exceeded' in str(e):
				time.sleep(1)
				self.client.request(r)
			else:
				raise
		except:
			raise

	def send_order(self, instrument, limit_price, units, stopLoss, takeProfit, gtdTime):
		orderbody = {
			"order": {
				"price": str(limit_price),
				"stopLossOnFill": {
					"timeInForce": "GTC",
      				"price": str(stopLoss)
    			},
				"takeProfitOnFill": {
                    "timeInForce": "GTC",
                    "price": str(takeProfit)
                },
    		"timeInForce": "GTD",
			"gtdTime":str(gtdTime),
    		"instrument": instrument,
    		"units": str(units),
    		"type": "LIMIT",
    		"positionFill": "DEFAULT"
  			}
		}
		r = orders.OrderCreate(accountID, data=orderbody)
		self.request(r)
		#self.client.request(r)
		print r.response 

	def adjust_targets(self, instrument, takeProfit, stopLoss):
		data = {
			"takeProfit": {
				"timeInForce": "GTC",
				"price": str(takeProfit)
			},
			"stopLoss": {
				"timeInForce": "GTC",
				"price": str(stopLoss)
			}
		}
		r = trades.TradeCRCDO(accountID=accountID,tradeID=self.status[instrument]['tradeID'], data=data)
		self.request(r)
        #print r.response

	def close_position(self, instrument):
		r = trades.TradeClose(accountID, tradeID = int(self.status[instrument]['tradeID']))
		self.request(r)

	def units_available(self, instrument, margin_available):
		margin_required = {'AUD_USD':.03, 'USD_JPY':.04, 'EUR_USD':.02, 'GBP_USD':.05, 'USD_CAD':.02, 'EUR_JPY':.04, 'NZD_USD':.03}
		if instrument[:3] == 'USD':
			return margin_available * (1.0/margin_required[instrument])
		return margin_available * (1.0/margin_required[instrument]) /  float(self.status[instrument[:3]+'_USD']['bid'])
		
	
	def make_prediction(self, df,inst):
		print "Making prediction..."
		df = transform(df,pair=inst)
		df = transform2(df,pair=inst)
		inputs = df.values[-1].reshape(1,-1)
		print "Inputs ",inputs
		prediction = self.model.predict_proba(inputs)
		print "Predictions: ",prediction
		return prediction
		
	def get_account_details(self):
		r = accounts.AccountDetails(accountID)
		self.request(r)
		return r.response


	def get_pending_orders(self):
		r = orders.OrdersPending(accountID)
		self.request(r)
		return r.response
	

	def rates(self, accountID, instruments, **params):
		self.connected = True
		params = params or {}
		while self.connected:
			try:
				response = self.client.request(self)		
				for tick in response:
					if not self.connected:
						break
					if tick['type'] == 'PRICE':
						self.on_success(tick)
			except ChunkedEncodingError:
				sendEmail('AutoTrader', recipient, self.account_name+'\n'+'ChunkedEncodingError')
				pass
			except:
				sendEmail('AutoTrader', recipient, self.account_name+'\n'+'An exception occured')
				raise		

	def update_status(self, tick, trades):

		self.status[str(tick['instrument'])]['bid'] = tick['bids'][0]['price']
		self.status[str(tick['instrument'])]['ask'] = tick['asks'][0]['price']
		self.status[str(tick['instrument'])]['time'] = tick['time']

		for inst in self.instruments:
			self.status[inst]['short'] = 0
			self.status[inst]['long'] = 0
			self.status[inst]['tradeID'] = None

		for trade in trades:
			if int(trade['currentUnits']) < 0:
				self.status[trade['instrument']]['short'] = int(trade['currentUnits'])				
			elif int(trade['currentUnits']) > 0:
				self.status[trade['instrument']]['long'] = int(trade['currentUnits'])
			self.status[trade['instrument']]['unrealizedPL'] = float(trade['unrealizedPL'])
			self.status[trade['instrument']]['tradeID'] = trade['id']
			

	def display_status(self):
		cls()
		print "=====AUTOTRADER V2====="
		for inst in self.instruments:
			if self.status[inst]['bid'] == None:
				continue
			print '\n'
			print inst
			print 'ask:\t', self.status[inst]['ask']
			print 'bid:\t', self.status[inst]['bid']			
			print 'spread:\t', self.spread( inst, self.status[inst]['bid'], self.status[inst]['ask'] )
			print 'time:\t', parse(self.status[inst]['time'])
			print 'pred:\t',self.status[inst]['current_pred']
			if self.status[inst]['short'] != 0 or self.status[inst]['long'] != 0:
				print '\n'
				print '\tPOSITION'
				if self.status[inst]['short'] != 0:
					print '\tshort:\t', self.status[inst]['short']
					if not (self.status[inst]['trade_pred'] is None):
						print '\tprobability:\t', self.status[inst]['trade_pred'][0]
				else:
					print '\tlong:\t', self.status[inst]['long']
					if not (self.status[inst]['trade_pred'] is None):
						print '\tprobability:\t', self.status[inst]['trade_pred'][1]
				print '\tunrealized PL: ', self.status[inst]['unrealizedPL']

	def send_notification(self, instrument, direction, limit, units, probability ):
		sendEmail('AutoTrader', recipient, self.account_name+'\n'+instrument+'\n'+direction+'\nLimit: '+str(limit)+'\nUnits: '+str(units)+'\nProbability: '+str(round(probability,5)))
	
	def spread(self, inst, bid, ask):
		diff = float(ask) - float(bid)
		if 'JPY' in inst:
			return round(diff * 100,1)
		return round(diff * 10000,1)

	def disconnect(self):
		self.connected = False

def cls():
	os.system('cls' if os.name=='nt' else 'clear')			


					
with open('config.json', 'r') as f:
	config = json.load(f)
#oanda account to be traded on
accountID = ""
#oanda API access token 
access_token = "" 
#username of notication sender (tested on gmail)
email = config['emailUser']
#an email address of the notification recipient 
recipient = config['emailRecipient']

account_name = raw_input("Enter account name to trade on: ")
environment = raw_input("Live or practice: ")
if (environment == "live"):	
	accountID = config[account_name]
	access_token = config['liveToken']
elif (environment == "practice"):
	accountID = config[account_name]
	access_token = config['practiceToken']

instruments = 'EUR_USD,AUD_USD,USD_JPY,USD_CAD,GBP_USD,EUR_JPY,NZD_USD'

autotrader = AutoTrader(target=.0025, instruments = instruments, granularity='H1', prob_threshold=.53, accountID=accountID, account_name = account_name, params={"instruments":instruments})
autotrader.rates(accountID=accountID, instruments=instruments)
