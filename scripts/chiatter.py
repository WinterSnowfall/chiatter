#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 1.40
@date: 01/08/2021

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

watchdog_counter = 0
chia_stats_error_counter = 0
truepool_stats_error_counter = 0

# Prometheus client metrics

#---------------------- chia_stats ----------------------------------------------
chia_stats_og_size = Gauge('chia_stats_og_size', 'Total size of og plots')
chia_stats_portable_size = Gauge('chia_stats_portable_size', 'Total size of portable plots')
chia_stats_plots_k32_og = Gauge('chia_stats_plots_k32_og', 'Number of og k32 plots')
chia_stats_plots_k33_og = Gauge('chia_stats_plots_k33_og', 'Number of og k33 plots')
chia_stats_plots_k32_portable = Gauge('chia_stats_plots_k32_portable', 'Number of portable k32 plots')
chia_stats_plots_k33_portable = Gauge('chia_stats_plots_k33_portable', 'Number of portable k33 plots')
chia_stats_network_space_size = Gauge('chia_stats_network_space_size', 'Total network space')
chia_stats_chia_farmed = Gauge('chia_stats_chia_farmed', 'XCH farmed')
chia_stats_og_time_to_win = Gauge('chia_stats_og_time_to_win', 'OG time to win')
chia_stats_sync_status = Gauge('chia_stats_sync_status', 'Blockchain synced status')
chia_stats_current_height = Gauge('chia_stats_current_height', 'Current blockchain height')
chia_stats_wallet_funds = Gauge('chia_stats_wallet_funds', 'Funds present in the main chia wallet')
#--------------------------------------------------------------------------------

#---------------------- truepool_stats ------------------------------------------
truepool_stats_total_size = Gauge('truepool_stats_total_size', 'Estimated pool capacity')
truepool_stats_total_farmers = Gauge('truepool_stats_total_farmers', 'Total number of pool members')
truepool_stats_minutes_to_win = Gauge('truepool_stats_minutes_to_win', 'Estimated time to win')
truepool_stats_blocks_won = Gauge('truepool_stats_blocks_won', 'Number of blocks won by the pool')
truepool_stats_seconds_since_last_win = Gauge('truepool_stats_seconds_since_last_win', 'Number of seconds since last block win')
truepool_stats_farmer_points = Gauge('truepool_stats_farmer_points', 'Total points a farmer has for the current reward cycle')
truepool_stats_farmer_difficulty = Gauge('truepool_stats_farmer_difficulty', 'Current pool difficulty for the farmer')
truepool_stats_farmer_points_percentage = Gauge('truepool_stats_farmer_points_percentage', 'Percentage the farmer has from the overall rewards')
truepool_stats_farmer_estimated_size = Gauge('truepool_stats_farmer_estimated_size', 'Estimated size of a farmer\'s contribution to the pool')
truepool_stats_farmer_ranking = Gauge('truepool_stats_farmer_ranking', 'Position the farmer is occupying on the leaderboard')
truepool_stats_partial_errors_24h = Gauge('truepool_stats_partial_errors_24h', 'Number of erroneous partials in the last 24h')
truepool_stats_farmer_pool_earnings = Gauge('truepool_stats_farmer_pool_earnings', 'Total amount of rewards received by the farmer from the pool')
#--------------------------------------------------------------------------------

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
            
            chia_stats_og_size.set(chia_stats_inst.og_size)
            chia_stats_portable_size.set(chia_stats_inst.portable_size)
            chia_stats_plots_k32_og.set(chia_stats_inst.plots_k32_og)
            chia_stats_plots_k33_og.set(chia_stats_inst.plots_k33_og)
            chia_stats_plots_k32_portable.set(chia_stats_inst.plots_k32_portable)
            chia_stats_plots_k33_portable.set(chia_stats_inst.plots_k33_portable)
            chia_stats_network_space_size.set(chia_stats_inst.network_space_size)
            chia_stats_chia_farmed.set(chia_stats_inst.chia_farmed)
            chia_stats_og_time_to_win.set(chia_stats_inst.og_time_to_win)
            chia_stats_sync_status.set(chia_stats_inst.sync_status)
            chia_stats_current_height.set(chia_stats_inst.current_height)
            chia_stats_wallet_funds.set(chia_stats_inst.wallet_funds)
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
            truepool_stats_farmer_difficulty.set(truepool_stats_inst.farmer_difficulty)
            truepool_stats_farmer_points_percentage.set(truepool_stats_inst.farmer_points_percentage)
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
        if 'truepool_stats' in modules:
            TRUEPOOL_STATS_COLLECTION_INTERVAL = configParser['TRUEPOOL_STATS'].getint('collection_interval')
            TRUEPOOL_LAUNCHER_ID = configParser['TRUEPOOL_STATS'].get('launcher_id')
            
    except:
        print('Could not parse configuration file. Please make sure the appropriate structure is in place!')
        raise SystemExit(1)
    
    #start the Prometheus http server to expose the metrics
    http_server_thread = threading.Thread(target=http_server, args=(), daemon=True)
    http_server_thread.start()
    
    if 'chia_stats' in modules:
        print('*** Loading the chia_stats module ***')
        chia_stats_inst = chia_stats();
    if 'truepool_stats' in modules:
        print('*** Loading the truepool_stats module ***')
        truepool_stats_inst = truepool_stats();
        truepool_stats_inst.set_farmer_launcher_id(TRUEPOOL_LAUNCHER_ID)
    
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
