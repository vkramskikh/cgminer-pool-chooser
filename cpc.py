#!/usr/bin/env python

import sys
import time
import json
import yaml
import socket
import argparse
from pycgminer import CgminerAPI
from data_providers import CoinwarzAPI, CryptsyAPI

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)
logger = logging.getLogger('cpc')


class CPC(object):
    def __init__(self, config):
        self.config = config
        self.cgminer = CgminerAPI(config['cgminer']['host'], config['cgminer']['port'])
        self.coinwarz = CoinwarzAPI(config['coinwarz'])
        self.cryptsy = CryptsyAPI(config['cryptsy'])

    def restart_cgminer(self):
        logger.info('Restarting CGMiner...')
        try:
            self.cgminer.restart()
        except ValueError:
            pass
        while True:
            try:
                self.cgminer.version()
            except socket.error:
                time.sleep(1)
            else:
                break
        logger.info('CGMiner restarted')

    def pools(self):
        pools = self.cgminer.pools()['POOLS']
        pools = filter(lambda pool: pool['Status'] == 'Alive', pools)
        for pool in pools:
            currency = self.config['pool_currency'].get(pool['URL'])
            if not currency:
                logger.warning('Unknown currency for pool %s', pool['URL'])
                continue
            pool['Currency'] = currency
        return pools


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CGMiner Pool Chooser')
    parser.add_argument(
        '--config', dest='config', type=argparse.FileType('r'), default='cpc.yaml'
    )
    args = parser.parse_args()

    cpc = CPC(yaml.load(args.config))

    cgminer_version = cpc.cgminer.version()['VERSION'][0]
    logger.info('Connected to CGMiner v{CGMiner} API v{API}'.format(**cgminer_version))

    merged_data = {}
    btc_price = None
    price_data = cpc.cryptsy.get_data()['return']['markets']
    difficulty_data = cpc.coinwarz.get_data()['Data']

    for label, currency_price_data in price_data.items():
        if currency_price_data['secondarycode'] != 'BTC':
            continue
        currency_data = merged_data[currency_price_data['primarycode']] = {}
        currency_data['price'] = float(currency_price_data['lasttradeprice'])
        currency_data['exchange_volume'] = float(currency_price_data['volume'])

    for currency_difficulty_data in difficulty_data:
        currency = currency_difficulty_data['CoinTag']
        if currency == 'BTC':
            btc_price = currency_difficulty_data['ExchangeRate']
            continue
        if currency not in merged_data:
            continue
        currency_data = merged_data[currency]
        currency_data['difficulty'] = currency_difficulty_data['Difficulty']
        currency_data['block_reward'] = currency_difficulty_data['BlockReward']
        currency_data['coins_per_day'] = 86400 * cpc.config['hashes_per_sec'] * currency_data['block_reward'] / (currency_data['difficulty'] * 2 ** 32)

    merged_data = {k: v for k, v in merged_data.iteritems() if 'coins_per_day' in v}

    if btc_price:
        for currency, currency_data in merged_data.items():
            currency_data['btc_per_day'] = currency_data['coins_per_day'] * currency_data['price']
            currency_data['usd_per_day'] = currency_data['btc_per_day'] * btc_price

    print json.dumps(merged_data, indent=2)
