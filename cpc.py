#!/usr/bin/env python

import sys
import time
import json
import yaml
import socket
import argparse
import traceback
from pycgminer import CgminerAPI
from data_providers import CoinwarzAPI, CryptsyAPI
from rating_calculator import RatingCalculator

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
        self.hashrate = self.config['hashrate']

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

    def cgminer_pools(self):
        pools = []
        for pool in self.cgminer.pools()['POOLS']:
            currency = self.config['pool_currency'].get(pool['URL'])
            if pool['Status'] != 'Alive':
                logger.warning('Pool %s status is %s', pool['URL'], pool['Status'])
            if not currency:
                logger.error('Unknown currency for pool %s', pool['URL'])
                continue
            pool['Currency'] = currency
            pools.append(pool)
        return pools

    def get_currencies(self):
        currencies = {}
        btc_price = None
        price_data = self.cryptsy.get_data()['return']['markets']
        difficulty_data = self.coinwarz.get_data()['Data']

        for label, currency_price_data in price_data.items():
            if currency_price_data['secondarycode'] != 'BTC':
                continue
            currency_data = currencies[currency_price_data['primarycode']] = {}
            currency_data['id'] = currency_price_data['primarycode']
            currency_data['name'] = currency_price_data['primaryname']
            currency_data['price'] = float(currency_price_data['lasttradeprice'])
            currency_data['exchange_volume'] = float(currency_price_data['volume'])

        for currency_difficulty_data in difficulty_data:
            currency = currency_difficulty_data['CoinTag']
            if currency == 'BTC':
                btc_price = currency_difficulty_data['ExchangeRate']
                continue
            if currency not in currencies:
                continue
            currency_data = currencies[currency]
            currency_data['profit_growth'] = currency_difficulty_data['ProfitRatio'] / currency_difficulty_data['AvgProfitRatio']
            currency_data['difficulty'] = currency_difficulty_data['Difficulty']
            currency_data['block_reward'] = currency_difficulty_data['BlockReward']
            currency_data['coins_per_day'] = 86400 * self.hashrate * currency_data['block_reward'] / (currency_data['difficulty'] * 2 ** 32)

        currencies = {k: v for k, v in currencies.iteritems() if 'coins_per_day' in v}

        for currency_data in currencies.values():
            currency_data['usd_per_day'] = currency_data['coins_per_day'] * currency_data['price'] * btc_price
            currency_data['rating'] = RatingCalculator.rate_currency(currency_data)

        return currencies


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CGMiner Pool Chooser')
    parser.add_argument(
        '--config', dest='config', type=argparse.FileType('r'), default='cpc.yaml'
    )
    parser.add_argument(
        '--data-only', dest='data_only', action='store_true'
    )
    parser.add_argument(
        '--no-priority-change', dest='no_priority_change', action='store_true'
    )
    parser.add_argument(
        '--no-loop', dest='no_loop', action='store_true'
    )
    args = parser.parse_args()

    cpc = CPC(yaml.load(args.config))

    while True:
        try:
            try:
                cgminer_version = cpc.cgminer.version()['VERSION'][0]
                logger.debug('Connected to CGMiner v{CGMiner} API v{API}'.format(**cgminer_version))
                cgminer_summary = cpc.cgminer.summary()['SUMMARY'][0]
                cpc.hashrate = cgminer_summary['MHS av'] * 1000000
            except Exception:
                logger.error('Unable to get CGMiner info: %s', traceback.format_exc())
                logger.info('Using hashrate from config: %d Kh/s', cpc.hashrate)

            currencies = cpc.get_currencies()
            prioritized_currencies = list(reversed(sorted(currencies.values(), key=lambda c: c['rating'])))
            if args.data_only:
                print json.dumps(prioritized_currencies, indent=2)
                exit(0)

            pools = cpc.cgminer_pools()
            active_pools = filter(lambda p: p['Stratum Active'], pools)
            active_currency = None
            if len(active_pools):
                active_currency = currencies[active_pools[0]['Currency']]
                active_currency_info = cpc.cgminer.coin()['COIN'][0]
                logger.info('Currently mining %s ($%.2f/d, diff %f, %d Kh/s) on %s',
                            active_currency['name'],
                            active_currency['usd_per_day'],
                            active_currency_info['Network Difficulty'],
                            cpc.hashrate / 1000,
                            active_pools[0]['URL'])
            else:
                logger.error('No active pools found')

            prioritized_currencies = [c for c in prioritized_currencies if c['id'] in (p['Currency'] for p in pools)]
            logger.info('Currency priority: %s', ', '.join('%s(%.2f,$%.2f/d)' % (c['name'], c['rating'], c['usd_per_day']) for c in prioritized_currencies))

            prioritized_pools = []
            for currency in prioritized_currencies:
                prioritized_pools += [p for p in pools if p['Currency'] == currency['id']]
            pool_priority = ','.join(str(p['POOL']) for p in prioritized_pools)
            logger.debug('Pool priority: %s', pool_priority)

            change_priority = True
            proposed_currency = prioritized_currencies[0]
            if active_currency:
                rating_ratio = proposed_currency['rating'] / active_currency['rating']
                currency_switch_threshold = cpc.config['currency_switch_threshold']
                if rating_ratio < currency_switch_threshold:
                    change_priority = False
                    logger.info('Rating ratio %f < %f, leaving pool priority as it is', rating_ratio, currency_switch_threshold)
                else:
                    logger.info('Rating ratio %f >= %f, applying new pool priority', rating_ratio, currency_switch_threshold)
            if not args.no_priority_change and change_priority:
                if cpc.config['cgminer']['restart_on_pool_change']:
                    cpc.restart_cgminer()
                response = cpc.cgminer.poolpriority(pool_priority)
                priority_changed = response['STATUS'][0]['STATUS'] == 'S'
                getattr(logger, priority_changed and 'info' or 'error')(response['STATUS'][0]['Msg'])
                if not priority_changed:
                    raise ValueError('Unable to change pool priority')

            if args.no_loop:
                break
        except Exception:
            logger.error('Error occured during main loop: %s', traceback.format_exc())
            logger.info('Retrying after %ds', cpc.config['retry_interval'])
            time.sleep(cpc.config['retry_interval'])
        else:
            logger.info('Retrying after %ds', cpc.config['pool_choose_interval'])
            time.sleep(cpc.config['pool_choose_interval'])
