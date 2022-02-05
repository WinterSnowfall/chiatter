#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 2.63
@date: 05/02/2022

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
log_file_full_path = os.path.join('..', 'logs', 'openchia_stats.log')
logger_file_handler = RotatingFileHandler(log_file_full_path, maxBytes=16777216, backupCount=2, encoding='utf-8')
logger_format = '%(asctime)s %(levelname)s : %(name)s >>> %(message)s'
logger_file_handler.setFormatter(logging.Formatter(logger_format))
#logging level for other modules
logging.basicConfig(format=logger_format, level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.addHandler(logger_file_handler)

class openchia_stats:
    '''gather pool stats using the OpenChia RESTful APIs'''
    
    _logging_level = logging.WARNING
    
    HTTP_SUCCESS_OK = 200
    HTTP_TIMEOUT = 10
    
    #ordering used for the farmer ranking query
    #options: points, points_pplns (- stands for descending)
    LAUNCHER_ORDERING = '-points_pplns'
    
    OPENCHIA_BASE_URL = 'https://openchia.io'
    ##API endpoint URLs
    POOL_STATS_API_URL = OPENCHIA_BASE_URL + '/api/v1.0/stats'
    LAUNCHER_STATS_API_URL = OPENCHIA_BASE_URL + '/api/v1.0/launcher'
    PAYOUT_STATS_API_URL = OPENCHIA_BASE_URL + '/api/v1.0/payoutaddress'
    PARTIAL_STATS_API_URL = OPENCHIA_BASE_URL + '/api/v1.0/partial'
    
    ##Pagination limits for various queries
    PAYOUT_PAGINATION_LIMIT = '2000'
    #24h partials should average out around ~600, but also cater for increased
    #partial count (can potentially be set to double that amount by farmers)
    PARTIAL_PAGINATION_LIMIT = '1400'

    def __init__(self, logging_level):
        self._launcher_id = None
        self._pool_rewards_blocks_prev = 0
        self._launcher_pool_earnings_prev = 0
        self._launcher_pool_earnings_stale = False
    
        self.pool_space = 0
        self.pool_farmers = 0
        self.pool_estimate_win = 0
        self.pool_rewards_blocks = 0
        self.pool_time_since_last_win = 0
        self.launcher_points = 0
        self.launcher_points_pplns = 0
        self.launcher_difficulty = 0
        self.launcher_points_of_total = 0
        self.launcher_share_pplns = 0
        self.launcher_estimated_size = 0
        self.launcher_ranking = 0
        self.launcher_pool_earnings = 0
        self.partial_errors_24h = 0
        
        #defaults to WARNING otherwise
        if logging_level == 'DEBUG':
            self._logging_level = logging.DEBUG
        elif logging_level == 'INFO':
            self._logging_level = logging.INFO
            
        #logging level for current logger
        logger.setLevel(self._logging_level)
    
    def clear_stats(self):
        self.pool_space = 0
        self.pool_farmers = 0
        self.pool_estimate_win = 0
        self.pool_rewards_blocks = 0
        self.pool_time_since_last_win = 0
        self.launcher_points = 0
        self.launcher_points_pplns = 0
        self.launcher_difficulty = 0
        self.launcher_points_of_total = 0
        self.launcher_share_pplns = 0
        self.launcher_estimated_size = 0
        self.launcher_ranking = 0
        self.partial_errors_24h = 0
        
    def set_launcher_id(self, launcher_id):
        self._launcher_id = launcher_id
        
    def collect_stats(self):
        if self._launcher_id is None:
            raise Exception('Launcher id has not been set. Pool stats can not be collected!')
        
        logger.info('+++ Starting data collection run +++')
        
        try:
            with requests.Session() as session:
                four_score_and_twenty_four_hours_ago = int(datetime.timestamp(datetime.now() - timedelta(hours=24)))
                logger.debug(f'four_score_and_twenty_four_hours_ago: {four_score_and_twenty_four_hours_ago}')
                
                #########################################################
                logger.info('Fetching pool stats...')
                                
                response = session.get(openchia_stats.POOL_STATS_API_URL, timeout=openchia_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == openchia_stats.HTTP_SUCCESS_OK:
                    pool_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)
                    
                    self.pool_space = pool_stats_json['pool_space']
                    self.pool_farmers = pool_stats_json['farmers_active']
                    self.pool_estimate_win = pool_stats_json['estimate_win']
                    self.pool_rewards_blocks = pool_stats_json['rewards_blocks']
                    self.pool_time_since_last_win = pool_stats_json['time_since_last_win']
                    
                    logger.debug(f'pool_space: {self.pool_space}')
                    logger.debug(f'pool_farmers: {self.pool_farmers}')
                    logger.debug(f'pool_estimate_win: {self.pool_estimate_win}')
                    logger.debug(f'pool_rewards_blocks: {self.pool_rewards_blocks}')
                    logger.debug(f'pool_time_since_last_win: {self.pool_time_since_last_win}')
                else:
                    logger.warning('Failed to connect to API endpoint for pool stats.')
                #########################################################
                
                #########################################################
                logger.info('Fetching launcher stats...')
                                
                #can't be bothered with pagination (meant for the website anyway), 
                #so use a resonable non-standard limit - based on farmer count
                response = session.get(openchia_stats.LAUNCHER_STATS_API_URL + f'?ordering={openchia_stats.LAUNCHER_ORDERING}' + 
                                       f'&limit={self.pool_farmers}', timeout=openchia_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == openchia_stats.HTTP_SUCCESS_OK:
                    global_farmer_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    launcher_iterator = iter(global_farmer_stats_json)
                    found_launcher = False
                    
                    try:
                        while not found_launcher:
                            current_farmer = next(launcher_iterator)
                            self.launcher_ranking += 1
                            
                            if current_farmer['launcher_id'].strip() == self._launcher_id:
                                logger.debug('Found the launcher!')
                                found_launcher = True
                    except StopIteration:
                        logger.error('Failed to find an entry based on the launcher id.')
                        raise
                    
                    logger.debug(f'launcher_ranking: {self.launcher_ranking}')
                else:
                    logger.warning('Failed to connect to API endpoint for launcher ranking stats.')
                
                response = session.get(openchia_stats.LAUNCHER_STATS_API_URL + f'/{self._launcher_id}', 
                                       timeout=openchia_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == openchia_stats.HTTP_SUCCESS_OK:
                    launcher_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)
                    
                    self.launcher_points = launcher_stats_json['points']
                    self.launcher_points_pplns = launcher_stats_json['points_pplns']
                    self.launcher_difficulty = launcher_stats_json['difficulty']
                    self.launcher_points_of_total = launcher_stats_json['points_of_total']
                    self.launcher_share_pplns = launcher_stats_json['share_pplns']
                    self.launcher_estimated_size = launcher_stats_json['estimated_size']
                    
                    logger.debug(f'launcher_points: {self.launcher_points}')
                    logger.debug(f'launcher_points_pplns: {self.launcher_points_pplns}')
                    logger.debug(f'launcher_difficulty: {self.launcher_difficulty}')
                    logger.debug(f'launcher_points_of_total: {self.launcher_points_of_total}')
                    logger.debug(f'launcher_share_pplns: {self.launcher_share_pplns}')
                    logger.debug(f'launcher_estimated_size: {self.launcher_estimated_size}')
                else:
                    logger.warning('Failed to connect to API endpoint for launcher stats.')
                #########################################################
                
                #########################################################
                if self._pool_rewards_blocks_prev != self.pool_rewards_blocks or self._launcher_pool_earnings_stale:
                    logger.info('Fetching payout (address) stats...')
                    
                    #skip payout reads until the next block win
                    self._pool_rewards_blocks_prev = self.pool_rewards_blocks
                    #ensure the stats are refresh until a change is detected (may come with a delay)
                    self._launcher_pool_earnings_stale = True
                    
                    #can't be bothered with pagination (meant for the website anyway), 
                    #so use a resonable non-standard limit - may have to adjust later on
                    response = session.get(openchia_stats.PAYOUT_STATS_API_URL + f'/?launcher={self._launcher_id}&limit=' +
                                           openchia_stats.PAYOUT_PAGINATION_LIMIT, timeout=openchia_stats.HTTP_TIMEOUT)
                    
                    logger.debug(f'HTTP response code is: {response.status_code}.')
                
                    if response.status_code == openchia_stats.HTTP_SUCCESS_OK:
                        payouts_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                        
                        #clear existing value before updating
                        self.launcher_pool_earnings = 0
                        
                        for payout in payouts_stats_json:
                            self.launcher_pool_earnings += payout['amount']
                                
                        if (self.launcher_pool_earnings != self._launcher_pool_earnings_prev or 
                            #useful to skip repeated checks when joining a new pool, as initial earnings will be 0
                            self.launcher_pool_earnings == 0):
                            
                            self._launcher_pool_earnings_prev = self.launcher_pool_earnings
                            self._launcher_pool_earnings_stale = False
                            
                        elif self._launcher_pool_earnings_stale:
                            logger.debug('Launcher pool earnings are stale. Will recheck on next update.')
                                
                        logger.debug(f'launcher_pool_earnings: {self.launcher_pool_earnings}')
                    else:
                        logger.warning('Failed to connect to API endpoint for payout stats.')
                        
                else:
                    logger.info('Skipping payout stats update until next block win.')
                #########################################################
                
                #########################################################
                logger.info('Fetching partials stats...')
                
                #can't be bothered with pagination (meant for the website anyway), 
                #so use a resonable non-standard limit - may have to adjust later on
                response = session.get(openchia_stats.PARTIAL_STATS_API_URL + f'?launcher={self._launcher_id}' + 
                                       f'&min_timestamp={four_score_and_twenty_four_hours_ago}&limit=' +
                                       openchia_stats.PARTIAL_PAGINATION_LIMIT, timeout=openchia_stats.HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code is: {response.status_code}.')
            
                if response.status_code == openchia_stats.HTTP_SUCCESS_OK:
                    partials_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    for partial in partials_stats_json:
                        if partial['error'] is not None:
                            self.partial_errors_24h += 1
                            
                    logger.debug(f'partial_errors_24h: {self.partial_errors_24h}')
                else:
                    logger.warning('Failed to connect to API endpoint for partials stats.')
                #########################################################
                
        except:
            #uncomment for debugging purposes only
            logger.error(traceback.format_exc())
            raise
            
        logger.info('--- Data collection complete ---')
