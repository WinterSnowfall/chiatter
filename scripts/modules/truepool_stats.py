#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 1.70
@date: 16/08/2021

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
logger_file_handler = RotatingFileHandler(log_file_full_path, maxBytes=104857600, backupCount=2, encoding='utf-8')
logger_format = '%(asctime)s %(levelname)s : %(name)s >>> %(message)s'
logger_file_handler.setFormatter(logging.Formatter(logger_format))
#logging level for other modules
logging.basicConfig(format=logger_format, level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.addHandler(logger_file_handler)

class truepool_stats:
    '''gather pool stats using the TruePool RESTful APIs'''
    
    _logging_level = logging.WARNING
    
    HTTP_SUCCESS_OK = 200
    HTTP_TIMEOUT = 5
    
    ##base url strings
    POOL_INFO_API_URL = 'https://truepool.io/v1/pool/info'
    FARMER_STATS_API_URL = 'https://truepool.io/v1/pool/farmer'
    PARTIALS_STATS_API_URL = 'https://truepool.io/v1/pool/partial'
    PAYOUT_STATS_API_URL = 'https://truepool.io/v1/pool/payout_address'

    def __init__(self, logging_level):
        self._farmer_launcher_id = None
        self._pool_blocks_won_prev = 0
        self._farmer_pool_earnings_prev = 0
        self._farmer_pool_earnings_stale = False
    
        self.pool_total_size = 0
        self.pool_total_farmers = 0
        self.pool_minutes_to_win = 0
        self.pool_blocks_won = 0
        self.pool_seconds_since_last_win = 0
        self.farmer_points = 0
        self.farmer_difficulty = 0
        self.farmer_points_percentage = 0
        self.farmer_estimated_size = 0
        self.farmer_ranking = 0
        self.partial_errors_24h = 0
        self.farmer_pool_earnings = 0
        
        #defaults to WARNING otherwise
        if logging_level == 'DEBUG':
            self._logging_level = logging.DEBUG
        elif logging_level == 'INFO':
            self._logging_level = logging.INFO
            
        #logging level for current logger
        logger.setLevel(self._logging_level)
    
    def clear_stats(self):
        self.pool_total_size = 0
        self.pool_total_farmers = 0
        self.pool_minutes_to_win = 0
        self.pool_blocks_won = 0
        self.pool_seconds_since_last_win = 0
        self.farmer_points = 0
        self.farmer_difficulty = 0
        self.farmer_points_percentage = 0
        self.farmer_estimated_size = 0
        self.farmer_ranking = 0
        self.partial_errors_24h = 0
        
    def set_farmer_launcher_id(self, farmer_launcher_id):
        self._farmer_launcher_id = farmer_launcher_id
        
    def collect_stats(self):
        if self._farmer_launcher_id is None:
            raise Exception('Farmer launcher id has not been set. Pool stats can not be collected!')
        
        logger.info('+++ Starting data collection run +++')
        
        try:
            with requests.Session() as session:
                four_score_and_twenty_four_hours_ago = int(datetime.timestamp(datetime.now() - timedelta(hours=24)))
                logger.debug(f'four_score_and_twenty_four_hours_ago: {four_score_and_twenty_four_hours_ago}')
                
                #########################################################
                logger.info('Fetching pool stats...')
                                
                response = session.get(truepool_stats.POOL_INFO_API_URL, timeout=truepool_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == truepool_stats.HTTP_SUCCESS_OK:
                    pool_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)
                    
                    self.pool_total_size = pool_stats_json['total_size']
                    self.pool_total_farmers = pool_stats_json['total_farmers']
                    self.pool_minutes_to_win = pool_stats_json['minutes_to_win']
                    self.pool_blocks_won = pool_stats_json['total_rewards_heights']
                    self.pool_seconds_since_last_win = pool_stats_json['seconds_since_last_win']
                    
                    logger.debug(f'pool_total_size: {self.pool_total_size}')
                    logger.debug(f'pool_total_farmers: {self.pool_total_farmers}')
                    logger.debug(f'pool_minutes_to_win: {self.pool_minutes_to_win}')
                    logger.debug(f'pool_blocks_won: {self.pool_blocks_won}')
                    logger.debug(f'pool_seconds_since_last_win: {self.pool_seconds_since_last_win}')
                else:
                    logger.warning('Failed to connect to API endpoint for pool stats.')
                #########################################################
                
                #########################################################
                logger.info('Fetching farmer stats...')
                                
                #can't be bothered with pagination (meant for the website anyway), 
                #so use a resonable non-standard limit - based on total farmer count
                response = session.get(truepool_stats.FARMER_STATS_API_URL + f'?ordering=-points&limit={self.pool_total_farmers}', 
                                       timeout=truepool_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == truepool_stats.HTTP_SUCCESS_OK:
                    global_farmer_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    farmer_iterator = iter(global_farmer_stats_json)
                    found_farmer = False
                    
                    try:
                        while not found_farmer:
                            current_farmer = next(farmer_iterator)
                            self.farmer_ranking += 1
                            
                            if current_farmer['launcher_id'].strip() == self._farmer_launcher_id:
                                logger.debug('Found the farmer!')
                                found_farmer = True
                    except StopIteration:
                        logger.error('Failed to find farmer based on the launcher id.')
                        raise
                    
                    logger.debug(f'farmer_ranking: {self.farmer_ranking}')
                else:
                    logger.warning('Failed to connect to API endpoint for farmer ranking stats.')
                
                response = session.get(truepool_stats.FARMER_STATS_API_URL + f'/?launcher_id={self._farmer_launcher_id}', 
                                       timeout=truepool_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == truepool_stats.HTTP_SUCCESS_OK:
                    farmer_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results'][0]
                    
                    self.farmer_points = farmer_stats_json['points']
                    self.farmer_difficulty = farmer_stats_json['difficulty']
                    self.farmer_points_percentage = farmer_stats_json['points_percentage']
                    self.farmer_estimated_size = farmer_stats_json['farm_estimated_size']
                    
                    logger.debug(f'farmer_points: {self.farmer_points}')
                    logger.debug(f'farmer_difficulty: {self.farmer_difficulty}')
                    logger.debug(f'farmer_points_percentage: {self.farmer_points_percentage}')
                    logger.debug(f'farmer_estimated_size: {self.farmer_estimated_size}')
                else:
                    logger.warning('Failed to connect to API endpoint for farmer stats.')
                #########################################################
                
                #########################################################
                logger.info('Fetching partials stats...')
                
                #can't be bothered with pagination (meant for the website anyway), 
                #so use a resonable non-standard limit - may have to adjust later on
                response = session.get(truepool_stats.PARTIALS_STATS_API_URL + f'/?launcher_id={self._farmer_launcher_id}' + 
                                       f'&start_timestamp={four_score_and_twenty_four_hours_ago}&limit=500', 
                                       timeout=truepool_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == truepool_stats.HTTP_SUCCESS_OK:
                    partials_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    for partial in partials_stats_json:
                        if partial['error'] is not None:
                            self.partial_errors_24h += 1
                            
                    logger.debug(f'partial_errors_24h: {self.partial_errors_24h}')
                else:
                    logger.warning('Failed to connect to API endpoint for partials stats.')
                #########################################################
                
                #########################################################
                if self._pool_blocks_won_prev != self.pool_blocks_won or self._farmer_pool_earnings_stale:
                    logger.info('Fetching payout stats...')
                    
                    #skip payout reads until the next block win
                    self._pool_blocks_won_prev = self.pool_blocks_won
                    #ensure the stats are refresh until a change is detected (may come with a delay)
                    self._farmer_pool_earnings_stale = True
                    
                    #can't be bothered with pagination (meant for the website anyway), 
                    #so use a resonable non-standard limit - may have to adjust later on
                    response = session.get(truepool_stats.PAYOUT_STATS_API_URL + f'/?farmer={self._farmer_launcher_id}&limit=500', 
                                           timeout=truepool_stats.HTTP_TIMEOUT)
                    
                    logger.debug(f'HTTP response code is: {response.status_code}.')
                
                    if response.status_code == truepool_stats.HTTP_SUCCESS_OK:
                        payouts_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                        
                        #clear existing value before updating
                        self.farmer_pool_earnings = 0
                        
                        for payout in payouts_stats_json:
                            self.farmer_pool_earnings += payout['amount']
                                
                        if self.farmer_pool_earnings != self._farmer_pool_earnings_prev:
                            self._farmer_pool_earnings_prev = self.farmer_pool_earnings
                            self._farmer_pool_earnings_stale = False
                        elif self._farmer_pool_earnings_stale:
                            logger.debug('Farmer pool earnings are stale. Will recheck on next update.')
                                
                        logger.debug(f'farmer_pool_earnings: {self.farmer_pool_earnings}')
                    else:
                        logger.warning('Failed to connect to API endpoint for payout stats.')
                        
                else:
                    logger.info('Skipping payout stats update until next block win.')
                #########################################################
                
        except:
            #uncomment for debugging purposes only
            logger.error(traceback.format_exc())
            raise
            
        logger.info('--- Data collection complete ---')
