#!/usr/bin/env python

import sys
import time
import json
import yaml
import socket
import argparse
from pycgminer import CgminerAPI
from coinwarz import CoinwarzAPI
from cryptsy import CryptsyAPI

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
        self.cryptsy = CryptsyAPI(config['coinwarz'])

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

    print json.dumps(cpc.cryptsy.get_data(), indent=2)
