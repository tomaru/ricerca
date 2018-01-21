#!/usr/bin/env python
# coding:utf-8

import os
import re
import sys
import datetime
import ConfigParser
import requests

from time import sleep

import codecs
from bs4 import BeautifulSoup

from pymongo import MongoClient
import chardet

import imagehash
from PIL import Image

#=====================================================#

client = MongoClient('localhost', 27017)
db = client['test-database']
collection = db["Index"]

#=====================================================#
#ハミング距離
def getHammingDistance(n,m):
	data=n ^ m
	data=(data & 0x5555555555555555)+((data & 0xAAAAAAAAAAAAAAAA)>> 1)
	data=(data & 0x3333333333333333)+((data & 0xCCCCCCCCCCCCCCCC)>> 2)
	data=(data & 0x0F0F0F0F0F0F0F0F)+((data & 0xF0F0F0F0F0F0F0F0)>> 4)
	data=(data & 0x00FF00FF00FF00FF)+((data & 0xFF00FF00FF00FF00)>> 8)
	data=(data & 0x0000FFFF0000FFFF)+((data & 0xFFFF0000FFFF0000)>>16)
	data=(data & 0x00000000FFFFFFFF)+((data & 0xFFFFFFFF00000000)>>32)
	return data
		
#=====================================================#

def save_db(url, dhash):
	log_depth = 1
	log_name = "SaveHash"
	
	data = {}
	data['img_url'] = url
	data['dhash'] = dhash 
	
	collection.insert(data)
	CrawlPage.log(log_depth,log_name, "SUCCESS: dhash: %s  url = %s" % (dhash,  url))
   
#=====================================================#

# 画像hashを保存する
def save_dhash_image(path, url):
	entry = collection.find_one({'img_url': url})

	#hash=imagehash.dhash(image)
	hash = imagehash.dhash(Image.open(path))
	hash_Str = unicode(hash)
		
	if entry:
		if hash_Str != "" and (hash_Str not in entry['dhash']):
			save_db(url, hash_Str)
		return
	# not found
	save_db(url, hash_Str)

#=====================================================#

# 画像hashを検索する
def search_dhash_image(path):
	hash = imagehash.dhash(Image.open(path))
	
	entry = collection.find_one({'dhash': unicode(hash)})
	
	if entry:
		print "FOUD image to use dhash"
		return
	print "NOT found image to use dhash"
	
#=====================================================#
def add_to_index(keyword, url):
	entry = collection.find_one({'keyword': keyword})
	if entry:
		if url not in entry['url']:
			entry['url'].append(url)
			collection.save(entry)
		return
	# not found, add new keyword to index
	collection.insert({'keyword': keyword, 'url': [url]})
	
#=====================================================#
#画像のURLがすでにダウンロード済みかどうかを判定する
def exist_index(keyword, url):
	entry = collection.find_one({'keyword': keyword})
	if entry:
		if url not in entry['url']:
			# not found
			return 0
		# FOUND
		return 1
	# not found
	return 0

#=====================================================#

def print_debug_log(str):
#	if not __debug__:
	print(str)

#=====================================================#
def check_encoding(str):
	print chardet.detect(str)
		
#=====================================================#
def guess_charset(data):  
	f = lambda d, enc: d.decode(enc) and enc  
  
	try: return f(data, 'utf-8')  
	except: pass  
	try: return f(data, 'shift-jis')  
	except: pass  
	try: return f(data, 'ascii')  
	except: pass  
	try: return f(data, 'euc-jp')  
	except: pass  
	try: return f(data, 'iso2022-jp')  
	except: pass  
	return None  
  
#=====================================================#
def conv(data):  
	charset = guess_charset(data)  
	u = data.decode(charset)  
	return u.encode('utf-8')  
	
#=====================================================#
def read_config(tag, name):
	""" read config file and  return value."""
	config_path = './config/config.ini'
	try:
		ini_reader = ConfigParser.SafeConfigParser()
		ini_reader.read(config_path)
		return ini_reader.get(tag, name)
	except ConfigParser.NoSectionError:
		exit("[Exit] ERROR: ConfigParser.NoSectionError, tag: %s, name: %s"
			% (tag, name))
	except ConfigParser.NoOptionError:
		exit("[Exit] ERROR: ConfigParser.NoOptionError, tag: %s, name: %s"
			% (tag, name))

#=====================================================#

def display_input_info():
	""" dump set conditions in the config file """
	print "I'll write this content.\n"

#=====================================================#
# CrawlPageクラス
#=====================================================#

class CrawlPage(object):
	""" Crawlするクラス"""

	DEFAULT_TIMEOUT = int(read_config("Access", "timeout"))
	MAX_ACCESS_COUNT = int(read_config("Access", "max_access_count"))

#=====================================================#

# log 出力関数
	@staticmethod
	def log(depth, tag_name, msg):
		if depth == 0: print "\n"
		print "\t" * depth +  "[%s] %s" % (tag_name ,msg)

#=====================================================#

# html or csv の出力関数
	@staticmethod
	def _file_write(file_name, data, file_type="html", url=None, params=None):
		log_name = "Write to File"
		log_depth = 1

		separate_str = "\n--------------------\n"
		d = datetime.datetime.today()
		date_str = "%s-%s-%s_%s:%s:%s" % (d.year, d.month, d.day, d.hour, d.minute, d.second)

		if file_type == "html":
			dir_path = read_config("Log", "html_dir")
			# OSによって決まっているセパレータ記号に置換する
			dir_path = dir_path.replace('/',os.sep)
			name_extension = ".html"
		elif file_type == 'csv':
			dir_path = read_config("Log", "html_dir")
			# OSによって決まっているセパレータ記号に置換する
			dir_path = dir_path.replace('/',os.sep)
			name_extension = ".csv"
		else:
			dir_path = read_config("Log", "dir")
			# OSによって決まっているセパレータ記号に置換する
			dir_path = dir_path.replace('/',os.sep)
			name_extension = ".log"

		# ":"はWindows では使えないため置換する
		date_str = date_str.replace(":", "_");
		file_path = os.path.join(dir_path, file_name + "~" + date_str + name_extension)
		#CrawlPage.log(log_depth,log_name, "try to write to file: %s" % (file_path))
		try:
			if file_type == 'html':
				f = open(file_path, 'w')
			else:
				f = open(file_path, 'wb')
			f.write(data)

			if not url is None: f.write(separate_str + "url: %s" %(url))
			if not params is None: f.write(separate_str + "request parameter: %s" %(params))

			f.close()
			CrawlPage.log(log_depth,log_name, "SUCCESS: write to file: %s" % (file_path))
			return True, None
		except IOError:
			CrawlPage.log(log_depth,log_name, "SUCCESS: write to file: %s" % (file_path))
			return False, "Occured IOError"
		except:
			CrawlPage.log(log_depth,log_name, "SUCCESS: write to file: %s" % (file_path))
			return False, "Occured Something Error" 

#=====================================================#

	def __init__(self):
		""" initialize: set urllib2.opener """
		print_debug_log( "=== Callled : " + sys._getframe().f_code.co_name + " ===" )
		self.buy_push_flg = False
#		self.select_flights = map(int, read_config("config", "candidate_flights").strip().split(','))

#=====================================================#

# 引数のURLで情報を要求する
	def _open_url(self, url, params=None):
		""" try to access to `url` """
		decoded_html= ""
		
		log_depth = 1
		log_name = "Trying to Open Url"

		for i in range(self.MAX_ACCESS_COUNT):
			try:
				#self.log(log_depth, log_name, "access to %s (access count: %d)\n\t\t\tparams: %s" % (url, i+1, params))
				timeout = self.DEFAULT_TIMEOUT + i
				
				headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
				page = requests.get(url, timeout=timeout, params=params, headers=headers)
				
				
				if page.status_code == requests.codes.ok:
					# 取得成功
					self.log(log_depth, log_name, "SUCCESS: access to %s" % (url))
					
					#check_encoding(page.content)
					# HTMLをデコード
					if( page.content != "" ):
						content_type = page.headers["content-type"]
						if 'image' not in content_type:
							decoded_html = conv(page.content)
					#check_encoding(decoded_html)
				
					# ログとしてHTMLを書き込むかどうか判定
					if int(read_config("Log", "enable")) == 1:
						self._file_write("PAGE", decoded_html,file_type="html", url=url, params=params)
						
					return decoded_html
				else:
					self.log(log_depth, log_name, "FAILURE: access to %s" % (url))
			except requests.exceptions.RequestException as e:  # This is the correct syntax
				self.log(log_depth, log_name, "FAILURE: access to %s" % (url))
		return decoded_html
		#sys.exit("[EXIT] cannot reach %s" % (url))

#=====================================================#

# 画像をダウンロードする
	def download_image(self, url, timeout = 10):
		log_depth = 1
		log_name = "Down Image"
		response = requests.get(url, allow_redirects=False, timeout=timeout)
			
		if response.status_code == requests.codes.ok:
			self.log(log_depth, log_name, "SUCCESS: access to %s" % (url))
		else:
			self.log(log_depth, log_name, "FAILURE: access to %s" % (url))
			e = Exception("HTTP status: " + response.status_code)
			raise e

		content_type = response.headers["content-type"]
		if 'image' not in content_type:
			e = Exception("Content-Type: " + content_type)
			raise e

		return response.content

#=====================================================#

# 画像を保存する
	def save_image(self, url, image):
		log_depth = 1
		log_name = "Save Image"
		
		file_path = ""
		d = datetime.datetime.today()
		date_str = "%s-%s-%s_%s:%s:%s" % (d.year, d.month, d.day, d.hour, d.minute, d.second)

		dir_path = read_config("Log", "img_dir")
		# OSによって決まっているセパレータ記号に置換する
		dir_path = dir_path.replace('/',os.sep)
		filename = os.path.basename(url)
		file_name, ext = os.path.splitext(filename)
		name_extension = ext

		# ":"はWindows では使えないため置換する
		date_str = date_str.replace(":", "_");

		file_path = os.path.join(dir_path, file_name + "~" + date_str + ".txt")
		with open(file_path, "w") as fout:
			fout.write(url)
			
		file_path = os.path.join(dir_path, file_name + "~" + date_str + name_extension)
		
		with open(file_path, "wb") as fout:
			fout.write(image)
		self.log(log_depth, log_name, "SUCCESS: save = %s" % (url))
		
		return file_path

#=====================================================#
	def robot_aceess_check(self, html):
		log_depth = 1
		log_name = "robots"
		#check_encoding(html)
		soup = BeautifulSoup(html, "html5lib")
		meta = soup.find_all('meta',
								attrs={"name":"robots"},
								content=lambda x: "nofollow" in unicode(x).lower() or "noarchive" in unicode(x).lower())
		if ( len(meta) > 0 ):
			self.log(log_depth, log_name, "FAILURE: access to meta = %s" % (meta))
			return 0
		else:
			self.log(log_depth, log_name, "SUCCESS: access to meta = %s" % (meta))
			return 1

#=====================================================#

	def _img_found(self, url):
		# print "img found"
		# すでにurlはダウンロード済みか判定する
		
		if(exist_index(os.path.basename(url), url)):
			# ダウンロード済みだった
			log_depth = 1
			log_name = "IMAGE"
			self.log(log_depth, log_name, "FOUND: not add = %s" % (url))
		else:
			# 未ダウンロードのため画像をダウンロードする
			log_depth = 1
			log_name = "IMAGE"
			self.log(log_depth, log_name, "NOT FOUND: add = %s" % (url))
			image = self.download_image(url)
			save_img_file_path = self.save_image(url, image)
			add_to_index(os.path.basename(url), url)
			save_dhash_image(save_img_file_path, url)
			
	def _extract_url_links(self,html):
		"""extract url links
		>>> _extract_url_links('aa<a href="link1">link1</a>bb<a href="link2">link2</a>cc')
		['link1', 'link2']
		"""
				
		get_image_extensions = {".jpg", ".bmp", ".png"}
		get_html_extensions = {".html", ".htm"}
		
		crawlpages = []
		if ( self.robot_aceess_check(html) ):
			# Crawl OK!!			
			soup = BeautifulSoup(html, "html.parser")
			links = soup.find_all('a')
			for link in links:
				imglinks = soup.find_all('img')
				for imglink in imglinks:
					img_url = imglink.get("src")
					if( img_url!=""):
						self. _img_found(img_url)
						
				# hrefリンクが"http://"または"https://"で始まるURLのうち、refにnofollowがないURLを対象とする
				if ('href' in link.attrs and ('http://' in link.attrs['href'] or 'https://' in link.attrs['href'] ) and link.get("rel") != "nofollow"):
					url = link.get("href")
					# URLの拡張子を取得する
					urlleft, ext = os.path.splitext(url.split("/")[-1])
					# htmlファイルのPATHの場合
					if ext in get_html_extensions:
						crawlpages.append(url)
					# 画像ファイルのPATHの場合
					if ext in get_image_extensions:
						# print "img found"
						# すでにurlはダウンロード済みか判定する
						self. _img_found(img_url)
		# クロールした結果、新しく発見したURLを返す
		return crawlpages
		
#=====================================================#
	
	def crawl_web(self,seed, max_depth):
		print_debug_log( "=== Callled : " + sys._getframe().f_code.co_name + " ===" )
		log_name = "crawl_web Phase"
		log_depth = 0
		
		page_set = set([seed])
		to_crawl = []
		to_crawl.append(page_set)
		
		length = len(to_crawl)
		crawl_len = []
		crawl_len.append(length)
		
		crawled = []
		next_depth = []
		depth = -1
		while to_crawl and depth <= max_depth:
			#print "========="
			#print to_crawl
			#print "========="
			
			page_set = to_crawl.pop()
			page_url = page_set.pop()
			
			if len(page_set) != 0:
				to_crawl.append(page_set)
			
			length = crawl_len.pop()
			
			if length == 1:
				depth += 1
				self.log(log_depth, log_name, "DEPTH = %d" % (depth))
			else:
				crawl_len.append(length - 1)

			if page_url not in crawled:
				#params = {u"p" : u"apple"}
				#html = self._open_url(page_url, params)
				html = self._open_url(page_url)
				if( html != "" ):
					# アクセスしたページにインデックス付与する
					#add_page_to_index(page_url, html)
					# アクセスしたページのリンクを追加する
					add_page_set = set(self._extract_url_links(html))
					#クロール個数追加
					crawl_len = [len(add_page_set)] + crawl_len
					# クロール済みリストに追加
					crawled.append(page_url)
					to_crawl = [add_page_set] + to_crawl
				sleep(1)
			
		print "===table list==="
		for doc in collection.find():
			print(doc)
	
#=====================================================#

if __name__ == "__main__":

	print_debug_log( "=== Callled : " + sys._getframe().f_code.co_name + " ===" )
	
	crawlmarket = CrawlImage.CrawlPage()
	crawlmarket.prepare_push()

# End of File #
