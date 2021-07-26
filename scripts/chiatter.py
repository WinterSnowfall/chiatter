#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 1.00
@date: 26/07/2021

Warning: Built for use with python 3.6+
'''

from prometheus_client import start_http_server, Gauge
from modules.chia_stats import chia_stats
#from scripts.modules.truepool_stats import truepool_stats
from configparser import ConfigParser
from time import sleep
import threading
import asyncio
import os

##global parameters init
configParser = ConfigParser()

##conf file block
conf_file_full_path = os.path.join('..', 'conf', 'chiatter.conf')

# Prometheus client metrics

#---------------------- chia_stats ----------------------------------------------
chia_stats_og_count = Gauge('chia_stats_og_count', 'Total number of og plots')
chia_stats_og_size = Gauge('chia_stats_og_size', 'Total size of og plots')
chia_stats_portable_count = Gauge('chia_stats_portable_count', 'Total number of portable plots')
chia_stats_portable_size = Gauge('chia_stats_portable_size', 'Total size of portable plots')
chia_stats_plots_k32_og = Gauge('chia_stats_plots_k32_og', 'Number of og k32 plots')
chia_stats_plots_k33_og = Gauge('chia_stats_plots_k33_og', 'Number of og k33 plots')
chia_stats_plots_k32_portable = Gauge('chia_stats_plots_k32_portable', 'Number of portable k32 plots')
chia_stats_plots_k33_portable = Gauge('chia_stats_plots_k33_portable', 'Number of portable k33 plots')
chia_stats_total_size = Gauge('chia_stats_total_size', 'Total network space')
chia_stats_chia_farmed = Gauge('chia_stats_chia_farmed', 'XCH farmed')
chia_stats_ttw = Gauge('chia_stats_ttw', 'OG time to win')
chia_stats_sync_status = Gauge('chia_stats_sync_status', 'Blockchain synced status')
#--------------------------------------------------------------------------------

#---------------------- truepool ------------------------------------------------
#TBD
#--------------------------------------------------------------------------------

def http_server():
    start_http_server(8080)

if __name__ == '__main__':
    print('----------------------------------------------------------------------------------------------------')
    print('| Welcome to chiatter - the most basic/dense chia collection agent. Speak very slowly and clearly! |')
    print(f'----------------------------------------------------------------------------------------------------\n')
    
    try:
        #reading from config file
        configParser.read(conf_file_full_path)
        general_section = configParser['GENERAL']
        #parsing generic parameters
        COLLECTION_INTERVAL_SECONDS = general_section.getint('collection_interval_seconds')
                
        modules = general_section.get('modules')
        modules = [module.strip() for module in modules.split(',')]
    except:
        print('Could not parse configuration file. Please make sure the appropriate structure is in place!')
        raise SystemExit(1)
    
    # Start up the server to expose the metrics.
    server_thread = threading.Thread(target=http_server, args=(), daemon=True)
    server_thread.start()
    
    if 'chia_stats' in modules:
        print('*** Loading the chia_stats module ***')
        chia_stats_inst = chia_stats();
    
    #a mere aestetic separator
    print('')
    
try:
    # Generate some requests
    while True:
        if 'chia_stats' in modules:
            chia_stats_inst.clear_stats()
                    
            #you'll have to excuse me here, but I simply h8 asyncio
            loop = asyncio.get_event_loop()
            coroutine = chia_stats_inst.collect_stats()
            loop.run_until_complete(coroutine)
            
            chia_stats_og_count.set(chia_stats_inst.og_count)
            chia_stats_og_size.set(chia_stats_inst.og_size)
            chia_stats_portable_count.set(chia_stats_inst.portable_count)
            chia_stats_portable_size.set(chia_stats_inst.portable_size)
            chia_stats_plots_k32_og.set(chia_stats_inst.plots_k32_og)
            chia_stats_plots_k33_og.set(chia_stats_inst.plots_k33_og)
            chia_stats_plots_k32_portable.set(chia_stats_inst.plots_k32_portable)
            chia_stats_plots_k33_portable.set(chia_stats_inst.plots_k33_portable)
            chia_stats_total_size.set(chia_stats_inst.total_size)
            chia_stats_chia_farmed.set(chia_stats_inst.chia_farmed)
            chia_stats_ttw.set(chia_stats_inst.ttw)
            chia_stats_sync_status.set(chia_stats_inst.sync_status)
            
        if 'truepool_stats' in modules:
            #TBD
            pass
        
        sleep(COLLECTION_INTERVAL_SECONDS)
        
except KeyboardInterrupt:
    pass

print(f'\n\nThank you for using chiatter. I can only hope it wasn\'t too painfull. Bye!')
