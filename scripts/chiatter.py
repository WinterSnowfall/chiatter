#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 3.23
@date: 28/10/2023

Warning: Built for use with python 3.6+
'''

import signal
import threading
import asyncio
import os
from configparser import ConfigParser
from time import sleep
from chia import __version__ as chia_version
from prometheus_client import start_http_server, Gauge
from modules.chia_stats import chia_stats
from modules.openchia_stats import openchia_stats

# conf file block
CONF_FILE_PATH = os.path.join('..', 'conf', 'chiatter.conf')

PLOT_BASE_KSIZE = 32
# starts at k32 and goes up to k41 (should be enough 
# even for the k-raziest of plotters out there)
PLOT_KSIZE_RANGE = range(10)
# will cater for C0 to C9, although only compression 
# levels up to C7 are oficialy supported
PLOT_COMPRESSION_LEVEL_RANGE = range(10)

def sigterm_handler(signum, frame):
    print('Stopping stats collection due to SIGTERM...')
    
    raise SystemExit(0)

def sigint_handler(signum, frame):
    print('Stopping stats collection due to SIGINT...')
    
    raise SystemExit(0)

def chia_stats_worker(counter_lock, terminate_event, error_counters):
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while not terminate_event.is_set():
        try:
            # you'll have to excuse me here, but I simply h8 asyncio
            loop.run_until_complete(chia_stats_inst.collect_stats())
            
            chia_stats_harvesters.set(chia_stats_inst.harvesters)
            
            chia_stats_duplicate_plots.set(chia_stats_inst.plots_duplicates)
            chia_stats_failed_to_open_plots.set(chia_stats_inst.plots_failed_to_open)
            chia_stats_no_key_plots.set(chia_stats_inst.plots_no_key)
            
            # OG plots
            chia_stats_og_size.set(chia_stats_inst.og_size)
            chia_stats_og_time_to_win.set(chia_stats_inst.og_time_to_win)
            for ksize in PLOT_KSIZE_RANGE:
                chia_stats_og_plots[ksize].set(chia_stats_inst.plots_og[ksize])
            # OG plots won't have a compression level
            
            # portable plots
            chia_stats_portable_size.set(chia_stats_inst.portable_size)
            chia_stats_portable_time_to_win.set(chia_stats_inst.portable_time_to_win)
            for ksize in PLOT_KSIZE_RANGE:
                chia_stats_portable_plots[ksize].set(chia_stats_inst.plots_portable[ksize])
            for clevel in PLOT_COMPRESSION_LEVEL_RANGE:
                chia_stats_plots_compression_level[clevel].set(chia_stats_inst.plots_clevel[clevel])
            
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
            
        except:
            chia_stats_inst.clear_stats()
            
            if WATCHDOG_MODE:
                with counter_lock:
                    error_counters[0] += CHIA_STATS_COLLECTION_INTERVAL
        
        sleep(CHIA_STATS_COLLECTION_INTERVAL)
        
    loop.close()
    asyncio.set_event_loop(None)

def openchia_stats_worker(counter_lock, terminate_event, error_counters):
    
    while not terminate_event.is_set():
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
    # catch SIGTERM and exit gracefully
    signal.signal(signal.SIGTERM, sigterm_handler)
    # catch SIGINT and exit gracefully
    signal.signal(signal.SIGINT, sigint_handler)
    
    print(f'Starting chiatter - the chia stats collection agent...')
    
    print(f'Detected chia-blockchain version: {chia_version}')
    if chia_version.startswith('0.') or chia_version.startswith('1.'):
        print('Minimum required chia-blockchain version check: FAILED.')
        print('chiatter needs chia-blockchain version 2.0.0+ in order to run properly. Please upgrade your chia client.')
        raise SystemExit(1)
    else:
        print('Minimum required chia-blockchain version check: PASSED.')
    
    configParser = ConfigParser()
    
    try:
        configParser.read(CONF_FILE_PATH)
        general_section = configParser['GENERAL']
        
        PROMETHEUS_CLIENT_PORT = general_section.getint('prometheus_client_port')
        WATCHDOG_MODE = general_section.getboolean('watchdog_mode')
        WATCHDOG_INTERVAL = general_section.getint('watchdog_interval')
        WATCHDOG_THRESHOLD = general_section.getint('watchdog_threshold')
        MODULES = [module.strip() for module in general_section.get('modules').split(',')]
        # determine enabled modules
        CHIA_STATS_MODULE = 'chia_stats' in MODULES
        OPENCHIA_STATS_MODULE = 'openchia_stats' in MODULES
        # parse collection intervals conditionally for each module
        if CHIA_STATS_MODULE:
            CHIA_STATS_COLLECTION_INTERVAL = configParser['CHIA_STATS'].getint('collection_interval')
            CHIA_STATS_CONTRACT_ADDRESS_FILTER = configParser['CHIA_STATS'].get('contract_address_filter').strip()
            CHIA_STATS_LOGGING_LEVEL = configParser['CHIA_STATS'].get('logging_level')
        if OPENCHIA_STATS_MODULE:
            OPENCHIA_STATS_COLLECTION_INTERVAL = configParser['OPENCHIA_STATS'].getint('collection_interval')
            OPENCHIA_STATS_LAUNCHER_ID = configParser['OPENCHIA_STATS'].get('launcher_id')
            OPENCHIA_STATS_XCH_CURRENT_PRICE_CURRENCY = configParser['OPENCHIA_STATS'].get('xch_current_price_currency')
            OPENCHIA_STATS_LOGGING_LEVEL = configParser['OPENCHIA_STATS'].get('logging_level')
    
    except:
        print('Could not parse configuration file. Please make sure the appropriate structure is in place!')
        raise SystemExit(2)
    
    ### Prometheus client metrics ####################################################################################################################
    
    #--------------------------------------------------------- chia_stats ----------------------------------------------------------------------------
    chia_stats_harvesters = Gauge('chia_stats_harvesters', 'Number of connected harvesters, as seen by the farmer')
    
    chia_stats_duplicate_plots = Gauge('chia_stats_duplicate_plots', 'Number of duplicate plots across all harvesters')
    chia_stats_failed_to_open_plots = Gauge('chia_stats_failed_to_open_plots', 'Number of plots with access errors across all harvesters')
    chia_stats_no_key_plots = Gauge('chia_stats_no_key_plots', 'Number of plots without a valid key across all harvesters')
    
    # OG plots
    chia_stats_og_size = Gauge('chia_stats_og_size', 'Total size of og plots')
    chia_stats_og_time_to_win = Gauge('chia_stats_og_time_to_win', 'OG time to win')
    chia_stats_og_plots = [Gauge(f'chia_stats_og_plots_k{ksize + PLOT_BASE_KSIZE}', 
                                 f'Number of og k{ksize + PLOT_BASE_KSIZE} plots') for ksize in PLOT_KSIZE_RANGE]
        
    # portable plots
    chia_stats_portable_size = Gauge('chia_stats_portable_size', 'Total size of portable plots')
    chia_stats_portable_time_to_win = Gauge('chia_stats_portable_time_to_win', 'Portable time to win')
    chia_stats_portable_plots = [Gauge(f'chia_stats_portable_plots_k{ksize + PLOT_BASE_KSIZE}', 
                                          f'Number of portable k{ksize + PLOT_BASE_KSIZE} plots') for ksize in PLOT_KSIZE_RANGE]
    chia_stats_plots_compression_level = [Gauge(f'chia_stats_plots_compression_level_c{clevel}', 
                                                   f'Number of C{clevel} compressed plots') for clevel in PLOT_COMPRESSION_LEVEL_RANGE]
    
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
    
    #-------------------------------------------------------------------------------------------------------------------------------------------------
    
    #---------------------------------------------------------- openchia_stats -----------------------------------------------------------------------
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
    
    ##################################################################################################################################################
    
    # start a Prometheus http server thread to expose the metrics
    start_http_server(PROMETHEUS_CLIENT_PORT)
    
    if CHIA_STATS_MODULE:
        print('*** Loading the chia_stats module ***')
        chia_stats_inst = chia_stats(CHIA_STATS_LOGGING_LEVEL)
        if CHIA_STATS_CONTRACT_ADDRESS_FILTER != '':
            chia_stats_inst.set_contract_address_filter(CHIA_STATS_CONTRACT_ADDRESS_FILTER)
    
    if OPENCHIA_STATS_MODULE:
        print('*** Loading the openchia_stats module ***')
        openchia_stats_inst = openchia_stats(OPENCHIA_STATS_LOGGING_LEVEL)
        openchia_stats_inst.set_launcher_id(OPENCHIA_STATS_LAUNCHER_ID)
        # will default to 'usd'/$ if unspecified
        if OPENCHIA_STATS_XCH_CURRENT_PRICE_CURRENCY != '':
            openchia_stats_inst.set_xch_current_price_currency(OPENCHIA_STATS_XCH_CURRENT_PRICE_CURRENCY)
    
    counter_lock = threading.Lock()
    terminate_event = threading.Event()
    terminate_event.clear()
    # counts errors for the chia_stats_worker ([0]) & openchia_stats_worker threads ([1])
    error_counters = [0, 0]
    
    try:
        if CHIA_STATS_MODULE:
            chia_stats_thread = threading.Thread(target=chia_stats_worker, args=(counter_lock, 
                                                                                 terminate_event, error_counters), 
                                                 daemon=True)
            chia_stats_thread.start()
        
        if OPENCHIA_STATS_MODULE:
            openchia_stats_thread = threading.Thread(target=openchia_stats_worker, args=(counter_lock, 
                                                                                 terminate_event, error_counters), 
                                                     daemon=True)
            openchia_stats_thread.start()
        
        if WATCHDOG_MODE:
            while not terminate_event.is_set():
                if error_counters[0] > WATCHDOG_THRESHOLD or error_counters[1] > WATCHDOG_THRESHOLD:
                    print('The chiatter watchdog has reached its critical error threshold. Stopping data collection.')
                    raise SystemExit(3)
                else:
                    sleep(WATCHDOG_INTERVAL)
        else:
            # outside of watchdog mode simply wait forever, as the called threads 
            # should never terminate unless critical exceptions are encountered
            terminate_event.wait()
    
    except SystemExit:
        print('Stopping chiatter...')
        terminate_event.set()
        
    finally:
        # only wait to join threads in watchdog mode, otherwise terminate immediately
        if WATCHDOG_MODE:
            if CHIA_STATS_MODULE:
                chia_stats_thread.join()
            if OPENCHIA_STATS_MODULE:
                openchia_stats_thread.join()
    
    print(f'Thank you for using chiatter. Bye!')
