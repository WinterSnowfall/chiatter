#!/usr/bin/env python3
'''
@author: Winter Snowfall
@version: 3.50
@date: 04/08/2025

Warning: Built for use with python 3.6+
'''

import logging
import os
import binascii
from datetime import datetime
from logging.handlers import RotatingFileHandler
from aiohttp.client_exceptions import ClientConnectorError
from chia.util.config import load_config
from chia.rpc.farmer_rpc_client import FarmerRpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.util import bech32m
from chia.cmds.farm_funcs import get_average_block_time
# uncomment for debugging purposes only
#import traceback

# logging configuration block
LOG_FILE_PATH = os.path.join('..', 'logs', 'chia_stats.log')
logger_file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=25165824, backupCount=1, encoding='utf-8')
LOGGER_FORMAT = '%(asctime)s %(levelname)s : %(name)s >>> %(message)s'
logger_file_handler.setFormatter(logging.Formatter(LOGGER_FORMAT))
# logging level for other modules
logging.basicConfig(format=LOGGER_FORMAT, level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.addHandler(logger_file_handler)

class chia_stats:
    '''gather stats using the chia RPC clients'''

    _logging_level = logging.WARNING

    _PLOT_BASE_KSIZE = 32
    # starts at k32 and goes up to k41 (should be enough
    # even for the k-raziest of plotters out there)
    _PLOT_KSIZES = 10
    _PLOT_KSIZE_RANGE = range(_PLOT_KSIZES)
    # will cater for C0 to C33, although only compression
    # levels up to C7 are oficialy supported as of now
    _PLOT_COMPRESSION_LEVELS = 34
    _PLOT_COMPRESSION_LEVEL_RANGE = range(_PLOT_COMPRESSION_LEVELS)
    
    # only 3 halving events are planned as per CHIP-0012
    _HALVING_EVENTS = 3
    # first halving occured on height 5045760, next will be on double that ammount
    _WON_BLOCK_HALVING_HEIGHTS = [5045760 * halving for halving in range(_HALVING_EVENTS + 1)]
    # 0.25 XCH is the initial won block transaction amount
    _WON_BLOCK_TRANSACTION_AMOUNTS = [int(250000000000 / (2 ** exp)) for exp in range(_HALVING_EVENTS + 1)]

    def __init__(self, logging_level):
        self._contract_address_filter = None
        self._decoded_puzzle_hash = None

        self._chia_farmed_prev = 0
        self._seconds_since_last_win_stale = False
        self._last_win_max_time = 0

        self.harvesters = 0
        self.plots_duplicates = 0
        self.plots_failed_to_open = 0
        self.plots_no_key = 0
        self.og_size = 0
        self.portable_size = 0
        self.plots_og = [0] * chia_stats._PLOT_KSIZES
        self.plots_portable = [0] * chia_stats._PLOT_KSIZES
        self.plots_clevel = [0] * chia_stats._PLOT_COMPRESSION_LEVELS
        self.sync_status = False
        self.difficulty = 0
        self.network_space_size = 0
        self.mempool_size = 0
        self.mempool_allocation = 0
        self.full_node_connections = 0
        self.og_time_to_win = 0
        self.portable_time_to_win = 0
        self.current_height = 0
        self.wallet_funds = 0
        self.chia_farmed = 0
        self.blocks_won = 0
        self.seconds_since_last_win = 0

        # defaults to 'WARNING' otherwise
        if logging_level == 'DEBUG':
            self._logging_level = logging.DEBUG
        elif logging_level == 'INFO':
            self._logging_level = logging.INFO

        # logging level for current logger
        logger.setLevel(self._logging_level)

        logger.debug('Loading chia configuration...')

        self._config = load_config(DEFAULT_ROOT_PATH, 'config.yaml')

        self._hostname = self._config['self_hostname']
        self._farmer_port = self._config['farmer']['rpc_port']
        self._fullnode_port = self._config['full_node']['rpc_port']
        self._wallet_port = self._config['wallet']['rpc_port']

    def clear_stats(self):
        self._chia_farmed_prev = 0
        self._seconds_since_last_win_stale = False
        self._last_win_max_time = 0

        self.harvesters = 0
        self.plots_duplicates = 0
        self.plots_failed_to_open = 0
        self.plots_no_key = 0
        self.og_size = 0
        self.portable_size = 0
        for ksize in chia_stats._PLOT_KSIZE_RANGE:
            self.plots_og[ksize] = 0
            self.plots_portable[ksize] = 0
        for clevel in chia_stats._PLOT_COMPRESSION_LEVEL_RANGE:
            self.plots_clevel[clevel] = 0
        self.sync_status = False
        self.difficulty = 0
        self.network_space_size = 0
        self.mempool_size = 0
        self.mempool_allocation = 0
        self.full_node_connections = 0
        self.og_time_to_win = 0
        self.portable_time_to_win = 0
        self.current_height = 0

    def set_won_block_transaction_fee(self, won_block_transaction_fee):
        # validate fee amount being between 1 mojo and 1 XCH
        if won_block_transaction_fee < 0.000000000001 or won_block_transaction_fee > 1:
            logger.warning('XCH_WON_BLOCK_TRANSACTION_FEE is out of bounds. Defaulting to 0.01 XCH.')
            won_block_transaction_fee = 0.01
        # convert to mojos (1000000000000 mojos = 1 XCH)
        chia_stats._WON_BLOCK_TRANSACTION_FEE = int(won_block_transaction_fee * 1000000000000)

        logger.debug(f'_WON_BLOCK_TRANSACTION_FEE: {chia_stats._WON_BLOCK_TRANSACTION_FEE}')

    def set_contract_address_filter(self, contract_address_filter):
        self._contract_address_filter = contract_address_filter

        decoded_bytes = bech32m.decode_puzzle_hash(self._contract_address_filter)
        self._decoded_puzzle_hash = '0x' + binascii.hexlify(decoded_bytes).decode('utf8')

        logger.debug(f'_decoded_puzzle_hash: {self._decoded_puzzle_hash}')

    async def collect_stats(self):
        logger.info('***** Starting data collection run *****')

        self.harvesters = 0
        self.plots_duplicates = 0
        self.plots_failed_to_open = 0
        self.plots_no_key = 0
        self.og_size = 0
        self.portable_size = 0
        for ksize in chia_stats._PLOT_KSIZE_RANGE:
            self.plots_og[ksize] = 0
            self.plots_portable[ksize] = 0
        for clevel in chia_stats._PLOT_COMPRESSION_LEVEL_RANGE:
            self.plots_clevel[clevel] = 0

        logger.info('Initializing clients...')

        farmer = await FarmerRpcClient.create(self._hostname, self._farmer_port,
                                              DEFAULT_ROOT_PATH, self._config)
        fullnode = await FullNodeRpcClient.create(self._hostname, self._fullnode_port,
                                                  DEFAULT_ROOT_PATH, self._config)
        wallet = await WalletRpcClient.create(self._hostname, self._wallet_port,
                                              DEFAULT_ROOT_PATH, self._config)

        try:
            logger.info('Fetching farmer state...')
            #########################################################
            # will scrape the local harvester as well as any remote harvesters
            harvesters = await farmer.get_harvesters()

            for harvester in harvesters['harvesters']:
                self.harvesters += 1

                self.plots_duplicates += len(harvester['duplicates'])
                self.plots_failed_to_open += len(harvester['failed_to_open_filenames'])
                self.plots_no_key += len(harvester['no_key_filenames'])

                for plot in harvester['plots']:
                    ksize = plot['size'] - chia_stats._PLOT_BASE_KSIZE
                    clevel = plot['compression_level']

                    # counterintuitively, pool_public key will have a value for OG plots
                    if plot['pool_public_key'] is not None:
                        self.og_size += plot['file_size']
                        self.plots_og[ksize] += 1
                        # OG plots won't have a compression level

                    # only count plots that match a specific puzzle hash (based on the contract address filter)
                    elif self._contract_address_filter is not None:
                        if plot['pool_contract_puzzle_hash'] == self._decoded_puzzle_hash:
                            self.portable_size += plot['file_size']
                            self.plots_portable[ksize] += 1
                            self.plots_clevel[clevel] += 1
                        else:
                            logger.debug('Different puzzle hash detected. Skipping plot.')
                    # if no filter is specified, process all plots, regardless of their puzzle hash
                    else:
                        self.portable_size += plot['file_size']
                        self.plots_portable[ksize] += 1
                        self.plots_clevel[clevel] += 1

            logger.debug(f'harvesters: {self.harvesters}')
            logger.debug(f'plots_duplicates: {self.plots_duplicates}')
            logger.debug(f'plots_failed_to_open: {self.plots_failed_to_open}')
            logger.debug(f'plots_no_key: {self.plots_no_key}')
            logger.debug(f'og_size: {self.og_size}')
            logger.debug(f'portable_size: {self.portable_size}')
            for ksize in chia_stats._PLOT_KSIZE_RANGE:
                logger.debug(f'plots_og_k{ksize + chia_stats._PLOT_BASE_KSIZE}: {self.plots_og[ksize]}')
            for ksize in chia_stats._PLOT_KSIZE_RANGE:
                logger.debug(f'plots_portable_k{ksize + chia_stats._PLOT_BASE_KSIZE}: {self.plots_portable[ksize]}')
            for clevel in chia_stats._PLOT_COMPRESSION_LEVEL_RANGE:
                logger.debug(f'plots_c{clevel}: {self.plots_clevel[clevel]}')
            #########################################################

            logger.info('Fetching blockchain state...')
            #########################################################
            blockchain = await fullnode.get_blockchain_state()

            self.sync_status = blockchain['sync']['synced']
            self.difficulty = blockchain['difficulty']
            self.network_space_size = blockchain['space']
            self.mempool_size = blockchain['mempool_size']
            self.mempool_allocation = int((blockchain['mempool_cost'] /
                                           blockchain['mempool_max_total_cost']) * 100)

            connections = await fullnode.get_connections()

            self.full_node_connections = 0
            for connection in connections:
                # only count full node connections (type 1)
                if connection['type'] == 1:
                    self.full_node_connections += 1

            average_block_time = await get_average_block_time(self._fullnode_port, DEFAULT_ROOT_PATH)

            if self.og_size != 0:
                self.og_time_to_win = int((average_block_time) /
                                          (self.og_size / self.network_space_size))
            if self.portable_size != 0:
                self.portable_time_to_win = int((average_block_time) /
                                                (self.portable_size / self.network_space_size))

            logger.debug(f'sync_status: {self.sync_status}')
            logger.debug(f'difficulty: {self.difficulty}')
            logger.debug(f'network_space_size: {self.network_space_size}')
            logger.debug(f'mempool_size: {self.mempool_size}')
            logger.debug(f'mempool_allocation: {self.mempool_allocation}')
            logger.debug(f'full_node_connections: {self.full_node_connections}')
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

            current_height = await wallet.get_height_info()
            self.current_height = current_height.height
            main_wallet = await wallet.get_wallets()
            # assume only one wallet exists - might want to alter it in the future
            main_wallet_balance = await wallet.get_wallet_balance(main_wallet[0]['id'])
            self.wallet_funds = main_wallet_balance.get('confirmed_wallet_balance')

            logger.debug(f'chia_farmed: {self.chia_farmed}')
            logger.debug(f'current_height: {self.current_height}')
            logger.debug(f'wallet_funds: {self.wallet_funds}')

            # simple transaction-based block win time detection logic
            if self._seconds_since_last_win_stale:
                # needed to determine end transaction for the transaction query below
                wallet_transaction_count = await wallet.get_transaction_count(main_wallet[0]['id'])
                logger.debug(f'wallet_transaction_count: {wallet_transaction_count}')
                # 0 to wallet_transaction_count will list all the transactions in the wallet
                wallet_transactions = await wallet.get_transactions(main_wallet[0]['id'], 0, wallet_transaction_count)

                self.blocks_won = 0
                current_transaction_no = 0
                # will be set to 0 on the initial calculation
                height_selector = -1
                next_halving_height = 0
                halving_events_exhausted = False
                
                for transaction_record in wallet_transactions:
                    current_transaction_no += 1
                    # ignore outbound transactions
                    if int(transaction_record.sent) == 0:
                        if not halving_events_exhausted and transaction_record.confirmed_at_height >= next_halving_height:
                            height_selector += 1
                            won_block_amount = chia_stats._WON_BLOCK_TRANSACTION_AMOUNTS[height_selector]
                            logger.debug(f'Won block amount is: {won_block_amount}')
                            if height_selector == len(chia_stats._WON_BLOCK_HALVING_HEIGHTS) - 1:
                                logger.debug(f'Halving heights exhausted.')
                                halving_events_exhausted = True
                            else:
                                next_halving_height = chia_stats._WON_BLOCK_HALVING_HEIGHTS[height_selector + 1]
                                logger.debug(f'Next halving height is: {next_halving_height}')
                        
                        # use a delta interval to determine a won block, since any transaction fees
                        # for a won block will be received within the same transaction
                        if (int(transaction_record.amount) >= won_block_amount and
                            int(transaction_record.amount) <= won_block_amount +
                            chia_stats._WON_BLOCK_TRANSACTION_FEE):
                            self.blocks_won += 1
                            logger.debug(f'Transaction #{current_transaction_no} has a block win share amount.')
                            current_time = int(transaction_record.created_at_time)
                            if current_time > self._last_win_max_time:
                                self._last_win_max_time = current_time

                if self._last_win_max_time == 0:
                    logger.warning('Unable to find a valid block win transaction.')

                self._seconds_since_last_win_stale = False
            else:
                logger.info('Skipping _last_win_max_time update until next block win.')

            if self._last_win_max_time != 0:
                self.seconds_since_last_win = int(datetime.timestamp(datetime.now())) - self._last_win_max_time
            else:
                self.seconds_since_last_win = 0

            logger.debug(f'blocks_won: {self.blocks_won}')
            logger.debug(f'seconds_since_last_win: {self.seconds_since_last_win}')
            #########################################################

        except ClientConnectorError:
            logger.warning('Chia RPC API call failed. Full node may be down.')

        except Exception as exception:
            logger.error(f'Encountered following exception: {type(exception)} {exception}')
            # uncomment for debugging purposes only
            #logger.error(traceback.format_exc())
            raise

        finally:
            farmer.close()
            fullnode.close()
            wallet.close()

        logger.info('***** Data collection complete *****')
