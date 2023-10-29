#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 3.23
@date: 28/10/2023

Warning: Built for use with python 3.6+
'''

import json
import requests
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
# uncomment for debugging purposes only
#import traceback

# logging configuration block
LOG_FILE_PATH = os.path.join('..', 'logs', 'openchia_stats.log')
logger_file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=25165824, backupCount=1, encoding='utf-8')
LOGGER_FORMAT = '%(asctime)s %(levelname)s : %(name)s >>> %(message)s'
logger_file_handler.setFormatter(logging.Formatter(LOGGER_FORMAT))
# logging level for other modules
logging.basicConfig(format=LOGGER_FORMAT, level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.addHandler(logger_file_handler)

class openchia_stats:
    '''gather pool stats using the OpenChia RESTful APIs'''
    
    _logging_level = logging.WARNING
    
    _HTTP_OK = 200
    _HTTP_TIMEOUT = 30
    
    # ordering used for the farmer ranking query
    # options: points, points_pplns (- stands for descending)
    _LAUNCHER_ORDERING = '-points_pplns'
    
    _OPENCHIA_BASE_URL = 'https://openchia.io'
    # API endpoint URLs
    _BLOCK_STATS_API_URL = ''.join((_OPENCHIA_BASE_URL, '/api/v1.0/block'))
    _POOL_STATS_API_URL = ''.join((_OPENCHIA_BASE_URL, '/api/v1.0/stats'))
    _LAUNCHER_STATS_API_URL = ''.join((_OPENCHIA_BASE_URL, '/api/v1.0/launcher'))

    def __init__(self, logging_level):
        self._launcher_id = None
        # will default to fetching the current $ exchange value of XCH
        self._xch_current_price_currency = 'usd'
        
        self._pool_rewards_blocks_prev = 0
        self._block_timestamp_prev = 0
        self._block_seconds_since_last_win_stale = False
        
        self.pool_space = 0
        self.pool_farmers = 0
        self.pool_estimate_win = 0
        self.pool_rewards_blocks = 0
        self.pool_time_since_last_win = 0
        self.pool_xch_current_price = 0
        self.launcher_points = 0
        self.launcher_points_pplns = 0
        self.launcher_difficulty = 0
        self.launcher_share_pplns = 0
        self.launcher_estimated_size = 0
        self.launcher_ranking = 0
        self.launcher_pool_earnings = 0
        self.launcher_partial_errors_24h = 0
        self.seconds_since_last_win = 0
        
        # defaults to 'WARNING' otherwise
        if logging_level == 'DEBUG':
            self._logging_level = logging.DEBUG
        elif logging_level == 'INFO':
            self._logging_level = logging.INFO
        
        # logging level for current logger
        logger.setLevel(self._logging_level)
    
    def clear_stats(self):
        self._pool_rewards_blocks_prev = 0
        self._block_timestamp_prev = 0
        self._block_seconds_since_last_win_stale = False
        
        self.pool_space = 0
        self.pool_farmers = 0
        self.pool_estimate_win = 0
        self.pool_rewards_blocks = 0
        self.pool_time_since_last_win = 0
        self.pool_xch_current_price = 0
        self.launcher_points = 0
        self.launcher_points_pplns = 0
        self.launcher_difficulty = 0
        self.launcher_share_pplns = 0
        self.launcher_estimated_size = 0
        self.launcher_ranking = 0
        self.launcher_pool_earnings = 0
        self.launcher_partial_errors_24h = 0
        self.seconds_since_last_win = 0
    
    def set_launcher_id(self, launcher_id):
        self._launcher_id = launcher_id
    
    def set_xch_current_price_currency(self, currency):
        self._xch_current_price_currency = currency
    
    def collect_stats(self):
        if self._launcher_id is None:
            raise Exception('Launcher id has not been set. Pool stats can not be collected!')
        
        logger.info('***** Starting data collection run *****')
        
        self.launcher_ranking = 0
        
        try:
            with requests.Session() as session:
                four_score_and_twenty_four_hours_ago = int(datetime.timestamp(datetime.now() - timedelta(hours=24)))
                logger.debug(f'four_score_and_twenty_four_hours_ago: {four_score_and_twenty_four_hours_ago}')
                
                #########################################################
                logger.info('Fetching pool stats...')
                
                response = session.get(openchia_stats._POOL_STATS_API_URL, timeout=openchia_stats._HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code: {response.status_code}')
                
                if response.status_code == openchia_stats._HTTP_OK:
                    pool_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)
                    
                    self.pool_space = pool_stats_json['pool_space']
                    self.pool_farmers = pool_stats_json['farmers_active']
                    self.pool_estimate_win = pool_stats_json['estimate_win']
                    self.pool_rewards_blocks = pool_stats_json['rewards_blocks']
                    self.pool_time_since_last_win = pool_stats_json['time_since_last_win']
                    self.pool_xch_current_price = pool_stats_json['xch_current_price'][self._xch_current_price_currency]
                    
                    logger.debug(f'pool_space: {self.pool_space}')
                    logger.debug(f'pool_farmers: {self.pool_farmers}')
                    logger.debug(f'pool_estimate_win: {self.pool_estimate_win}')
                    logger.debug(f'pool_rewards_blocks: {self.pool_rewards_blocks}')
                    logger.debug(f'pool_time_since_last_win: {self.pool_time_since_last_win}')
                    logger.debug(f'pool_xch_current_price: {self.pool_xch_current_price}')
                else:
                    logger.warning('Failed to connect to API endpoint for pool stats.')
                #########################################################
                
                # trigger won block read if the number of reported blocks changes
                if self._pool_rewards_blocks_prev != self.pool_rewards_blocks:
                    self._block_seconds_since_last_win_stale = True
                    # skip payout & won block reads until the next block win
                    self._pool_rewards_blocks_prev = self.pool_rewards_blocks
                
                #########################################################
                logger.info('Fetching launcher stats...')
                
                # can't be bothered with pagination (meant for the website anyway), 
                # so use a resonable non-standard limit - based on farmer count
                response = session.get(''.join((openchia_stats._LAUNCHER_STATS_API_URL, '/?ordering=', 
                                                openchia_stats._LAUNCHER_ORDERING, '&limit=', str(self.pool_farmers))), 
                                        timeout=openchia_stats._HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code: {response.status_code}')
                
                if response.status_code == openchia_stats._HTTP_OK:
                    global_farmer_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                    
                    launcher_iterator = iter(global_farmer_stats_json)
                    found_launcher = False
                    
                    try:
                        while not found_launcher:
                            current_farmer = next(launcher_iterator)
                            self.launcher_ranking += 1

                            if current_farmer['launcher_id'].strip() == self._launcher_id:
                                found_launcher = True
                                logger.debug('Found the launcher!')
                    
                    except StopIteration:
                        logger.error('Failed to find an entry based on the launcher id.')
                        raise
                    
                    logger.debug(f'launcher_ranking: {self.launcher_ranking}')
                else:
                    logger.warning('Failed to connect to API endpoint for launcher ranking stats.')
                
                response = session.get(''.join((openchia_stats._LAUNCHER_STATS_API_URL, '/', self._launcher_id)), 
                                       timeout=openchia_stats._HTTP_TIMEOUT)
                
                logger.debug(f'HTTP response code: {response.status_code}')
                
                if response.status_code == openchia_stats._HTTP_OK:
                    launcher_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)
                    
                    self.launcher_points = launcher_stats_json['points']
                    self.launcher_points_pplns = launcher_stats_json['points_pplns']
                    self.launcher_difficulty = launcher_stats_json['difficulty']
                    self.launcher_share_pplns = launcher_stats_json['share_pplns']
                    self.launcher_estimated_size = launcher_stats_json['estimated_size']
                    self.launcher_pool_earnings = launcher_stats_json['payout']['total_paid']
                    self.launcher_partial_errors_24h = launcher_stats_json['partials']['failed']
                    
                    logger.debug(f'launcher_points: {self.launcher_points}')
                    logger.debug(f'launcher_points_pplns: {self.launcher_points_pplns}')
                    logger.debug(f'launcher_difficulty: {self.launcher_difficulty}')
                    logger.debug(f'launcher_share_pplns: {self.launcher_share_pplns}')
                    logger.debug(f'launcher_estimated_size: {self.launcher_estimated_size}')
                    logger.debug(f'launcher_pool_earnings: {self.launcher_pool_earnings}')
                    logger.debug(f'launcher_partial_errors_24h: {self.launcher_partial_errors_24h}')
                else:
                    logger.warning('Failed to connect to API endpoint for launcher stats.')
                #########################################################
                
                #########################################################
                if self._block_seconds_since_last_win_stale:
                    logger.info('Fetching block stats...')
                    
                    # only get the latest won block for the configured launcher
                    response = session.get(''.join((openchia_stats._BLOCK_STATS_API_URL, '/?farmed_by=', 
                                                    self._launcher_id, '&ordering=timestamp&limit=1')), 
                                           timeout=openchia_stats._HTTP_TIMEOUT)
                    
                    logger.debug(f'HTTP response code: {response.status_code}')
                    
                    try:
                        if response.status_code == openchia_stats._HTTP_OK:
                            block_stats_json = json.loads(response.text, object_pairs_hook=OrderedDict)['results']
                            block_timestamp = int(block_stats_json[0]['timestamp'])
                            logger.debug(f'block_timestamp: {block_timestamp}')
                            logger.debug(f'_block_timestamp_prev: {self._block_timestamp_prev}')
                            
                            if self._block_timestamp_prev != block_timestamp:
                                self._block_seconds_since_last_win_stale = False
                                self._block_timestamp_prev = block_timestamp
                                
                            elif self._block_seconds_since_last_win_stale:
                                logger.debug('Last won block timestamp is stale. Will recheck on next update.')
                        
                        else:
                            logger.warning('Failed to connect to API endpoint for block stats.')
                    
                    # if no results are returned then the launcher has not won any blocks in the pool
                    except IndexError:
                        self._block_seconds_since_last_win_stale = False
                        logger.info('No won blocks detected for configured launcher.')
                else:
                    logger.info('Skipping block stats update until next block win.')
                
                # calculate time elapsed since last block win based on stored _prev value
                if self._block_timestamp_prev != 0:
                    self.seconds_since_last_win = int(datetime.timestamp(datetime.now())) - self._block_timestamp_prev
                else:
                    logger.debug('Last won block timestamp is 0, unable to calculate time since last win.')
                
                logger.debug(f'seconds_since_last_win: {self.seconds_since_last_win}')
                #########################################################
                
        except StopIteration:
            raise
        
        except Exception as exception:
            logger.error(f'Encountered following exception: {type(exception)} {exception}')
            # uncomment for debugging purposes only
            #logger.error(traceback.format_exc())
            raise
        
        logger.info('***** Data collection complete *****')
