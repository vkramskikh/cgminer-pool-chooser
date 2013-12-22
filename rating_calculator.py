from math import exp

import logging
logger = logging.getLogger(__name__)

class RatingCalculator(object):

    @staticmethod
    def analyze_exchange_volume(currency):
        exchange_ratio = currency['exchange_ratio'] = currency['exchange_volume'] / currency['coins_per_day']
        exchange_volume_change = (exp(-1000.0 / exchange_ratio) - 0.6) / 2
        return exchange_volume_change

    @staticmethod
    def analyze_profit_growth(currency):
        profit_growth = currency['profit_growth']
        profit_growth_change = 0
        if profit_growth > 1:
            profit_growth_change = -exp(-1.5 / (profit_growth - 1))
        return profit_growth_change

    @staticmethod
    def analyze_difficulty(currency):
        difficulty = currency['difficulty']
        difficulty_change = -exp(-200.0 / difficulty) / 5
        return difficulty_change

    @classmethod
    def rate_currency(cls, currency):
        from math import exp
        rating = currency['usd_per_day']
        logger.debug('%s original rating is %f', currency['name'], rating)
        for method in ('analyze_exchange_volume', 'analyze_profit_growth', 'analyze_difficulty'):
            rating_change = getattr(cls, method)(currency)
            rating *= (rating_change + 1)
            logger.debug('%s rating changed by %s by %.2f%% to %f', currency['name'], method, rating_change * 100, rating)
        return rating
