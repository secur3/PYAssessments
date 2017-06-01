#!/usr/bin/python

#Asks for domain names, company name, optional company nickname
#area codes, prefixes, and base numbers
#
#performs google CSE searchs to identify phone numbers belonging to company.

import urllib2
from urllib import quote_plus, unquote_plus, quote
from BeautifulSoup import BeautifulSoup
import json
import os
from subprocess import check_output
import time
from datetime import date
import random
import threading
import logging
import Queue
import urlparse
import ssl
import re
import gzip
from StringIO import StringIO

useprox = 0 # set to 1 to send traffic through proxy

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

gAPIkey = gk("api") # Google API key
gcseID = gk("cse") # Google Custom Search Engine ID

gbaseurl = 'https://www.googleapis.com/customsearch/v1?key='+gAPIkey+'&cx='+gcseID+'&q='

grefer = 'https://ecfirst.com/fonefind' # Referer for GCSE (if applicable)
maxthreads = 4 # max number of simultanious connections to the GCSE

outbase = '/client/' # Base dir for output files
outfile = outbase+"phones.txt"

domain = ""
company = ""
compnick = ""
areas = []
prefixes = []
basenums = []
scnt = 0
schk = -1

def getcompinfo():
  dom = ""
  comp = ""
  nick = ""
  while (len(dom) == 0):
    dom = raw_input("Enter the company domain name (i.e. ecfirst.com): ").rstrip("\n").lower()
    if ("." not in dom):
      print "\tDomain name required"
      dom = ""

  while (len(comp) == 0): comp = raw_input("Enter the company name (i.e. ecfirst): ").rstrip("\n")
  nick = raw_input("Enter a shortened company name if applicable (i.e. ecfirst)\n\tBe careful with names commonly found in words (i.e. MS, ING, etc.): ").rstrip("\n")
 
  return dom, comp, nick

def getnuminfo(areas=[], prefixes=[], basenums=[], scnt=0, schk=-1, retry=0):
  if (retry == 1):
    areas = []
    prefixes = []
    basenums = []
    scnt = 0
    schk = -1
  
  area = 0
  prefix = 0
  basenum = 0
  while (area == 0):
    area = raw_input("Enter the area code (i.e. 515): ").rstrip("\n")
    if (not area.isdigit()):
      print "\tArea codes consist of 3 numbers"
      area = 0
    elif (len(area) != 3):
      print "\tArea codes consist of 3 numbers"
      area = 0
    elif ((int(area) <= 0) or (int(area) >= 1000)):
      print "\tArea codes are 3 numbers between 000 and 999"
      area = 0
  areas.append(area)
  
  while (prefix == 0):
    prefix = raw_input("Enter the prefix (i.e 555): ").rstrip("\n")
    if (not prefix.isdigit()):
      print "\tPrefixes consist of 3 numbers"
      prefix = 0
    elif (len(prefix) != 3):
      print "\tPrefixes consist of 3 numbers"
      prefix = 0
    elif ((int(prefix) <=0) or (int(prefix) >=1000)):
      print "\tPrefixes are 3 numbers between 000 and 999"
      prefix = 0
  prefixes.append(prefix)
  
  while (basenum == 0):
    basenum = raw_input("Enter the base number, using 'X' for the numbers to replace (i.e. 12XX): ").rstrip("\n")
    if ("X" not in basenum):
      print "\tWe need at least 1 substitution"
      basenum = 0
    elif (len(basenum) != 4):
      print "\tThe base number must be 4 characters"
      basenum = 0
    elif (basenum.find("X") == 0): scnt = 4
    elif (basenum.find("X") == 1):
      if (not basenum[0].isdigit()):
        print "\tCharacters preceeding 'X' must be numbers"
        basenum = 0
      else: scnt = 3
    elif (basenum.find("X") == 2):
      if (not basenum[:2].isdigit()):
        print "\tCharacters preceeding 'X' must be numbers"
        basenum = 0
      else: scnt = 2
    elif (basenum.find("X") == 3):
      if (not basenum[:3].isdigit()):
        print "\tCharacters preceeding 'X' must be numbers"
        basenum = 0
      else: scnt = 1

  if (schk == -1): schk = scnt
  elif (schk != scnt):
    print "Masks do not match. The same number of 'X' placeholders must be in both base numbers.\nTry again"
    getnuminfo(retry=1)

  if (basenum != 0): basenums.append(basenum)

  goagain = raw_input("Enter more numbers? (y,N): ").rstrip("\n").lower()
  if ('y' in goagain): getnuminfo(areas, prefixes, basenums, scnt, schk)

  return areas, prefixes, basenums, scnt

def numbuilder(area, pre, base):
  numvars = ""
  numvars += '"'+area+'-'+pre+'-'+base+'" OR '
  numvars += '"('+area+') '+pre+'-'+base+'" OR '
  numvars += '"('+area+')'+pre+'-'+base+'" OR '
  numvars += '"'+area+'.'+pre+'.'+base+'" OR '
  numvars += '"'+area+pre+base+'"'
  
  return numvars

def checklinksdom(resp, num):
  data = json.loads(resp)
  if (int(data['searchInformation']['totalResults']) >= 1):
    print "\t Match for '"+num+"'!"
    winner(num, "confirmed")
    return True

  return False

def checklinks(resp, num, comp, nick):
  data = json.loads(resp)
  if (int(data['searchInformation']['totalResults']) == 0): return False
  for link in data.get("items"):
    if ((comp in link['title']) or (comp in link['snippet'])):
      print "\tPotential match for '"+num+"'!"
      winner(num, "potential-Company")
      return True
    if (len(nick) > 2):
      if ((nick in link['title']) or (nick in link['snippet'])):
        print "\tPotential match for '"+num+"'!"
        winner(num, "potential-Nickname")
        return True
 
  return False

def winner(num, status):
  try:
    file = open(outfile, 'a')
    file.write(num+"\t"+status+"\n")
    file.close()
  except (IOError) as err:
    print "Error writing to '"+outfile+"' : "+err.strerror
    exit()
  
  return

def gbro(url, g=1, rt=1): # Browser; takes an url and optional int (used w/ Google CSE); returns mechanize response object
  tname = threading.currentThread().name
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

#end functions

if (os.path.isfile(outfile)):
  ans = raw_input("Output file already exists; overwrite it? (Y,n): ")
  if not ("n" in ans.lower()):
    print "'"+outfile+"' deleted"
    print ""
    os.remove(outfile)

domain, company, compnick = getcompinfo()
areas, prefixes, basenums, scnt = getnuminfo()

therange = ''
if (scnt == 4): therange = range(10000)
elif (scnt == 3): therange = range(1000)
elif (scnt == 2): therange = range(100)
else: therange = range(10)

for num in therange:
  if (num < 1000):
    if (num < 100):
      if (num < 10):
        if (scnt > 1):
          num = "0"+str(num)
      if (scnt >= 3):
        num = "0"+str(num)
    if (scnt == 4):
      num = "0"+str(num)

  num = str(num)
  numdex = 0
  for area in areas:
    if (scnt == 4):
      realnum = area+"-"+prefixes[numdex]+"-"+num
      print "Trying '"+realnum+"'..."
      testnums = numbuilder(area, prefixes[numdex], num)
    else:
      realnum = area+"-"+prefixes[numdex]+"-"+basenums[numdex][:4-scnt]+num
      print "Trying '"+realnum+"'..."
      testnums = numbuilder(area, prefixes[numdex], basenums[numdex][:4-scnt]+num)

    cleannum = quote(testnums)
    domurl = gbaseurl+quote('site:'+domain+' '+testnums)
    url = gbaseurl+cleannum

    resp = gbro(domurl)
    if (checklinksdom(resp, realnum)):
      numdex += 1
      continue

    resp = gbro(url)
    checklinks(resp, realnum, company, compnick)

    numdex += 1

print "Done!\nResults written to '"+outfile+"'"
