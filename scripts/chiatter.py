#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 2.95
@date: 12/11/2022

Warning: Built for use with python 3.6+
'''

from chia import __version__ as chia_version
from prometheus_client import start_http_server, Gauge
from modules.chia_stats import chia_stats
from modules.openchia_stats import openchia_stats
from configparser import ConfigParser
from time import sleep
import signal
import threading
import asyncio
import os

##global parameters init
configParser = ConfigParser()
counter_lock = threading.Lock()

##conf file block
conf_file_full_path = os.path.join('..', 'conf', 'chiatter.conf')

CHIA_STATS_SELF_POOLING_OG = 'og'
CHIA_STATS_SELF_POOLING_PORTABLE = 'portable'

def sigterm_handler(signum, frame):
    print(f'\n\nThank you for using chiatter. I can only hope it wasn\'t too painful. Bye!')
    raise SystemExit(0)

def http_server():
    start_http_server(PROMETHEUS_CLIENT_PORT)
    
def chia_stats_worker(error_counters, loop):
        
    while True:
        try:                    
            #you'll have to excuse me here, but I simply h8 asyncio
            coroutine = chia_stats_inst.collect_stats()
            loop.run_until_complete(coroutine)
            
            chia_stats_portable_size.set(chia_stats_inst.portable_size)
            chia_stats_portable_plots_k32.set(chia_stats_inst.plots_portable_k32)
            chia_stats_portable_plots_k33.set(chia_stats_inst.plots_portable_k33)
            chia_stats_portable_plots_k34.set(chia_stats_inst.plots_portable_k34)
            chia_stats_portable_time_to_win.set(chia_stats_inst.portable_time_to_win)
            
            chia_stats_sync_status.set(chia_stats_inst.sync_status)
            chia_stats_difficulty.set(chia_stats_inst.difficulty)
            chia_stats_current_height.set(chia_stats_inst.current_height)
            chia_stats_chia_farmed.set(chia_stats_inst.chia_farmed)
            chia_stats_wallet_funds.set(chia_stats_inst.wallet_funds)
            chia_stats_network_space_size.set(chia_stats_inst.network_space_size)
            chia_stats_mempool_size.set(chia_stats_inst.mempool_size)
            chia_stats_mempool_allocation.set(chia_stats_inst.mempool_allocation)
            chia_stats_full_node_connections.set(chia_stats_inst.full_node_connections)
            chia_stats_seconds_since_last_win.set(chia_stats_inst.seconds_since_last_win)
            
            if CHIA_STATS_SELF_POOLING_OG in self_pooling_types:
                chia_stats_og_size.set(chia_stats_inst.og_size)
                chia_stats_og_plots_k32.set(chia_stats_inst.plots_og_k32)
                chia_stats_og_plots_k33.set(chia_stats_inst.plots_og_k33)
                chia_stats_og_plots_k34.set(chia_stats_inst.plots_og_k34)
                chia_stats_og_time_to_win.set(chia_stats_inst.og_time_to_win)
                
            if CHIA_STATS_SELF_POOLING_PORTABLE in self_pooling_types:
                chia_stats_sp_portable_size.set(chia_stats_inst.sp_portable_size)
                chia_stats_sp_portable_plots_k32.set(chia_stats_inst.plots_sp_portable_k32)
                chia_stats_sp_portable_plots_k33.set(chia_stats_inst.plots_sp_portable_k33)
                chia_stats_sp_portable_plots_k34.set(chia_stats_inst.plots_sp_portable_k34)
                chia_stats_sp_portable_time_to_win.set(chia_stats_inst.sp_portable_time_to_win)
        
        except:
            chia_stats_inst.clear_stats()
            if WATCHDOG_MODE:
                with counter_lock:
                    error_counters[0] += CHIA_STATS_COLLECTION_INTERVAL
            
        sleep(CHIA_STATS_COLLECTION_INTERVAL)
    
def openchia_stats_worker(error_counters):
    
    while True:
        try:
            openchia_stats_inst.collect_stats()
            
            openchia_stats_space.set(openchia_stats_inst.pool_space)
            openchia_stats_farmers.set(openchia_stats_inst.pool_farmers)
            openchia_stats_estimate_win.set(openchia_stats_inst.pool_estimate_win)
            openchia_stats_rewards_blocks.set(openchia_stats_inst.pool_rewards_blocks)
            openchia_stats_time_since_last_win.set(openchia_stats_inst.pool_time_since_last_win)
            openchia_stats_xch_current_price.set(openchia_stats_inst.pool_xch_current_price)
            openchia_stats_launcher_points.set(openchia_stats_inst.launcher_points)
            openchia_stats_launcher_points_pplns.set(openchia_stats_inst.launcher_points_pplns)
            openchia_stats_launcher_difficulty.set(openchia_stats_inst.launcher_difficulty)
            openchia_stats_launcher_share_pplns.set(openchia_stats_inst.launcher_share_pplns)
            openchia_stats_launcher_estimated_size.set(openchia_stats_inst.launcher_estimated_size)
            openchia_stats_launcher_ranking.set(openchia_stats_inst.launcher_ranking)
            openchia_stats_launcher_pool_earnings.set(openchia_stats_inst.launcher_pool_earnings)
            openchia_stats_launcher_partial_errors_24h.set(openchia_stats_inst.launcher_partial_errors_24h)
            openchia_stats_seconds_since_last_win.set(openchia_stats_inst.seconds_since_last_win)

        except:
            openchia_stats_inst.clear_stats()
            if WATCHDOG_MODE:
                with counter_lock:
                    error_counters[1] += OPENCHIA_STATS_COLLECTION_INTERVAL
            
        sleep(OPENCHIA_STATS_COLLECTION_INTERVAL)

if __name__ == '__main__':
    #catch SIGTERM and exit gracefully
    signal.signal(signal.SIGTERM, sigterm_handler)
    
    print('----------------------------------------------------------------------------------------------------')
    print('| Welcome to chiatter - the most basic/dense chia collection agent. Speak very slowly and clearly! |')
    print(f'----------------------------------------------------------------------------------------------------\n')
    
    if chia_version.startswith('1.0.') or chia_version.startswith('1.1.') or chia_version.startswith('1.2.'):
        print('chiatter needs chia-blockchain version 1.3.0+ in order to run. Please upgrade your chia client.')
        raise SystemExit(1)
    
    try:
        #reading from config file
        configParser.read(conf_file_full_path)
        general_section = configParser['GENERAL']
        #parsing generic parameters
        PROMETHEUS_CLIENT_PORT = general_section.getint('prometheus_client_port')
        WATCHDOG_MODE = general_section.getboolean('watchdog_mode')
        WATCHDOG_INTERVAL = general_section.getint('watchdog_interval')
        WATCHDOG_THRESHOLD = general_section.getint('watchdog_threshold')
        modules = [module.strip() for module in general_section.get('modules').split(',')]
        #determine enabled modules
        CHIA_STATS_MODULE = 'chia_stats' in modules
        OPENCHIA_STATS_MODULE = 'openchia_stats' in modules
        #parse collection intervals conditionally for each module
        if CHIA_STATS_MODULE:
            CHIA_STATS_COLLECTION_INTERVAL = configParser['CHIA_STATS'].getint('collection_interval')
            CHIA_STATS_LOGGING_LEVEL = configParser['CHIA_STATS'].get('logging_level')
            self_pooling_types = configParser['CHIA_STATS'].get('self_pooling_types')
            self_pooling_types = [pooling_type.strip() for pooling_type 
                                  in self_pooling_types.split(',')] if self_pooling_types != '' else []
            CHIA_STATS_SELF_POOLING_CONTACT_ADDRESS = configParser['CHIA_STATS'].get('self_pooling_contact_address').strip()
        if OPENCHIA_STATS_MODULE:
            OPENCHIA_STATS_COLLECTION_INTERVAL = configParser['OPENCHIA_STATS'].getint('collection_interval')
            OPENCHIA_STATS_LAUNCHER_ID = configParser['OPENCHIA_STATS'].get('launcher_id')
            OPENCHIA_STATS_XCH_CURRENT_PRICE_CURRENCY = configParser['OPENCHIA_STATS'].get('xch_current_price_currency')
            OPENCHIA_STATS_LOGGING_LEVEL = configParser['OPENCHIA_STATS'].get('logging_level')
            
    except:
        print('Could not parse configuration file. Please make sure the appropriate structure is in place!')
        raise SystemExit(2)
    
    ### Prometheus client metrics ####################################################################################################################
    #
    #---------------------- chia_stats ---------------------------------------------------------------------------------------------------------------
    chia_stats_portable_size = Gauge('chia_stats_portable_size', 'Total size of portable plots')
    chia_stats_portable_plots_k32 = Gauge('chia_stats_portable_plots_k32', 'Number of portable k32 plots')
    chia_stats_portable_plots_k33 = Gauge('chia_stats_portable_plots_k33', 'Number of portable k33 plots')
    chia_stats_portable_plots_k34 = Gauge('chia_stats_portable_plots_k34', 'Number of portable k34 plots')
    chia_stats_portable_time_to_win = Gauge('chia_stats_portable_time_to_win', 'Portable time to win')
    #
    chia_stats_sync_status = Gauge('chia_stats_sync_status', 'Blockchain synced status')
    chia_stats_difficulty = Gauge('chia_stats_difficulty', 'Current difficulty on mainnet')
    chia_stats_current_height = Gauge('chia_stats_current_height', 'Current blockchain height')
    chia_stats_chia_farmed = Gauge('chia_stats_chia_farmed', 'XCH farmed')
    chia_stats_wallet_funds = Gauge('chia_stats_wallet_funds', 'Funds present in the main chia wallet')
    chia_stats_network_space_size = Gauge('chia_stats_network_space_size', 'Total network space')
    chia_stats_mempool_size = Gauge('chia_stats_mempool_size', 'Total size of the mempool')
    chia_stats_mempool_allocation = Gauge('chia_stats_mempool_allocation', 'Percentage of total mempool which is in use')
    chia_stats_full_node_connections = Gauge('chia_stats_full_node_connections', 'Number of full node connections')
    chia_stats_seconds_since_last_win = Gauge('chia_stats_seconds_since_last_win', 'Number of seconds since last block win (farmer)')
    #
    if CHIA_STATS_SELF_POOLING_OG in self_pooling_types:
        chia_stats_og_size = Gauge('chia_stats_og_size', 'Total size of og plots')
        chia_stats_og_plots_k32 = Gauge('chia_stats_og_plots_k32', 'Number of og k32 plots')
        chia_stats_og_plots_k33 = Gauge('chia_stats_og_plots_k33', 'Number of og k33 plots')
        chia_stats_og_plots_k34 = Gauge('chia_stats_og_plots_k34', 'Number of og k34 plots')
        chia_stats_og_time_to_win = Gauge('chia_stats_og_time_to_win', 'OG time to win')
    #   
    if CHIA_STATS_SELF_POOLING_PORTABLE in self_pooling_types:
        chia_stats_sp_portable_size = Gauge('chia_stats_sp_portable_size', 'Total size of portable self-pooling plots')
        chia_stats_sp_portable_plots_k32 = Gauge('chia_stats_sp_portable_plots_k32', 'Number of portable self-pooling k32 plots')
        chia_stats_sp_portable_plots_k33 = Gauge('chia_stats_sp_portable_plots_k33', 'Number of portable self-pooling k33 plots')
        chia_stats_sp_portable_plots_k34 = Gauge('chia_stats_sp_portable_plots_k34', 'Number of portable self-pooling k34 plots')
        chia_stats_sp_portable_time_to_win = Gauge('chia_stats_sp_portable_time_to_win', 'Portable self-pooling time to win')
    #-------------------------------------------------------------------------------------------------------------------------------------------------
    #
    #---------------------- openchia_stats -----------------------------------------------------------------------------------------------------------
    openchia_stats_space = Gauge('openchia_stats_space', 'Estimated pool capacity')
    openchia_stats_farmers = Gauge('openchia_stats_farmers', 'Total number of pool members')
    openchia_stats_estimate_win = Gauge('openchia_stats_estimate_win', 'Estimated time to win')
    openchia_stats_rewards_blocks = Gauge('openchia_stats_rewards_blocks', 'Number of blocks won/rewarded by the pool')
    openchia_stats_time_since_last_win = Gauge('openchia_stats_time_since_last_win', 'Time since last block win/reward')
    openchia_stats_xch_current_price = Gauge('openchia_stats_xch_current_price', 'XCH exchange price in the currencty of choice')
    openchia_stats_launcher_points = Gauge('openchia_stats_launcher_points', 'Total points a launcher has for the current reward cycle')
    openchia_stats_launcher_points_pplns = Gauge('openchia_stats_launcher_points_pplns', 'Total points a launcher has over the PPLNS interval')
    openchia_stats_launcher_difficulty = Gauge('openchia_stats_launcher_difficulty', 'Current pool difficulty for the launcher')
    openchia_stats_launcher_share_pplns = Gauge('openchia_stats_launcher_share_pplns', 'Fraction the launcher has of the pool points over the PPLNS interval')
    openchia_stats_launcher_estimated_size = Gauge('openchia_stats_launcher_estimated_size', 'Estimated size of a launcher\'s contribution to the pool')
    openchia_stats_launcher_ranking = Gauge('openchia_stats_launcher_ranking', 'Launcher rank, as seen on the OpenChia leaderboard')
    openchia_stats_launcher_pool_earnings = Gauge('openchia_stats_launcher_pool_earnings', 'Total amount of rewards received by the launcher from the pool')
    openchia_stats_launcher_partial_errors_24h = Gauge('openchia_stats_launcher_partial_errors_24h', 'Number of erroneous partials in the last 24h')
    openchia_stats_seconds_since_last_win = Gauge('openchia_stats_seconds_since_last_win', 'Number of seconds since last block win (launcher)')
    #-------------------------------------------------------------------------------------------------------------------------------------------------
    #
    ##################################################################################################################################################
    
    #start the Prometheus http server to expose the metrics
    http_server_thread = threading.Thread(target=http_server, args=(), daemon=True)
    http_server_thread.start()
    
    if CHIA_STATS_MODULE:
        print('*** Loading the chia_stats module ***')
        chia_stats_inst = chia_stats(CHIA_STATS_LOGGING_LEVEL)
        if (CHIA_STATS_SELF_POOLING_PORTABLE in self_pooling_types and 
            CHIA_STATS_SELF_POOLING_CONTACT_ADDRESS != ''):
            chia_stats_inst.set_self_pooling_contract_address(CHIA_STATS_SELF_POOLING_CONTACT_ADDRESS)
    if OPENCHIA_STATS_MODULE:
        print('*** Loading the openchia_stats module ***')
        openchia_stats_inst = openchia_stats(OPENCHIA_STATS_LOGGING_LEVEL)
        openchia_stats_inst.set_launcher_id(OPENCHIA_STATS_LAUNCHER_ID)
        #will default to 'usd'/$ if unspecified
        if OPENCHIA_STATS_XCH_CURRENT_PRICE_CURRENCY != '':
            openchia_stats_inst.set_xch_current_price_currency(OPENCHIA_STATS_XCH_CURRENT_PRICE_CURRENCY)
    
    #a mere aestetic separator
    print('')
    
    #counts errors for the chia_stats_worker ([0]) & openchia_stats_worker threads ([1])
    error_counters = [0, 0]
    
    try:
        if CHIA_STATS_MODULE:
            loop = asyncio.get_event_loop()
            chia_stats_thread = threading.Thread(target=chia_stats_worker, args=(error_counters, loop), daemon=True)
            chia_stats_thread.start()
                
        if OPENCHIA_STATS_MODULE:
            openchia_stats_thread = threading.Thread(target=openchia_stats_worker, args=(error_counters, ), daemon=True)
            openchia_stats_thread.start()
                
        if WATCHDOG_MODE:
            while True:
                if error_counters[0] > WATCHDOG_THRESHOLD or error_counters[1] > WATCHDOG_THRESHOLD:
                    print('The chiatter watchdog has reached its critical error threshold. Stopping data collection.')
                    raise SystemExit(3)
                else:
                    sleep(WATCHDOG_INTERVAL)
        else:
            #outside of watchdog mode simply wait forever, as the called threads 
            #should never terminate unless critical exceptions are encountered
            if CHIA_STATS_MODULE:
                chia_stats_thread.join()
            if OPENCHIA_STATS_MODULE:
                openchia_stats_thread.join()
            
    except KeyboardInterrupt:
        pass

    print(f'\n\nThank you for using chiatter. I can only hope it wasn\'t too painful. Bye!')
