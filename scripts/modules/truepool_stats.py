#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 1.20
@date: 28/07/2021

Warning: Built for use with python 3.6+
'''

import json
import requests
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
#uncomment for debugging purposes only
import traceback

##logging configuration block
log_file_full_path = os.path.join('..', 'logs', 'truepool_stats.log')
logger_file_handler = RotatingFileHandler(log_file_full_path, maxBytes=8388608, backupCount=1, encoding='utf-8')
logger_format = '%(asctime)s %(levelname)s : %(name)s >>> %(message)s'
logger_file_handler.setFormatter(logging.Formatter(logger_format))
#logging level for other modules
logging.basicConfig(format=logger_format, level=logging.INFO) #DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = logging.getLogger(__name__)
#logging level for current logger
logger.setLevel(logging.INFO) #DEBUG, INFO, WARNING, ERROR, CRITICAL
logger.addHandler(logger_file_handler)

HTTP_TIMEOUT = 5

##base url strings
POOL_INFO_API_URL = 'https://truepool.io/v1/pool/info'
FARMER_STATS_API_URL = 'https://truepool.io/v1/pool/farmer'
PARTIALS_STATS_API_URL = 'https://truepool.io/v1/pool/partial'
PAYOUT_STATS_API_URL = 'https://truepool.io/v1/pool/payout_address'

class truepool_stats:
    '''gather pool stats using the TruePool RESTful API'''
    
    _farmer_launcher_id = None

    pool_total_size = 0
    pool_total_farmers = 0
    pool_minutes_to_win = 0
    pool_blocks_won = 0
    farmer_points = 0
    farmer_difficulty = 0
    farmer_points_percentage = 0
    farmer_estimated_size = 0
    farmer_ranking = 0
    farmer_pool_earnings = 0
    partial_errors_24h = 0
    
    def clear_stats(self):
        #note to self - it might make sense to accumulate some stats in 
        #the future, depending on what grafana charts are being exposed
        self.pool_total_size = 0
        self.pool_total_farmers = 0
        self.pool_minutes_to_win = 0
        self.pool_blocks_won = 0
        self.farmer_points = 0
        self.farmer_difficulty = 0
        self.farmer_points_percentage = 0
        self.farmer_estimated_size = 0
        self.farmer_ranking = 0
        self.farmer_pool_earnings = 0
        self.partial_errors_24h = 0
        
    def set_farmer_launcher_id(self, farmer_launcher_id):
        self._farmer_launcher_id = farmer_launcher_id
        
    def collect_stats(self):
        
        #maybe only show a warning in the future an only exclude farmer/partial specific stats
        if self._farmer_launcher_id is None:
            raise Exception('Farmer launcher id has not been set. Pool stats can not be collected!')
        
        logger.info('+++ Starting data collection run +++')
        
        try:
            with requests.Session() as session:
                four_score_and_twenty_four_hours_ago = int(datetime.timestamp(datetime.now() - timedelta(hours=24)))
                logger.debug(f'four_score_and_twenty_four_hours_ago: {four_score_and_twenty_four_hours_ago}')
                
                logger.info('Fetching pool stats...')
                #########################################################
                response = session.get(POOL_INFO_API_URL, timeout=HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == 200:
                    pool_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)
                    
                    self.pool_total_size = pool_stats_json['total_size']
                    self.pool_total_farmers = pool_stats_json['total_farmers']
                    self.pool_minutes_to_win = pool_stats_json['minutes_to_win']
                    self.pool_blocks_won = pool_stats_json['total_rewards_heights']
                    
                    logger.debug(f'pool_total_size: {self.pool_total_size}')
                    logger.debug(f'pool_total_farmers: {self.pool_total_farmers}')
                    logger.debug(f'pool_minutes_to_win: {self.pool_minutes_to_win}')
                    logger.debug(f'pool_blocks_won: {self.pool_blocks_won}')
                #########################################################
                
                logger.info('Fetching farmer stats...')
                #########################################################
                response = session.get(FARMER_STATS_API_URL + f'?ordering=-points', timeout=HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == 200:
                    global_farmer_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    farmer_iterator = iter(global_farmer_stats_json)
                    found_farmer = False
                    
                    while not found_farmer:
                        current_farmer = next(farmer_iterator)
                        self.farmer_ranking += 1
                        
                        if current_farmer['launcher_id'].strip() == self._farmer_launcher_id:
                            logger.debug('Found the farmer!')
                            found_farmer = True
                    
                    logger.debug(f'farmer_ranking: {self.farmer_ranking}')
                
                response = session.get(FARMER_STATS_API_URL + f'/?launcher_id={self._farmer_launcher_id}', timeout=HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == 200:
                    farmer_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results'][0]
                    
                    self.farmer_points = farmer_stats_json['points']
                    self.farmer_difficulty = farmer_stats_json['difficulty']
                    self.farmer_points_percentage = farmer_stats_json['points_percentage']
                    self.farmer_estimated_size = farmer_stats_json['farm_estimated_size']
                    
                    logger.debug(f'farmer_points: {self.farmer_points}')
                    logger.debug(f'farmer_difficulty: {self.farmer_difficulty}')
                    logger.debug(f'farmer_points_percentage: {self.farmer_points_percentage}')
                    logger.debug(f'farmer_estimated_size: {self.farmer_estimated_size}')
                #########################################################
                
                logger.info('Fetching partials stats...')
                #########################################################
                #can't be bothered with pagination (meant for the website anyway), 
                #so use a resonable non-standard limit - may have to adjust later on
                response = session.get(PARTIALS_STATS_API_URL + f'/?launcher_id={self._farmer_launcher_id}' + 
                                       f'&start_timestamp={four_score_and_twenty_four_hours_ago}&limit=500', 
                                       timeout=HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == 200:
                    partials_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    for partial in partials_stats_json:
                        if partial['error'] is not None:
                            self.partial_errors_24h += 1
                            
                    logger.debug(f'partial_errors_24h: {self.partial_errors_24h}')
                #########################################################
                
                logger.info('Fetching payout stats...')
                #########################################################
                response = session.get(PAYOUT_STATS_API_URL + f'/?farmer={self._farmer_launcher_id}', timeout=HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == 200:
                    payouts_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    for payout in payouts_stats_json:
                        self.farmer_pool_earnings += payout['amount']
                            
                    logger.debug(f'farmer_pool_earnings: {self.farmer_pool_earnings}')
                #########################################################
                    
        except:
            #uncomment for debugging purposes only
            logger.error(traceback.format_exc())
            raise
            
        logger.info('--- Data collection complete ---')
    