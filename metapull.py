#!/usr/bin/env python

# takes a domain and check for filetypes
# downloads each result

import logging
import urllib2
from urllib import quote_plus, unquote_plus
from BeautifulSoup import BeautifulSoup
import json
import urlparse
import ssl
import re
import gzip
from StringIO import StringIO
import time

myloglevel = logging.INFO # change to DEBUG for more info; WARNING for less

def gk(mtype):
  key = ""
  filename = ""
  if (mtype == "api"): filename = ".gapikey"
  if (mtype == "cse"): filename = ".gcseid"

  try:
    f = open(filename)
    key = f.readline().strip()
    f.close()
  except (IOError):
    print "Unable to access key file!"
    exit()

  return key

useprox = 1

gAPIkey = gk("api") # Google API key
gcseID = gk("cse") # Google Custom Search Engine ID
gbaseurl = 'https://www.googleapis.com/customsearch/v1?key='+gAPIkey+'&cx='+gcseID+'&q=' # Base URL for Google CSE queries
grefer = 'https://ecfirst.com/ghdb' # Referer for GCSE (if applicable)
maxthreads = 4 # max number of simultanious connections to the GCSE

outbase = '/client/' # Base dir for output files
filetypes = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"] # file types to seach for

domain = "" # Set later in script

def gbro(url, g=1, rt=1): # Browser; takes an url and optional int (used w/ Google CSE); returns mechanize response object
  #tname = threading.currentThread().name
  tname = "filesearch"
  resp = ''
  try:
    if (useprox == 1):
      ctx = ssl.create_default_context()
      ctx.check_hostname = False
      ctx.verify_mode = ssl.CERT_NONE
      mproxy = urllib2.ProxyHandler({'https': '192.168.187.187:8888'})
      mopener = urllib2.build_opener(urllib2.HTTPSHandler(context=ctx), mproxy)
      urllib2.install_opener(mopener)
    #wbro = urllib2.Request(url)
    #if (g == 1): wbro.addheaders=[('User-Agent', 'Linux Firefox (ecfirst); GHDB'), ('Referer', grefer)]
    #else: wbro.addheaders=[('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0'), ('Accept-encoding', 'gzip')]
    if (g == 1): mheaders = { 'User-Agent': 'Linux Firefox (ecfirst); GHDB', 'Referer': grefer }
    else: mheaders = { 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0', 'Accept-encoding': 'gzip'}
    wbro = urllib2.Request(url, headers=mheaders)
    r = urllib2.urlopen(url=wbro, timeout=11.12)
    if r.info().get('Content-Encoding') == 'gzip':
      buf = StringIO(r.read())
      r2 = gzip.GzipFile(fileobj=buf)
      resp = r2.read()
    else:
      resp = r.read()
  except (urllib2.HTTPError) as err:
    if (err.code == 403):
      data = json.load(err)
      if (data['error']['errors'][0]['reason'] == "dailyLimitExceeded"):
        logging.critical("You've exceeded the daily limit of your CSE. Purchase more queries from Google or try back later")
        exit()
      else:
        logging.warning("Google error : "+ str(data['error']['errors'][0]['reason']))
        ans = raw_input("Press Enter to try again.")
        resp = gbro(url)
  except (urllib2.URLError, ssl.SSLError) as err:
    if ("unreachable" in str(err)):
      if (rt > 10):
        logging.warning(tname+"--> giving up...")
        resp = "BAD"
        return resp

      logging.warning(tname+"--> Unreachable Error: " + str(err) + " | Retrying...")
      rt += 1
      time.sleep(rt+1)
      if (g == 1): resp = gbro(url)
      else: resp = gbro(url, 0, rt)
    if ("timed out" in str(err)):
      if (rt > 10):
        logging.warning(tname+"--> giving up...")
        resp = "BAD"
        return resp

      logging.warning(tname+"--> Timeout Error: " + str(err) + " | Retrying...")
      rt += 1
      time.sleep(rt)
      if (g == 1): resp = gbro(url)
      else: resp = gbro(url, 0, rt)
    elif (re.search('HTTP Error 5\d\d', str(err))):
      if (rt > 10):
        logging.warning(tname+"--> giving up...")
        resp = "BAD"
        return resp

      logging.warning("[C]Server Error: "+ str(err.reason) + " | Retrying...")
      rt += 1
      time.sleep(rt)
      if (g == 1): resp = gbro(url)
      else: resp = gbro(url, 0, rt)
    else:
      logging.critical("uncaught error:"+ str(err))
      raise

  if resp == '':
    logging.critical("Hmmm, looks like we failed to get something back")
    logging.warning("Retrying once...")
    time.sleep(5)
    if (g == 1): resp = gbro(url, 1, 10)
    else: resp = gbro(url, 0, 10)
  return resp

def check_res(resp): # Checks to see if GCSE result contains search results; Returns True if search results
  data = json.loads(resp)
  if (int(data['searchInformation']['totalResults']) >= 1): return True

  return False



### End functions ###

domain = str(raw_input("Enter the domain to use\n(no validity checks performed so double check\nbefore you hit enter so that queries aren't wasted): "))

for ft in filetypes:
  query = "site:" + domain + "+filetype:" + ft
  url = gbaseurl+query
  resp = gbro(url)

  if check_res(resp):
    data = json.loads(resp)
    print data


