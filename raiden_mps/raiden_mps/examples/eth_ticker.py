import json
from tkinter import ttk
import tkinter
import logging

import time

from raiden_mps import Client, DefaultHTTPClient
from raiden_mps.test.config import TEST_SENDER_PRIVKEY, TEST_RECEIVER_PRIVKEY
from raiden_mps.proxy.content import PaywalledProxyUrl
from raiden_mps.proxy.paywalled_proxy import PaywalledProxy
from raiden_mps.utils import make_channel_manager

log = logging.getLogger(__name__)


def start_proxy(receiver_privkey: str) -> PaywalledProxy:
    cm = make_channel_manager(receiver_privkey, 'eth_ticker_proxy.pkl')
    app = PaywalledProxy(cm)
    app.add_content(PaywalledProxyUrl(
        "[A-Z]{6}",
        1,
        lambda request: 'api.bitfinex.com/v1/pubticker/' + request
    ))
    app.run()
    return app


class ETHTicker(ttk.Frame):
    def __init__(
            self,
            sender_privkey: str,
            receiver_privkey: str = None,
            proxy: PaywalledProxy = None,
            httpclient: DefaultHTTPClient = None
    ):
        self.root = tkinter.Tk()
        ttk.Frame.__init__(self, self.root)
        self.root.title('µRaiden ETH Ticker')
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.pack()
        self.pricevar = tkinter.StringVar(value='0.00 USD')
        ttk.Label(self, textvariable=self.pricevar, font=('Helvetica', '72')).pack()

        if proxy:
            self.app = proxy
            self.app.add_content(PaywalledProxyUrl(
                "[A-Z]{6}",
                1,
                lambda request: 'api.bitfinex.com/v1/pubticker/' + request
            ))
        else:
            self.app = start_proxy(receiver_privkey)

        self.client = Client(sender_privkey)

        if httpclient:
            self.httpclient = httpclient
        else:
            self.httpclient = DefaultHTTPClient(
                self.client,
                'localhost',
                5000,
                initial_deposit=lambda x: 20 * x,
                topup_deposit=lambda x: 10 * x
            )

        self.active_query = False
        self.running = False

    def run(self):
        self.running = True
        self.root.after(1000, self.query_price)
        self.root.mainloop()

    def query_price(self):
        if not self.running:
            return
        self.active_query = True

        response = self.httpclient.run('ETHUSD')
        if response:
            ticker = json.loads(response.decode())
            price = float(ticker['last_price'])
            log.info('New price received: {:.2f} USD'.format(price))
            self.pricevar.set('{:.2f} USD'.format(price))
        else:
            log.warning('No response.')

        if not self.running:
            self.root.after(5000, self.query_price)
        self.active_query = False

    def close(self):
        log.info('Shutting down gracefully.')
        self.running = False
        self.root.destroy()
        self.httpclient.stop()
        # Sloppy handling of thread joining but works for this small demo.
        while self.active_query:
            time.sleep(1)

        self.httpclient.close_active_channel()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    ticker = ETHTicker(TEST_SENDER_PRIVKEY, TEST_RECEIVER_PRIVKEY)
    ticker.run()