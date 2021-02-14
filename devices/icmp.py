from icmplib import ping
import time
import threading
import logging
logger = logging.getLogger(__name__)


class icmp:
    def __init__(self, addr, interval):
        self.addr = addr
        self.interval = interval
        self.data = {
            'status': False,
            'msg': '',
            'data': {}
        }
        self.ping = threading.Thread(
            target=self.pingThread, daemon=True).start()

    def pingThread(self):
        logger.info('Thread started')
        while True:
            host = ping(self.addr, count=1, interval=1, timeout=2)
            if host.is_alive:
                self.data['status'] = True
                self.data['data'] = host
            else:
                self.data['status'] = False
                self.data['msg'] = 'Device seems down'
                logger.warn('Cannot ping through {}'.format(self.addr))
            time.sleep(self.interval)

    def getData(self):
        return self.data
