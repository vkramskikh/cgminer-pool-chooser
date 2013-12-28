import time
import json
import os.path
import urllib
import logging
logger = logging.getLogger(__name__)

class DataProviderAPI(object):
    def __init__(self, config):
        self.config = config

    def load_cached_data(self):
        with open(self.config['cache_file'], 'r') as f:
            return json.load(f)

    def get_data(self, fetch=False):
        if not fetch and os.path.exists(self.config['cache_file']) and \
                (os.path.getmtime(self.config['cache_file']) + self.config['cache_expiry'] > time.time()):
            logger.debug('Loading cached %s data', self.name)
            return self.load_cached_data()
        else:
            logger.info('Fetching %s data...', self.name)
            data = json.loads(self.fetch_data())
            if not self.check_data(data):
                raise ValueError('Query unsuccessful')
            logger.info('%s data loaded successfully', self.name)
            with open(self.config['cache_file'], 'w') as f:
                json.dump(data, f, indent=2)
            return data


class CoinwarzAPI(DataProviderAPI):
    name = 'Coinwarz'

    def check_data(self, data):
        return bool(data.get('Success'))

    def fetch_data(self):
        url = 'http://www.coinwarz.com/v1/api/profitability/'
        params = {'apikey': self.config['apikey'], 'algo': 'scrypt'}
        data = urllib.urlopen(url + '?' + urllib.urlencode(params)).read()
        return data


class CryptsyAPI(DataProviderAPI):
    name = 'Cryptsy'

    def fetch_data(self):
        url = 'http://pubapi.cryptsy.com/api.php?method=marketdatav2'
        return urllib.urlopen(url).read()

    def check_data(self, data):
        return bool(data.get('success'))
