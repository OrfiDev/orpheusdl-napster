import base64, json
from utils.utils import create_requests_session


class NapsterAPI:
    def __init__(self, exception, api_key, customer_secret):
        self.API_URL = 'https://api.napster.com'
        self.API_VERSION = 'v2.2'
        self.s = create_requests_session()
        self.exception = exception

        # api key and customer secret are both uuid4's that are stored as base64, like the access token
        self.api_key = api_key
        self.customer_secret = customer_secret
        self.headers = {
            'apikey': api_key,
            'Connection': 'Keep-Alive',
            'User-Agent': 'okhttp/4.9.1'
        }

        self.access_token = None
        self.catalog_region = None

    def login(self, username, password, current_timestamp):
        basic_token = base64.b64encode(f'{self.api_key}:{self.customer_secret}'.encode()).decode()
        data = {
            'username': username,
            'password': password,
            'grant_type': 'password'
        }

        headers = {**self.headers, 'Authorization': 'Basic ' + basic_token}
        r = self.s.post(self.API_URL + '/oauth/token', data, headers=headers)
        if r.status_code != 200: raise self.exception(r.json()['message'])

        r = r.json()
        self.access_token = r['access_token']
        self.catalog_region = r['catalog']

        r2 = self._get('me/account')
        return r['access_token'], r['refresh_token'], r['expires_in'] + current_timestamp, r['catalog'], \
            r2['account']['entitlements']['maxStreamBitrate'], r2['account']['entitlements']['canStreamHiRes']
    
    def refresh_login(self, refresh_token, current_timestamp):
        data = {
            'client_id': self.api_key,
            'client_secret': self.customer_secret,
            'refresh_token': refresh_token,
            'response_type': 'token',
            'grant_type': 'refresh_token'
        }

        r = self.s.post(self.API_URL + '/oauth/access_token', data, headers=self.headers)
        if r.status_code != 200: raise self.exception(r.json()['message'])

        r = r.json()
        self.access_token = r['access_token']
        return r['access_token'], r['expires_in'] + current_timestamp

    def _get(self, url, params = {}):
        headers = {**self.headers, 'Authorization': 'Bearer ' + self.access_token}
        r = self.s.get(f'{self.API_URL}/{self.API_VERSION}/{url}', params=params, headers=headers)
        if r.status_code not in [200, 201, 202]: raise self.exception(r.json()['message'])
        return r.json()
    
    def search(self, query_type, query, limit = 10, offset = 0):
        params = {
            'query': query,
            'type': query_type,
            'per_type_limit': limit,
            'catalog': self.catalog_region,
            'rights': '2',
            'offset': offset
        }
        return self._get('search', params)['search']['data'][query_type+'s']
    
    def get_items_list(self, item_type, item_ids, item_sub='', item_string='', limit=50):
        if isinstance(item_ids, list): item_ids = ','.join(item_ids)
        r = self._get(f'{item_type}/{item_ids}' + (f'/{item_sub}' if item_sub else ''), {'limit': limit})
        results = r[item_string if item_string else item_type] if item_ids else []
        
        requested, total = r['meta']['returnedCount'], r['meta']['totalCount']
        if not total: total = 0
        while requested < total:
            r = self._get(f'{item_type}/{item_ids}' + (f'/{item_sub}' if item_sub else ''), {'limit': limit, 'offset': requested})
            results += r[item_string if item_string else item_type] if item_ids else []
            requested += r['meta']['returnedCount']

        return results

    def get_items_dict(self, item_type, item_ids, item_sub='', item_string='', limit=50):
        return {i['id']: i for i in self.get_items_list(item_type, item_ids, item_sub, item_string, limit)}
    
    def get_string_from_items_list(self, item_type, item_ids, string_key, item_sub='', item_string='', limit=50):
        return {i['id']: i[string_key] for i in self.get_items_list(item_type, item_ids, item_sub, item_string, limit)}
    
    def get_stream_url(self, bitrate, codec, track_id):
        params = {
            'bitrate': bitrate,
            'format': codec,
            'protocol': '',
            'track': track_id
        }
        return self._get('streams', params)['streams'][0]['url']
