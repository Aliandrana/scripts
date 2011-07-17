#!/usr/bin/env python

import os
import sys
import signal
import urllib2

from PyQt4.QtCore import QUrl, SIGNAL
from PyQt4.QtGui import QApplication
from PyQt4.QtNetwork import QNetworkProxy
from PyQt4.QtWebKit import QWebPage


def set_proxy(proxy):
    proxy_url = QUrl(proxy)
    if unicode(proxy_url.scheme()).startswith('http'):
        protocol = QNetworkProxy.HttpProxy
    else:
        protocol = QNetworkProxy.Socks5Proxy
    QNetworkProxy.setApplicationProxy(
        QNetworkProxy(
            protocol,
            proxy_url.host(),
            proxy_url.port(),
            proxy_url.userName(),
            proxy_url.password()))
if 'HTTP_PROXY' in os.environ:
    set_proxy(os.environ['HTTP_PROXY'])


class Crawler( QWebPage ):
    def __init__(self):
        QWebPage.__init__(self)

    def crawl(self, url):
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	self.connect(self, SIGNAL('loadFinished(bool)'), self._finished_loading)
	self.mainFrame().load(QUrl(url))

    def _finished_loading( self, result ):
        """ When done loading, pring the result. """
	print unicode(self.mainFrame().toHtml())
	sys.exit(0)


def main():
    app = QApplication([])

    if len(sys.argv) != 2:
        sys.stderr.write("Expected argument url\n")
        sys.exit()

    url = sys.argv[1]
    crawler = Crawler()

    qurl = QUrl(url)
    user_agent = crawler.userAgentForUrl(qurl)

    uo = urllib2.build_opener()
    uo.addheaders = [('User-agent', user_agent)]

    try:
        up = uo.open(url)
        up.close()
    except urllib2.HTTPError as e:
        sys.stderr.write("HTTPError" + str(e.code) + "\n")
        del crawler # prevent segfault
        sys.exit(1)

    crawler.crawl(url)

    sys.exit( app.exec_() )

if __name__ == '__main__':
	main()

