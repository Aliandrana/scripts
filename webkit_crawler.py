#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set fenc=utf-8 ai ts=4 sw=4 sts=4 et:


import os
import sys
import signal
from urlparse import urlparse
from httplib import HTTPConnection

from PyQt4.QtCore import QUrl, QTimer, SIGNAL
from PyQt4.QtGui import QApplication
from PyQt4.QtNetwork import QNetworkProxy, QNetworkCookie, QNetworkCookieJar
from PyQt4.QtWebKit import QWebPage

TIMEOUT_MSECS = 5 * 60 * 1000

#::SOURCE http://stackoverflow.com/questions/5423013/pyqt-how-to-use-qwebpage-with-an-anonimous-proxy/5564898#5564898::
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


#::KUDOS Tudor Barbu <ul.enatom@uaim> ::
#::: http://blog.motane.lu/2009/07/07/downloading-a-pages-content-with-python-and-webkit/ ::
class Crawler( QWebPage ):
    def __init__(self):
        QWebPage.__init__(self)

    def crawl(self, url):
        QTimer.singleShot(TIMEOUT_MSECS, self._timeout)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.connect(self, SIGNAL('loadFinished(bool)'), self._finished_loading)
        self.mainFrame().load(QUrl(url))

    def load_cookies(self, url, cookie_strings):
        p = urlparse(url)

        cookies = list()
        for c in cookie_strings:
            n = c.find('=')
            name, value = c[:n], c[n+1:]
            cookie = QNetworkCookie(name, value)
            cookie.setDomain(p.netloc)
            cookies.append(cookie)

        cookiejar = QNetworkCookieJar()
        cookiejar.setAllCookies(cookies)
        self.networkAccessManager().setCookieJar(cookiejar)


    def _finished_loading( self, result ):
        """ When done loading, pring the result. """
        print unicode(self.mainFrame().toHtml())
        sys.exit(0)

    def _timeout(self):
        """ Called if the webpage has timed out."""
        sys.stderr.write("Timeout.\n")
        sys.exit(1)


def test_url(url):
    """ Tests if given url returns a valid response."""
    p = urlparse(url)
    conn = HTTPConnection(p.netloc, p.port)
    conn.request('HEAD', p.path)
    res = conn.getresponse()

    if res.status > 300 and res.status < 399:
        test_url(res.getheader('location'))
        return
    if res.status < 200 or res.status > 399:
        sys.stderr.write("%d: %s\n" % (res.status, res.reason))
        sys.exit(1)


def main():
    app = QApplication([])

    if len(sys.argv) < 2:
        sys.stderr.write("Arguments: url [cookie_name=value ...]\n")
        sys.exit()

    url = sys.argv[1]

    test_url(url)

    crawler = Crawler()
    if len(sys.argv) > 2:
        crawler.load_cookies(url, sys.argv[2:])
    crawler.crawl(url)

    sys.exit( app.exec_() )


if __name__ == '__main__':
	main()

