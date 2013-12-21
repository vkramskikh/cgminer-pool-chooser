import time
import json
import os.path
import urllib
import logging
logger = logging.getLogger(__name__)

class CoinwarzAPI(object):
    def __init__(self, config):
        self.config = config

    def fetch_data(self):
        url = 'http://www.coinwarz.com/v1/api/apikeyinfo'
        params = {'apikey': self.config['apikey']}
        data = urllib.urlopen(url + '?' + urllib.urlencode(params)).read()
        return data

    def load_cached_data(self):
        with open(self.config['cache_file'], 'r') as f:
            return json.load(f)

    def get_data(self):
        if os.path.exists(self.config['cache_file']) and \
                (os.path.getmtime(self.config['cache_file']) + self.config['cache_expiry'] > time.time()):
            logger.info('Loading cached Coinwarz data')
            return self.load_cached_data()
        else:
            logger.info('Fetching Coinwarz data...')
            data = json.loads(self.fetch_data())
            if not data.get('Success'):
                raise ValueError('Query unsuccessful')
            logger.info('Data loaded successfully')
            with open(self.config['cache_file'], 'w') as f:
                json.dump(data, f, indent=2)
            return data

