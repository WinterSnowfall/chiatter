#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 2.80
@date: 18/03/2022

Warning: Built for use with python 3.6+
'''

from chia.util.config import load_config
from chia.rpc.harvester_rpc_client import HarvesterRpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.util import bech32m
from chia.cmds.farm_funcs import get_average_block_time
import logging
import os
import binascii
from aiohttp.client_exceptions import ClientConnectorError
from datetime import datetime
from logging.handlers import RotatingFileHandler
#uncomment for debugging purposes only
#import traceback

##logging configuration block
log_file_full_path = os.path.join('..', 'logs', 'chia_stats.log')
logger_file_handler = RotatingFileHandler(log_file_full_path, maxBytes=16777216, backupCount=2, encoding='utf-8')
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
        self._self_pooling_contract_address = None
        self._decoded_puzzle_hash = None
        self._chia_farmed_prev = 0
        self._seconds_since_last_win_stale = False
        self._last_win_max_time = 0
        
        self.og_size = 0
        self.portable_size = 0
        self.sp_portable_size = 0
        self.plots_og_k32 = 0
        self.plots_og_k33 = 0
        self.plots_og_k34 = 0
        self.plots_portable_k32 = 0
        self.plots_portable_k33 = 0
        self.plots_portable_k34 = 0
        self.plots_sp_portable_k32 = 0
        self.plots_sp_portable_k33 = 0
        self.plots_sp_portable_k34 = 0
        self.sync_status = False
        self.difficulty = 0
        self.network_space_size = 0
        self.mempool_size = 0
        self.full_node_connections = 0
        self.og_time_to_win = 0
        self.portable_time_to_win = 0
        self.sp_portable_time_to_win = 0
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
        self.sp_portable_size = 0
        self.plots_og_k32 = 0
        self.plots_og_k33 = 0
        self.plots_og_k34 = 0
        self.plots_portable_k32 = 0
        self.plots_portable_k33 = 0
        self.plots_portable_k34 = 0
        self.plots_sp_portable_k32 = 0
        self.plots_sp_portable_k33 = 0
        self.plots_sp_portable_k34 = 0
        self.sync_status = False
        self.difficulty = 0
        self.network_space_size = 0
        self.mempool_size = 0
        self.full_node_connections = 0
        self.og_time_to_win = 0
        self.portable_time_to_win = 0
        self.sp_portable_time_to_win = 0
        self.current_height = 0
        
    def set_self_pooling_contract_address(self, self_pooling_contract_address):
        self._self_pooling_contract_address = self_pooling_contract_address
        
        decoded_bytes = bech32m.decode_puzzle_hash(self._self_pooling_contract_address)
        self._decoded_puzzle_hash = '0x' + binascii.hexlify(decoded_bytes).decode('utf8')
        
        logger.debug(f'_decoded_puzzle_hash: {self._decoded_puzzle_hash}')
    
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
                        #logger.debug('Found k32 OG plot!')
                        self.plots_og_k32 += 1
                    elif plot['size'] == 33:
                        #logger.debug('Found k33 OG plot!')
                        self.plots_og_k33 += 1
                    elif plot['size'] == 34:
                        #logger.debug('Found k34 OG plot!')
                        self.plots_og_k34 += 1
                    
                else:
                    if (self._self_pooling_contract_address is not None and 
                        plot['pool_contract_puzzle_hash'] == self._decoded_puzzle_hash):
                        if plot['size'] == 32:
                            #logger.debug('Found k32 self-pooling plot!')
                            self.plots_sp_portable_k32 += 1
                        elif plot['size'] == 33:
                            #logger.debug('Found k33 self-pooling plot!')
                            self.plots_sp_portable_k33 += 1
                        elif plot['size'] == 34:
                            #logger.debug('Found k34 self-pooling plot!')
                            self.plots_sp_portable_k34 += 1
                        self.sp_portable_size += plot['file_size']
                    else:
                        if plot['size'] == 32:
                            #logger.debug('Found k32 portable plot!')
                            self.plots_portable_k32 += 1
                        elif plot['size'] == 33:
                            #logger.debug('Found k33 portable plot!')
                            self.plots_portable_k33 += 1
                        elif plot['size'] == 34:
                            #logger.debug('Found k34 portable plot!')
                            self.plots_portable_k34 += 1
                        self.portable_size += plot['file_size']
                        
            logger.debug(f'og_size: {self.og_size}')
            logger.debug(f'portable_size: {self.portable_size}')
            logger.debug(f'sp_portable_size: {self.sp_portable_size}')
            logger.debug(f'plots_og_k32: {self.plots_og_k32}')
            logger.debug(f'plots_og_k33: {self.plots_og_k33}')
            logger.debug(f'plots_og_k34: {self.plots_og_k34}')
            logger.debug(f'plots_portable_k32: {self.plots_portable_k32}')
            logger.debug(f'plots_portable_k33: {self.plots_portable_k33}')
            logger.debug(f'plots_portable_k34: {self.plots_portable_k34}')
            logger.debug(f'plots_sp_portable_k32: {self.plots_sp_portable_k32}')
            logger.debug(f'plots_sp_portable_k33: {self.plots_sp_portable_k33}')
            logger.debug(f'plots_sp_portable_k34: {self.plots_sp_portable_k34}')
            #########################################################
            
            logger.info('Fetching blockchain state...')
            #########################################################
            blockchain = await fullnode.get_blockchain_state()
            
            self.sync_status = blockchain['sync']['synced']
            self.difficulty = blockchain['difficulty']
            self.network_space_size = blockchain['space']
            self.mempool_size = blockchain['mempool_size']
            
            connections = await fullnode.get_connections()
            
            for connection in connections:
                #only count full node connections (type 1)
                if connection['type'] == 1:
                    self.full_node_connections += 1
            
            average_block_time = await get_average_block_time(self._fullnode_port)
            
            if self.og_size != 0:
                self.og_time_to_win = int((average_block_time) / 
                                          (self.og_size / self.network_space_size))           
            if self.portable_size != 0:
                self.portable_time_to_win = int((average_block_time) / 
                                                (self.portable_size / self.network_space_size))
            if self.sp_portable_size != 0:
                self.sp_portable_time_to_win = int((average_block_time) / 
                                                   (self.sp_portable_size / self.network_space_size))
            
            logger.debug(f'sync_status: {self.sync_status}')
            logger.debug(f'difficulty: {self.difficulty}')
            logger.debug(f'network_space_size: {self.network_space_size}')
            logger.debug(f'mempool_size: {self.mempool_size}')
            logger.debug(f'full_node_connections: {self.full_node_connections}')
            logger.debug(f'og_time_to_win: {self.og_time_to_win}')
            logger.debug(f'portable_time_to_win: {self.portable_time_to_win}')
            logger.debug(f'sp_portable_time_to_win: {self.sp_portable_time_to_win}')
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
                
                for transaction_record in wallet_transactions:
                    if int(transaction_record.amount) == 250000000000:
                        logger.debug('Found transaction with a block win share amount.')
                        current_time = int(transaction_record.created_at_time)
                        if current_time > self._last_win_max_time:
                            self._last_win_max_time = current_time
                            
                if self._last_win_max_time == 0:
                    #this may currently happen due to a hard limit of 50 transactions (bug) in the RPC API
                    logger.warning('Unable to find a valid block win transaction.')
                            
                self._seconds_since_last_win_stale = False
            else:
                logger.info('Skipping _last_win_max_time update until next block win.')
            
            if self._last_win_max_time != 0:
                self.seconds_since_last_win = int(datetime.timestamp(datetime.now())) - self._last_win_max_time
            else:
                self.seconds_since_last_win = 0
                
            logger.debug(f'seconds_since_last_win: {self.seconds_since_last_win}')
            #########################################################
            
        except ClientConnectorError:
            logger.warning('Chia RPC API call failed. Full node may be down.')
            
        except Exception as exception:
            logger.error(f'Encountered following exception: {type(exception)} {exception}')
            #uncomment for debugging purposes only
            #logger.error(traceback.format_exc())
            raise
            
        finally:
            harvester.close()
            fullnode.close()
            wallet.close()
            
        logger.info('--- Data collection complete ---')
