from math import exp

import logging
logger = logging.getLogger(__name__)

class RatingCalculator(object):

    @staticmethod
    def analyze_exchange_volume(currency):
        exchange_ratio = currency['exchange_volume'] / currency['coins_per_day']
        exchange_volume_change = (1 / exp(1000.0 / exchange_ratio) - 0.6) / 2
        return exchange_volume_change

    @classmethod
    def rate_currency(cls, currency):
        from math import exp
        rating = currency['usd_per_day']
        logger.debug('%s original rating is %f', currency['name'], rating)
        for method in ('analyze_exchange_volume',):
            rating_change = getattr(cls, method)(currency)
            rating *= (rating_change + 1)
            logger.debug('%s rating changed by %s by %.2f%% to %f', currency['name'], method, rating_change * 100, rating)
        return rating
