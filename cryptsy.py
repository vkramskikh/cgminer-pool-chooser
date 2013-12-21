import time
import json
import os.path
import urllib
import logging
logger = logging.getLogger(__name__)

class CryptsyAPI(object):
    def __init__(self, config):
        self.config = config

    def fetch_data(self):
        url = 'http://pubapi.cryptsy.com/api.php?method=marketdatav2'
        return urllib.urlopen(url).read()

    def get_data(self):
        logger.info('Fetching Cryptsy data...')
        data = json.loads(self.fetch_data())
        if not data.get('success'):
            raise ValueError('Query unsuccessful')
        logger.info('Cryptsy data loaded successfully')
        return data
