#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 1.20
@date: 28/07/2021

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
from logging.handlers import RotatingFileHandler
#uncomment for debugging purposes only
import traceback

##logging configuration block
log_file_full_path = os.path.join('..', 'logs', 'chia_stats.log')
logger_file_handler = RotatingFileHandler(log_file_full_path, maxBytes=8388608, backupCount=1, encoding='utf-8')
logger_format = '%(asctime)s %(levelname)s >>> chia_stats >>> %(message)s'
logger_file_handler.setFormatter(logging.Formatter(logger_format))
#logging level for other modules
logging.basicConfig(format=logger_format, level=logging.INFO) #DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = logging.getLogger(__name__)
#logging level for current logger
logger.setLevel(logging.INFO) #DEBUG, INFO, WARNING, ERROR, CRITICAL
logger.addHandler(logger_file_handler)

class chia_stats:
    '''gather stats using the chia sdk/client'''
    
    plots_k32_og = 0
    plots_k33_og = 0
    plots_k32_portable = 0
    plots_k33_portable = 0
    og_count = 0
    portable_count = 0
    og_size = 0
    portable_size = 0
    sync_status = False
    total_size = 0
    og_time_to_win = 0
    current_height = 0
    wallet_funds = 0
    
    harvester = None
    fullnode = None
    wallet = None
    
    def clear_stats(self):
        #note to self - it might make sense to accumulate some stats in 
        #the future, depending on what grafana charts are being exposed
        self.plots_k32_og = 0
        self.plots_k33_og = 0
        self.plots_k32_portable = 0
        self.plots_k33_portable = 0
        self.og_count = 0
        self.portable_count = 0
        self.og_size = 0
        self.portable_size = 0
        self.sync_status = False
        self.total_size = 0
        self.og_time_to_win = 0
        self.current_height = 0
        self.wallet_funds = 0
    
    async def collect_stats(self):
        logger.info('+++ Starting data collection run +++')
        
        config = load_config(DEFAULT_ROOT_PATH, 'config.yaml')
        
        self_hostname = config['self_hostname']
        harvester_port = config['harvester']['rpc_port']
        fullnode_port = config['full_node']['rpc_port']
        wallet_port = config['wallet']['rpc_port']
        
        logger.info('Initializing clients...')
        
        self.harvester = await HarvesterRpcClient.create(self_hostname, harvester_port, DEFAULT_ROOT_PATH, config)
        self.fullnode = await FullNodeRpcClient.create(self_hostname, fullnode_port, DEFAULT_ROOT_PATH, config)
        self.wallet = await WalletRpcClient.create(self_hostname, wallet_port, DEFAULT_ROOT_PATH, config)
        
        try:
            logger.info('Fetching harvester state...')
            #########################################################
            plots = await self.harvester.get_plots()
            
            for plot in plots['plots']:
                if plot['pool_public_key'] is not None:
                    self.og_count += 1
                    self.og_size += plot["file_size"]
                    
                    if plot['size'] == 32:
                        logger.debug('Found k32 plot!')
                        self.plots_k32_og += 1
                    elif plot['size'] == 33:
                        logger.debug('Found k33 plot!')
                        self.plots_k33_og += 1
                    
                else:
                    self.portable_count += 1
                    self.portable_size += plot['file_size']
                    
                    if plot['size'] == 32:
                        logger.debug('Found k32 plot!')
                        self.plots_k32_portable += 1
                    elif plot['size'] == 33:
                        logger.debug('Found k33 plot!')
                        self.plots_k33_portable += 1
                        
            logger.debug(f'og_count: {self.og_count}')
            logger.debug(f'og_size: {self.og_size}')
            logger.debug(f'portable_count: {self.portable_count}')
            logger.debug(f'portable_size: {self.portable_size}')
            
            logger.debug(f'plots_k32_og: {self.plots_k32_og}')
            logger.debug(f'plots_k33_og: {self.plots_k33_og}')
            logger.debug(f'plots_k32_portable: {self.plots_k32_portable}')
            logger.debug(f'plots_k33_portable: {self.plots_k33_portable}')
            #########################################################
            
            logger.info('Fetching blockchain state...')
            #########################################################
            blockchain = await self.fullnode.get_blockchain_state()
            
            self.sync_status = blockchain['sync'].get('synced')
            self.total_size = blockchain['space']
            
            average_block_time = await get_average_block_time(fullnode_port)
            self.og_time_to_win = int((average_block_time) / (self.og_size / self.total_size))
            
            logger.debug(f'sync_status: {self.sync_status}')
            logger.debug(f'total_size: {self.total_size}')
            logger.debug(f'og_time_to_win: {self.og_time_to_win}')
            #########################################################
            
            logger.info('Fetching wallet state...')
            #########################################################
            farmed_stat = await self.wallet.get_farmed_amount()
    
            self.chia_farmed = farmed_stat['farmed_amount']
            self.current_height = await self.wallet.get_height_info()
            main_wallet = await self.wallet.get_wallets()
            #assume only one wallet exists - might want to alter it in the future
            main_wallet_balance = await self.wallet.get_wallet_balance(main_wallet[0]["id"])
            self.wallet_funds = main_wallet_balance.get('confirmed_wallet_balance')
            
            logger.debug(f'chia_farmed: {self.chia_farmed}')
            logger.debug(f'current_height: {self.current_height}')
            logger.debug(f'wallet_funds: {self.wallet_funds}')
            #########################################################          
            
        except:
            #uncomment for debugging purposes only
            logger.error(traceback.format_exc())
            raise
            
        finally:
            self.harvester.close()
            self.fullnode.close()
            self.wallet.close()
            
        logger.info('--- Data collection complete ---')
        