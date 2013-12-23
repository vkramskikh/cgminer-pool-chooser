from math import exp

import logging
logger = logging.getLogger(__name__)

class RatingCalculator(object):

    @staticmethod
    def analyze_exchange_volume(currency):
        # price of coins with low exchange volume is usually not stable, reduce rating
        exchange_ratio = currency['exchange_ratio'] = currency['exchange_volume'] / currency['coins_per_day']
        exchange_volume_change = (exp(-1000.0 / exchange_ratio) - 0.6) / 2
        return exchange_volume_change

    @staticmethod
    def analyze_profit_growth(currency):
        # price of coins with profit grow ratio > 1.5 is not stable, reduce rating
        profit_growth = currency['profit_growth']
        profit_growth_change = 0
        if profit_growth > 1:
            profit_growth_change = -exp(-1.5 / (profit_growth - 1))
        return profit_growth_change

    @staticmethod
    def analyze_difficulty(currency):
        # coins with high difficulty don't let me switch PPLNS pools frequently, slightly reduce rating
        difficulty = currency['difficulty']
        difficulty_change = -exp(-200.0 / difficulty) / 5
        return difficulty_change

    @classmethod
    def rate_currency(cls, currency):
        rating = currency['usd_per_day']
        logger.debug('%s original rating is %f', currency['name'], rating)
        for method in ('analyze_exchange_volume', 'analyze_profit_growth', 'analyze_difficulty'):
            rating_change = getattr(cls, method)(currency)
            rating *= (rating_change + 1)
            logger.debug('%s rating changed by %s by %.2f%% to %f', currency['name'], method, rating_change * 100, rating)
        return rating
