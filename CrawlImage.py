#!/usr/bin/env python
# coding:utf-8

import os
import sys
import io

from library import CrawlImage

os.environ['PYTHONIOENCODING'] = 'UTF-8'

print 'CrawlImage Start!!'

URL = {
	"search" : "http://blog.hatena.ne.jp/tktomaru",
	"fail" : "failurl",
}

#CrawlImage.display_input_info()
crawlmarket = CrawlImage.CrawlPage()
crawlmarket.crawl_web(URL["search"],1)


