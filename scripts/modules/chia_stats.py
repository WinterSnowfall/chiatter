#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 1.70
@date: 16/08/2021

Warning: Built for use with python 3.6+
'''

from chia.util.config import load_config
from chia.rpc.harvester_rpc_client import HarvesterRpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.cmds.farm_funcs import get_average_block_time
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
#uncomment for debugging purposes only
import traceback

##logging configuration block
log_file_full_path = os.path.join('..', 'logs', 'chia_stats.log')
logger_file_handler = RotatingFileHandler(log_file_full_path, maxBytes=104857600, backupCount=2, encoding='utf-8')
logger_format = '%(asctime)s %(levelname)s : %(name)s >>> %(message)s'
logger_file_handler.setFormatter(logging.Formatter(logger_format))
#logging level for other modules
logging.basicConfig(format=logger_format, level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.addHandler(logger_file_handler)

class chia_stats:
    '''gather stats using the chia RPC clients'''
    
    _logging_level = logging.WARNING
    
    def __init__(self, logging_level):
        self._chia_farmed_prev = 0
        self._seconds_since_last_win_prev = 0
        self._seconds_since_last_win_stale = False
        
        self.og_size = 0
        self.portable_size = 0
        self.plots_k32_og = 0
        self.plots_k33_og = 0
        self.plots_k32_portable = 0
        self.plots_k33_portable = 0
        self.sync_status = False
        self.network_space_size = 0
        self.og_time_to_win = 0
        self.portable_time_to_win = 0
        self.current_height = 0
        self.wallet_funds = 0
        self.chia_farmed = 0
        self.seconds_since_last_win = 0
        
        #defaults to WARNING otherwise
        if logging_level == 'DEBUG':
            self._logging_level = logging.DEBUG
        elif logging_level == 'INFO':
            self._logging_level = logging.INFO
            
        #logging level for current logger
        logger.setLevel(self._logging_level)
        
        logger.debug('Loading chia configuration...')
        
        self._config = load_config(DEFAULT_ROOT_PATH, 'config.yaml')
        
        self._hostname = self._config['self_hostname']
        self._harvester_port = self._config['harvester']['rpc_port']
        self._fullnode_port = self._config['full_node']['rpc_port']
        self._wallet_port = self._config['wallet']['rpc_port']
    
    def clear_stats(self):
        self.og_size = 0
        self.portable_size = 0
        self.plots_k32_og = 0
        self.plots_k33_og = 0
        self.plots_k32_portable = 0
        self.plots_k33_portable = 0
        self.sync_status = False
        self.network_space_size = 0
        self.og_time_to_win = 0
        self.portable_time_to_win = 0
        self.current_height = 0
        self.wallet_funds = 0
        self.chia_farmed = 0
    
    async def collect_stats(self):
        logger.info('+++ Starting data collection run +++')
        
        logger.info('Initializing clients...')
        
        harvester = await HarvesterRpcClient.create(self._hostname, self._harvester_port, 
                                                    DEFAULT_ROOT_PATH, self._config)
        fullnode = await FullNodeRpcClient.create(self._hostname, self._fullnode_port, 
                                                  DEFAULT_ROOT_PATH, self._config)
        wallet = await WalletRpcClient.create(self._hostname, self._wallet_port, 
                                              DEFAULT_ROOT_PATH, self._config)
        
        try:
            logger.info('Fetching harvester state...')
            #########################################################
            plots = await harvester.get_plots()
            
            for plot in plots['plots']:
                if plot['pool_public_key'] is not None:
                    self.og_size += plot["file_size"]
                    
                    if plot['size'] == 32:
                        #logger.debug('Found k32 plot!')
                        self.plots_k32_og += 1
                    elif plot['size'] == 33:
                        #logger.debug('Found k33 plot!')
                        self.plots_k33_og += 1
                    
                else:
                    self.portable_size += plot['file_size']
                    
                    if plot['size'] == 32:
                        #logger.debug('Found k32 plot!')
                        self.plots_k32_portable += 1
                    elif plot['size'] == 33:
                        #logger.debug('Found k33 plot!')
                        self.plots_k33_portable += 1
                        
            logger.debug(f'og_size: {self.og_size}')
            logger.debug(f'portable_size: {self.portable_size}')
            logger.debug(f'plots_k32_og: {self.plots_k32_og}')
            logger.debug(f'plots_k33_og: {self.plots_k33_og}')
            logger.debug(f'plots_k32_portable: {self.plots_k32_portable}')
            logger.debug(f'plots_k33_portable: {self.plots_k33_portable}')
            #########################################################
            
            logger.info('Fetching blockchain state...')
            #########################################################
            blockchain = await fullnode.get_blockchain_state()
            
            self.sync_status = blockchain['sync'].get('synced')
            self.network_space_size = blockchain['space']
            
            average_block_time = await get_average_block_time(self._fullnode_port)
            self.og_time_to_win = int((average_block_time) / (self.og_size / self.network_space_size))
            self.portable_time_to_win = int((average_block_time) / (self.portable_size / self.network_space_size))
            
            logger.debug(f'sync_status: {self.sync_status}')
            logger.debug(f'network_space_size: {self.network_space_size}')
            logger.debug(f'og_time_to_win: {self.og_time_to_win}')
            logger.debug(f'portable_time_to_win: {self.portable_time_to_win}')
            #########################################################
            
            logger.info('Fetching wallet state...')
            #########################################################
            farmed_stat = await wallet.get_farmed_amount()
            self.chia_farmed = farmed_stat['farmed_amount']
            if self.chia_farmed != self._chia_farmed_prev:
                self._chia_farmed_prev = self.chia_farmed
                self._seconds_since_last_win_stale = True
                    
            self.current_height = await wallet.get_height_info()
            main_wallet = await wallet.get_wallets()
            #assume only one wallet exists - might want to alter it in the future
            main_wallet_balance = await wallet.get_wallet_balance(main_wallet[0]["id"])
            self.wallet_funds = main_wallet_balance.get('confirmed_wallet_balance')
            
            logger.debug(f'chia_farmed: {self.chia_farmed}')
            logger.debug(f'current_height: {self.current_height}')
            logger.debug(f'wallet_funds: {self.wallet_funds}')
            
            #simple transaction-based block win time detection logic
            if self._seconds_since_last_win_stale:
                wallet_transactions = await wallet.get_transactions(main_wallet[0]["id"])
                max_time = 0
                
                for transaction_record in wallet_transactions:
                    if int(transaction_record.amount) == 250000000000:
                        logger.debug('Found transaction with a block win share amount.')
                        current_time = int(transaction_record.created_at_time)
                        if current_time > max_time:
                            max_time = current_time
                
                self.seconds_since_last_win = int(datetime.timestamp(datetime.now())) - max_time
                
                if self.seconds_since_last_win != self._seconds_since_last_win_prev:
                    self._seconds_since_last_win_prev = self.seconds_since_last_win
                    self._seconds_since_last_win_stale = False
                elif self._farmer_pool_earnings_stale:
                    logger.debug('Seconds since last win amount is stale. Will recheck on next update.')
                    
                logger.debug(f'seconds_since_last_win: {self.seconds_since_last_win}')
            else:
                logger.info('Skipping seconds since last win update until next block win.')
            #########################################################
            
        except:
            #uncomment for debugging purposes only
            logger.error(traceback.format_exc())
            raise
            
        finally:
            harvester.close()
            fullnode.close()
            wallet.close()
            
        logger.info('--- Data collection complete ---')
