import requests
import urllib.parse as urlparse
import threading
import time
import websocket as ws
import json
import ssl


class EdgeOS:
    def __init__(self, url, username, password, verifySSL=True):
        print('[EdgeOS] Initializing')
        self.url = url
        self.username = username
        self.password = password
        self.status = False
        self.errorMsg = 'Connecting to router'
        self.session = requests.session()
        self.session.verify = verifySSL
        self.data = {
            'speed': {
                'last_update': 0,
                'interfaces': {
                }
            }
        }
        self.ws = None
        self.establish()
        self.start()

    def establish(self):
        try:
            res = self.session.post(self.url, data={
                'username': self.username,
                'password': self.password
            }, allow_redirects=False)
            if res.status_code == 200:
                self.errorMsg = 'Invalid credential'
                print('[EdgeOS] Authentication failed')
            self.status = True
            print('[EdgeOS] API connected')
            self.openWebsocket()
        except:
            self.errorMsg = 'Router seems down'
            print('[EdgeOS] Unable to connect')

    def keepAlive(self):
        while True:
            try:
                res = self.session.get(urlparse.urljoin(
                    self.url, '/api/edge/heartbeat.json'), params={'_': int(time.time() * 1000)})
                if res.status_code == 403:
                    print('[EdgeOS] Restoring session')
                    # Session failure
                    self.status = False
                    self.errorMsg = 'Connecting to router'
                    self.establish()
                data = res.json()
                if data['SESSION'] == False:
                    print('[EdgeOS] Restoring session')
                    self.status = False
                    self.errorMsg = 'Connecting to router'
                    self.establish()
            except:
                self.status = False
                self.errorMsg = 'Router seems down'
            time.sleep(10)

    def start(self):
        self.keepAliveThread = threading.Thread(
            target=self.keepAlive, daemon=True)
        self.keepAliveThread.start()

    def on_ws_open(self):
        print('[EdgeOS] WS connection opened')
        self.wsData = {
            'length': 0,
            'buffer': ''
        }
        payload = json.dumps({
            'SESSION_ID': self.session.cookies.get_dict()['PHPSESSID'],
            'SUBSCRIBE': [
                {
                    'name': 'interfaces',
                },
                {
                    'name': 'system-stats'
                },
                {
                    'name': 'export'
                }
            ],
            'UNSUBSCRIBE': []
        }) + '\n'
        self.ws.send('{}\n{}'.format(len(payload), payload))

    def on_ws_message(self, message):
        length = int(message.split('\n')[0])
        payload = '\n'.join(message.split('\n')[1:])
        self.wsData['length'] = length
        self.wsData['buffer'] = self.wsData['buffer'] + payload
        # If match, craft directly
        # Else just drop the packet, IDK how to handle gracefully
        if len(payload) == length:
            data = json.loads(payload)
            if 'interfaces' in data:
                if self.data['speed']['last_update'] != 0:
                    for interface in data['interfaces']:
                        if interface in self.data['interfaces']:
                            orig_rx = int(
                                self.data['interfaces'][interface]['stats']['rx_bytes'])
                            new_rx = int(data['interfaces']
                                         [interface]['stats']['rx_bytes'])
                            orig_tx = int(
                                self.data['interfaces'][interface]['stats']['tx_bytes'])
                            new_tx = int(data['interfaces']
                                         [interface]['stats']['tx_bytes'])
                            duration = time.time() - \
                                self.data['speed']['last_update']
                            self.data['speed']['interfaces'][interface] = {
                                'rx': (new_rx - orig_rx) / duration,
                                'tx': (new_tx - orig_tx) / duration
                            }
                self.data['speed']['last_update'] = time.time()
            self.data.update(data)

    def on_ws_error(self, error):
        print('[EdgeOS] WS error')
        print(error)

    def on_ws_close(self):
        print('[EdgeOS] WS closed')

    def on_ws_ping(self):
        payload = json.dumps({
            'CLIENT_PING': '',
            'SESSION_ID': self.session.cookies.get_dict()['PHPSESSID']
        }) + '\n'
        self.ws.send('{}\n{}'.format(len(payload), payload))

    def _openWebsocket(self):
        if self.ws:
            self.ws.close()
        # Setup WS connection
        url = list(urlparse.urlsplit(self.url))
        url[0] = 'wss'
        url = urlparse.urlunsplit(url)
        url = urlparse.urljoin(url, 'ws/stats')
        self.ws = ws.WebSocketApp(url, on_open=self.on_ws_open, on_close=self.on_ws_close,
                                  on_message=self.on_ws_message, on_error=self.on_ws_error,
                                  on_ping=self.on_ws_ping)
        if self.session.verify == True:
            self.ws.run_forever(ping_interval=30)
        else:
            self.ws.run_forever(ping_interval=30, sslopt={
                                'cert_reqs': ssl.CERT_NONE,
                                'check_hostname': False})

    def openWebsocket(self):
        threading.Thread(target=self._openWebsocket, daemon=True).start()

    def getData(self):
        if self.status == False:
            return {
                'status': False,
                'msg': self.errorMsg,
                'data': {}
            }
        else:
            return {
                'status': True,
                'msg': '',
                'data': self.data
            }
