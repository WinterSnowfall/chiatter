#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 2.40
@date: 16/10/2021

Warning: Built for use with python 3.6+
'''

from prometheus_client import start_http_server, Gauge
from modules.chia_stats import chia_stats
from modules.truepool_stats import truepool_stats
from configparser import ConfigParser
from time import sleep
import signal
import threading
import asyncio
import os

##global parameters init
configParser = ConfigParser()

##conf file block
conf_file_full_path = os.path.join('..', 'conf', 'chiatter.conf')

CHIA_STATS_SELF_POOLING_OG = 'og'
CHIA_STATS_SELF_POOLING_PORTABLE = 'portable'

watchdog_counter = 0
chia_stats_error_counter = 0
truepool_stats_error_counter = 0

def sigterm_handler(signum, frame):
    print(f'\n\nThank you for using chiatter. I can only hope it wasn\'t too painful. Bye!')
    raise SystemExit(0)

def http_server():
    start_http_server(PROMETHEUS_CLIENT_PORT)
    
def chia_stats_worker(loop):
    global chia_stats_error_counter
    
    while True:
        try:
            chia_stats_inst.clear_stats()
                    
            #you'll have to excuse me here, but I simply h8 asyncio
            coroutine = chia_stats_inst.collect_stats()
            loop.run_until_complete(coroutine)
            
            chia_stats_portable_size.set(chia_stats_inst.portable_size)
            chia_stats_portable_plots_k32.set(chia_stats_inst.plots_portable_k32)
            chia_stats_portable_plots_k33.set(chia_stats_inst.plots_portable_k33)
            chia_stats_portable_time_to_win.set(chia_stats_inst.portable_time_to_win)
            
            chia_stats_sync_status.set(chia_stats_inst.sync_status)
            chia_stats_difficulty.set(chia_stats_inst.difficulty)
            chia_stats_current_height.set(chia_stats_inst.current_height)
            chia_stats_chia_farmed.set(chia_stats_inst.chia_farmed)
            chia_stats_wallet_funds.set(chia_stats_inst.wallet_funds)
            chia_stats_network_space_size.set(chia_stats_inst.network_space_size)
            chia_stats_full_node_connections.set(chia_stats_inst.full_node_connections)
            chia_stats_seconds_since_last_win.set(chia_stats_inst.seconds_since_last_win)
            
            if CHIA_STATS_SELF_POOLING_OG in self_pooling_types:
                chia_stats_og_size.set(chia_stats_inst.og_size)
                chia_stats_og_plots_k32.set(chia_stats_inst.plots_og_k32)
                chia_stats_og_plots_k33.set(chia_stats_inst.plots_og_k33)
                chia_stats_og_time_to_win.set(chia_stats_inst.og_time_to_win)
                
            if CHIA_STATS_SELF_POOLING_PORTABLE in self_pooling_types:
                chia_stats_sp_portable_size.set(chia_stats_inst.sp_portable_size)
                chia_stats_sp_portable_plots_k32.set(chia_stats_inst.plots_sp_portable_k32)
                chia_stats_sp_portable_plots_k33.set(chia_stats_inst.plots_sp_portable_k33)
                chia_stats_sp_portable_time_to_win.set(chia_stats_inst.sp_portable_time_to_win)
        except:
            chia_stats_error_counter += CHIA_STATS_COLLECTION_INTERVAL
            
        sleep(CHIA_STATS_COLLECTION_INTERVAL)
    
def truepool_stats_worker():
    global truepool_stats_error_counter
    
    while True:
        try:
            truepool_stats_inst.clear_stats()
            truepool_stats_inst.collect_stats()
            
            truepool_stats_space.set(truepool_stats_inst.pool_space)
            truepool_stats_farmers.set(truepool_stats_inst.pool_farmers)
            truepool_stats_estimate_win.set(truepool_stats_inst.pool_estimate_win)
            truepool_stats_rewards_blocks.set(truepool_stats_inst.pool_rewards_blocks)
            truepool_stats_time_since_last_win.set(truepool_stats_inst.pool_time_since_last_win)
            truepool_stats_launcher_points.set(truepool_stats_inst.launcher_points)
            truepool_stats_launcher_points_pplns.set(truepool_stats_inst.launcher_points_pplns)
            truepool_stats_launcher_difficulty.set(truepool_stats_inst.launcher_difficulty)
            truepool_stats_launcher_points_of_total.set(truepool_stats_inst.launcher_points_of_total)
            truepool_stats_launcher_share_pplns.set(truepool_stats_inst.launcher_share_pplns)
            truepool_stats_launcher_estimated_size.set(truepool_stats_inst.launcher_estimated_size)
            truepool_stats_launcher_ranking.set(truepool_stats_inst.launcher_ranking)
            truepool_stats_launcher_pool_earnings.set(truepool_stats_inst.launcher_pool_earnings)
            truepool_stats_partial_errors_24h.set(truepool_stats_inst.partial_errors_24h)
        except:
            truepool_stats_error_counter += TRUEPOOL_STATS_COLLECTION_INTERVAL
            
        sleep(TRUEPOOL_STATS_COLLECTION_INTERVAL)

if __name__ == '__main__':
    #catch SIGTERM and exit gracefully
    signal.signal(signal.SIGTERM, sigterm_handler)
    
    print('----------------------------------------------------------------------------------------------------')
    print('| Welcome to chiatter - the most basic/dense chia collection agent. Speak very slowly and clearly! |')
    print(f'----------------------------------------------------------------------------------------------------\n')
    
    try:
        #reading from config file
        configParser.read(conf_file_full_path)
        general_section = configParser['GENERAL']
        #parsing generic parameters
        PROMETHEUS_CLIENT_PORT = general_section.getint('prometheus_client_port')
        WATCHDOG_INTERVAL = general_section.getint('watchdog_interval')
        WATCHDOG_THRESHOLD = general_section.getint('watchdog_threshold')
        modules = general_section.get('modules')
        modules = [module.strip() for module in modules.split(',')]
        #parse collection intervals conditionally for each module
        if 'chia_stats' in modules:
            CHIA_STATS_COLLECTION_INTERVAL = configParser['CHIA_STATS'].getint('collection_interval')
            CHIA_STATS_LOGGING_LEVEL = configParser['CHIA_STATS'].get('logging_level')
            self_pooling_types = configParser['CHIA_STATS'].get('self_pooling_types')
            self_pooling_types = [pooling_type.strip() for pooling_type in self_pooling_types.split(',')]
            CHIA_STATS_SELF_POOLING_CONTACT_ADDRESS = configParser['CHIA_STATS'].get('self_pooling_contact_address')
        if 'truepool_stats' in modules:
            TRUEPOOL_STATS_COLLECTION_INTERVAL = configParser['TRUEPOOL_STATS'].getint('collection_interval')
            TRUEPOOL_STATS_LAUNCHER_ID = configParser['TRUEPOOL_STATS'].get('launcher_id')
            TRUEPOOL_STATS_LOGGING_LEVEL = configParser['TRUEPOOL_STATS'].get('logging_level')
            
    except:
        print('Could not parse configuration file. Please make sure the appropriate structure is in place!')
        raise SystemExit(1)
    
    ### Prometheus client metrics ####################################################################################################################
    #
    #---------------------- chia_stats ---------------------------------------------------------------------------------------------------------------
    chia_stats_portable_size = Gauge('chia_stats_portable_size', 'Total size of portable plots')
    chia_stats_portable_plots_k32 = Gauge('chia_stats_portable_plots_k32', 'Number of portable k32 plots')
    chia_stats_portable_plots_k33 = Gauge('chia_stats_portable_plots_k33', 'Number of portable k33 plots')
    chia_stats_portable_time_to_win = Gauge('chia_stats_portable_time_to_win', 'Portable time to win')
    #
    chia_stats_sync_status = Gauge('chia_stats_sync_status', 'Blockchain synced status')
    chia_stats_difficulty = Gauge('chia_stats_difficulty', 'Current difficulty on mainnet')
    chia_stats_current_height = Gauge('chia_stats_current_height', 'Current blockchain height')
    chia_stats_chia_farmed = Gauge('chia_stats_chia_farmed', 'XCH farmed')
    chia_stats_wallet_funds = Gauge('chia_stats_wallet_funds', 'Funds present in the main chia wallet')
    chia_stats_network_space_size = Gauge('chia_stats_network_space_size', 'Total network space')
    chia_stats_full_node_connections = Gauge('chia_stats_full_node_connections', 'Number of full node connections')
    chia_stats_seconds_since_last_win = Gauge('chia_stats_seconds_since_last_win', 'Number of seconds since last block win (farmer)')
    #
    if CHIA_STATS_SELF_POOLING_OG in self_pooling_types:
        chia_stats_og_size = Gauge('chia_stats_og_size', 'Total size of og plots')
        chia_stats_og_plots_k32 = Gauge('chia_stats_og_plots_k32', 'Number of og k32 plots')
        chia_stats_og_plots_k33 = Gauge('chia_stats_og_plots_k33', 'Number of og k33 plots')
        chia_stats_og_time_to_win = Gauge('chia_stats_og_time_to_win', 'OG time to win')
    #   
    if CHIA_STATS_SELF_POOLING_PORTABLE in self_pooling_types:
        chia_stats_sp_portable_size = Gauge('chia_stats_sp_portable_size', 'Total size of portable self-pooling plots')
        chia_stats_sp_portable_plots_k32 = Gauge('chia_stats_sp_portable_plots_k32', 'Number of portable self-pooling k32 plots')
        chia_stats_sp_portable_plots_k33 = Gauge('chia_stats_sp_portable_plots_k33', 'Number of portable self-pooling k33 plots')
        chia_stats_sp_portable_time_to_win = Gauge('chia_stats_sp_portable_time_to_win', 'Portable self-pooling time to win')
    #-------------------------------------------------------------------------------------------------------------------------------------------------
    #
    #---------------------- truepool_stats -----------------------------------------------------------------------------------------------------------
    truepool_stats_space = Gauge('truepool_stats_space', 'Estimated pool capacity')
    truepool_stats_farmers = Gauge('truepool_stats_farmers', 'Total number of pool members')
    truepool_stats_estimate_win = Gauge('truepool_stats_estimate_win', 'Estimated time to win')
    truepool_stats_rewards_blocks = Gauge('truepool_stats_rewards_blocks', 'Number of blocks won/rewarded by the pool')
    truepool_stats_time_since_last_win = Gauge('truepool_stats_time_since_last_win', 'Time since last block win/reward')
    truepool_stats_launcher_points = Gauge('truepool_stats_launcher_points', 'Total points a launcher has for the current reward cycle')
    truepool_stats_launcher_points_pplns = Gauge('truepool_stats_launcher_points_pplns', 'Total points a launcher has over the PPLNS interval')
    truepool_stats_launcher_difficulty = Gauge('truepool_stats_launcher_difficulty', 'Current pool difficulty for the launcher')
    truepool_stats_launcher_points_of_total = Gauge('truepool_stats_launcher_points_of_total', 'Percentage the launcher has of the overall rewards')
    truepool_stats_launcher_share_pplns = Gauge('truepool_stats_launcher_share_pplns', 'Fraction the launcher has of the pool points over the PPLNS interval')
    truepool_stats_launcher_estimated_size = Gauge('truepool_stats_launcher_estimated_size', 'Estimated size of a launcher\'s contribution to the pool')
    truepool_stats_launcher_ranking = Gauge('truepool_stats_launcher_ranking', 'Launcher rank, as seen on the TruePool leaderboard')
    truepool_stats_launcher_pool_earnings = Gauge('truepool_stats_launcher_pool_earnings', 'Total amount of rewards received by the launcher from the pool')
    truepool_stats_partial_errors_24h = Gauge('truepool_stats_partial_errors_24h', 'Number of erroneous partials in the last 24h')
    #-------------------------------------------------------------------------------------------------------------------------------------------------
    #
    ##################################################################################################################################################
    
    #start the Prometheus http server to expose the metrics
    http_server_thread = threading.Thread(target=http_server, args=(), daemon=True)
    http_server_thread.start()
    
    if 'chia_stats' in modules:
        print('*** Loading the chia_stats module ***')
        chia_stats_inst = chia_stats(CHIA_STATS_LOGGING_LEVEL)
        if CHIA_STATS_SELF_POOLING_PORTABLE in self_pooling_types:
            chia_stats_inst.set_self_pooling_contract_address(CHIA_STATS_SELF_POOLING_CONTACT_ADDRESS)
    if 'truepool_stats' in modules:
        print('*** Loading the truepool_stats module ***')
        truepool_stats_inst = truepool_stats(TRUEPOOL_STATS_LOGGING_LEVEL)
        truepool_stats_inst.set_launcher_id(TRUEPOOL_STATS_LAUNCHER_ID)
    
    #a mere aestetic separator
    print('')
    
    try:
        if 'chia_stats' in modules:
            loop = asyncio.get_event_loop()
            chia_stats_thread = threading.Thread(target=chia_stats_worker, args=((loop,)), daemon=True)
            chia_stats_thread.start()
                
        if 'truepool_stats' in modules:
            truepool_stats_thread = threading.Thread(target=truepool_stats_worker, args=(), daemon=True)
            truepool_stats_thread.start()
                
        while True:
            if chia_stats_error_counter > WATCHDOG_THRESHOLD or truepool_stats_error_counter > WATCHDOG_THRESHOLD:
                print('The chiatter watchdog has reached its critical error threshold. Stopping data collection.')
                raise SystemExit(2)
            else:
                sleep(WATCHDOG_INTERVAL)
            
    except KeyboardInterrupt:
        pass

    print(f'\n\nThank you for using chiatter. I can only hope it wasn\'t too painful. Bye!')
