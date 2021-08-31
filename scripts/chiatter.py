#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 2.10
@date: 31/08/2021

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
#uncomment for debugging purposes only
import traceback

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
    print(f'\n\nThank you for using chiatter. I can only hope it wasn\'t too painfull. Bye!')
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
                chia_stats_self_portable_size.set(chia_stats_inst.self_portable_size)
                chia_stats_self_portable_plots_k32.set(chia_stats_inst.plots_self_portable_k32)
                chia_stats_self_portable_plots_k33.set(chia_stats_inst.plots_self_portable_k33)
                chia_stats_self_portable_time_to_win.set(chia_stats_inst.self_portable_time_to_win)
        except:
            chia_stats_error_counter += CHIA_STATS_COLLECTION_INTERVAL
            #uncomment for debugging purposes only
            print(traceback.format_exc())
            
        sleep(CHIA_STATS_COLLECTION_INTERVAL)
    
def truepool_stats_worker():
    global truepool_stats_error_counter
    
    while True:
        try:
            truepool_stats_inst.clear_stats()
            truepool_stats_inst.collect_stats()
            
            truepool_stats_total_size.set(truepool_stats_inst.pool_total_size)
            truepool_stats_total_farmers.set(truepool_stats_inst.pool_total_farmers)
            truepool_stats_minutes_to_win.set(truepool_stats_inst.pool_minutes_to_win)
            truepool_stats_blocks_won.set(truepool_stats_inst.pool_blocks_won)
            truepool_stats_seconds_since_last_win.set(truepool_stats_inst.pool_seconds_since_last_win)
            truepool_stats_farmer_points.set(truepool_stats_inst.farmer_points)
            truepool_stats_farmer_points_pplns.set(truepool_stats_inst.farmer_points_pplns)
            truepool_stats_farmer_difficulty.set(truepool_stats_inst.farmer_difficulty)
            truepool_stats_farmer_points_percentage.set(truepool_stats_inst.farmer_points_percentage)
            truepool_stats_farmer_share_pplns.set(truepool_stats_inst.farmer_share_pplns)
            truepool_stats_farmer_estimated_size.set(truepool_stats_inst.farmer_estimated_size)
            truepool_stats_farmer_ranking.set(truepool_stats_inst.farmer_ranking)
            truepool_stats_partial_errors_24h.set(truepool_stats_inst.partial_errors_24h)
            truepool_stats_farmer_pool_earnings.set(truepool_stats_inst.farmer_pool_earnings)
        except:
            truepool_stats_error_counter += TRUEPOOL_STATS_COLLECTION_INTERVAL
            #uncomment for debugging purposes only
            print(traceback.format_exc())
            
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
        chia_stats_self_portable_size = Gauge('chia_stats_self_portable_size', 'Total size of portable self-pooling plots')
        chia_stats_self_portable_plots_k32 = Gauge('chia_stats_self_portable_plots_k32', 'Number of portable self-pooling k32 plots')
        chia_stats_self_portable_plots_k33 = Gauge('chia_stats_self_portable_plots_k33', 'Number of portable self-pooling k33 plots')
        chia_stats_self_portable_time_to_win = Gauge('chia_stats_self_portable_time_to_win', 'Portable self-pooling time to win')
    #-------------------------------------------------------------------------------------------------------------------------------------------------
    #
    #---------------------- truepool_stats -----------------------------------------------------------------------------------------------------------
    truepool_stats_total_size = Gauge('truepool_stats_total_size', 'Estimated pool capacity')
    truepool_stats_total_farmers = Gauge('truepool_stats_total_farmers', 'Total number of pool members')
    truepool_stats_minutes_to_win = Gauge('truepool_stats_minutes_to_win', 'Estimated time to win')
    truepool_stats_blocks_won = Gauge('truepool_stats_blocks_won', 'Number of blocks won by the pool')
    truepool_stats_seconds_since_last_win = Gauge('truepool_stats_seconds_since_last_win', 'Number of seconds since last block win (pool)')
    truepool_stats_farmer_points = Gauge('truepool_stats_farmer_points', 'Total points a farmer has for the current reward cycle')
    truepool_stats_farmer_points_pplns = Gauge('truepool_stats_farmer_points_pplns', 'Total points a farmer has over a certain PPLNS interval')
    truepool_stats_farmer_difficulty = Gauge('truepool_stats_farmer_difficulty', 'Current pool difficulty for the farmer')
    truepool_stats_farmer_points_percentage = Gauge('truepool_stats_farmer_points_percentage', 'Percentage the farmer has of the overall rewards')
    truepool_stats_farmer_share_pplns = Gauge('truepool_stats_farmer_share_pplns', 'Percentage the farmer has of the pool PPLNS points over a certain interval')
    truepool_stats_farmer_estimated_size = Gauge('truepool_stats_farmer_estimated_size', 'Estimated size of a farmer\'s contribution to the pool')
    truepool_stats_farmer_ranking = Gauge('truepool_stats_farmer_ranking', 'Position the farmer is occupying on the leaderboard')
    truepool_stats_partial_errors_24h = Gauge('truepool_stats_partial_errors_24h', 'Number of erroneous partials in the last 24h')
    truepool_stats_farmer_pool_earnings = Gauge('truepool_stats_farmer_pool_earnings', 'Total amount of rewards received by the farmer from the pool')
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
        truepool_stats_inst.set_farmer_launcher_id(TRUEPOOL_STATS_LAUNCHER_ID)
    
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
                print('The chiatter watchdog has reached its error threshold. Stopping data collection.')
                raise SystemExit(2)
            else:
                sleep(WATCHDOG_INTERVAL)
            
    except KeyboardInterrupt:
        pass

    print(f'\n\nThank you for using chiatter. I can only hope it wasn\'t too painfull. Bye!')
