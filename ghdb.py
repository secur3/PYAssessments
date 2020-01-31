#!/usr/bin/env python

# Checks if the GHDB dorks have been recently downloaded (from www.exploit-db.com); downloads if not
# Creates GHDB queries based on provided domain (optional)
# Tries all, 10% or other percentage, whichever is chosen (optional)
#
#b.miller

from __future__ import division
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import input
from builtins import str
from builtins import range
from past.utils import old_div
import urllib.request, urllib.error, urllib.parse
from urllib.parse import quote_plus, unquote_plus
from bs4 import BeautifulSoup
import json
import os
from subprocess import check_output
import time
from datetime import date
import random
import threading
import logging
import queue
import urllib.parse
import ssl
import re
import gzip
from io import StringIO, BytesIO
import argparse
import math

parser = argparse.ArgumentParser()
parser.add_argument("--test", help="Only test 11 items per subcategory", action="store_true")
parser.add_argument("--debug", help="Turn on debugging", action="store_true")
parser.add_argument("--proxy", help="Use to provide a proxy to connect through (e.g. --proxy '192.168.187.187:8888')")
parser.add_argument("--threads", help="Use to change the default threads from 4", type=int)
args = parser.parse_args()

if args.test: TEST = True
else: TEST = False # set to True to limit tries to 11 per subcategory; this should result in 99 queries at most

if args.proxy: useprox = args.proxy
else: useprox = False # set to a proxy value to send traffic through proxy

if args.debug: myloglevel = logging.DEBUG
else: myloglevel = logging.INFO # change to DEBUG for more info; WARNING for less

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
    print("Unable to access key file!")
    exit()

  return key

gAPIkey = gk("api") # Google API key
gcseID = gk("cse") # Google Custom Search Engine ID
gbaseurl = 'https://www.googleapis.com/customsearch/v1?key='+gAPIkey+'&cx='+gcseID+'&q=' # Base URL for Google CSE queries
grefer = 'https://ecfirst.com/ghdb' # Referer for GCSE (if applicable)
useragent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36'

if args.threads: maxthreads = args.threads+1
else: maxthreads = 5 # max number of simultanious connections to the GCSE

outbase = '/client/' # Base dir for output files
htmloutfile = '-ghdbqueries.html' # HTML file suffix for domain specific generated queries
resoutfile = '-ghdbresults.csv' # Output file suffix for domain specific test results

domain = "" # Set later in script
sleepsec = 1 # used for delays
cats = {} # Globally used
mycats = ["Footholds", "Vulnerable Files", "Vulnerable Servers", "Files containing passwords", "Files containing usernames", "Files containing juicy info", "Network or vulnerability data", "Advisories and Vulnerabilities", "Pages containing login portals", "Error Messages", "Various Online Devices"] # categories that we will try queries from when applicable

myq = queue.Queue()
logging.basicConfig(level=myloglevel, format='[%(levelname)s] %(message)s')

def gbro(url, g=1, rt=1): # Browser; takes an url and optional int (used w/ Google CSE); returns mechanize response object  
  tname = threading.currentThread().name
  resp = ''
  try:
    if (useprox):
      ctx = ssl.create_default_context()
      ctx.check_hostname = False
      ctx.verify_mode = ssl.CERT_NONE
      mproxy = urllib.request.ProxyHandler({'https': useprox})
      mopener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), mproxy)
      urllib.request.install_opener(mopener)
    #wbro = urllib2.Request(url)
    #if (g == 1): wbro.addheaders=[('User-Agent', 'Linux Firefox (ecfirst); GHDB'), ('Referer', grefer)]
    #else: wbro.addheaders=[('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0'), ('Accept-encoding', 'gzip')]
    if (g == 1): mheaders = { 'User-Agent': useragent, 'Referer': grefer }
    else: mheaders = {'User-Agent': useragent, 'Referer': url, 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
    wbro = urllib.request.Request(url, headers=mheaders)
    r = urllib.request.urlopen(url=wbro, timeout=11.12)
    if r.info().get('Content-Encoding') == 'gzip':
      buf = BytesIO(r.read())
      r2 = gzip.GzipFile(fileobj=buf)
      resp = r2.read()
    else:
      resp = r.read()
  except (urllib.error.HTTPError) as err:
    if (err.code == 403):
      data = json.load(err)
      if (data['error']['errors'][0]['reason'] == "dailyLimitExceeded"):
        logging.critical("You've exceeded the daily limit of your CSE. Purchase more queries from Google or try back later")
        exit()
      else:
        logging.warning("Google error : "+ str(data['error']['errors'][0]['reason']))
        ans = input("Press Enter to try again.")
        resp = gbro(url)
  except (urllib.error.URLError, ssl.SSLError) as err:
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

def get_cats(): # Returns a Dict of GHDB Category names and IDs
  global cats
  logging.info("Getting categories...")
  baseurl = 'https://www.exploit-db.com/google-hacking-database/'

  resp = gbro(baseurl, 1)
  resp = BeautifulSoup(resp, 'html.parser')

  catselect = resp.find(id="categorySelect")
  for option in catselect.select('option'):
    if option.text:
      catid = option['value']
      text = option.text
      text = text.strip(' \n')
      cats[text] = catid

  logging.debug("cat len: "+str(len(cats)))
  return True

def get_dorks(resp, count=0): # receives a json response for page with dorks; returns a List of dork urls 
  tname = threading.currentThread().name
  dorks = []
  base = 'https://www.exploit-db.com/ghdb/'

  for link in resp['data']:
    id = link['id']
    if id:
      title = link['url_title'].strip('</a>')
      if args.debug: logging.debug("{}:{}--> Found dork: {}".format(count, tname, title))
      else: logging.info("{}:{}--> Found dork".format(count, tname))
      skip = 0
      url = base + id
      while True:
        try:
          resp1 = gbro(url, 0)
          if (resp1 == "BAD"):
            logging.warning(tname+"--> Unable to get dork at: {}".format(url))
            skip = 1
            break

          resp2 = BeautifulSoup(resp1, 'html.parser')
        except Exception as err:
          logging.warning('Dorks Error: ' + str(err))
          if ("timed out" in str(err)): continue
          else:
            logging.critical(str(err))
            skip=1
        break

      if (skip == 1): continue
      dork = resp2.find("h1", {"class": "card-title"})
      if dork:
        dork = dork.text.strip(' \n')
        if dork:
          logging.debug(dork)
          dorks.append(dork)
        else: logging.debug('! Bad Dork Page !')
      else: logging.debug('! Bad Dork Page !')
      count += 1
      time.sleep(sleepsec) # added in a delay between dorks as exploit-db began blocking our IP during test runs; plus its the nice thing to do

  return dorks, count

def startchk(): # Start-up routine; creates required dir; checks for last run time; gathers domain name
  if not (os.path.isdir('./ghdb')):
    try:
      os.mkdir('./ghdb')
    except IOError as err:
      logging.critical('Unable to create GHDB directory : ' + err.strerror)
      exit()

  os.chdir('./ghdb')

  if not (os.path.isfile('time.time')):
    logging.info("Looks like this is the first run, downloading dorks...")
    get_ghdb()

  else:
    try:
      file = open('time.time', 'r')
      for lines in file.readlines():
        btime = float(lines)
      file.close()
    except (IOError, ValueError) as err:
      logging.critical('Unable to read time.time : ' + err.strerror)
      exit()

    ctime = time.time()

    if ((ctime - btime) <= 15552000):
      ans = input("\nLooks like the dorks were collected less than 6 months ago. Do you want to redownload them? [y,N] ")
      if ('y' in ans.lower()): get_ghdb()

    else:
      ans = input("\nLooks like the dorks haven't been collected for over 6 months. Do you want to redownload them? [Y,n]")
      if not ('n' in ans.lower()): get_ghdb()

  domain = str(input("Enter the domain to use\n(no validity checks performed so double check\nbefore you hit enter so that queries aren't wasted): "))
  os.chdir('..')

  return domain

def get_ghdb(): # Gets the GHDB; pulls Categories and urls; pulls dorks and urls; creates files in ./ghdb/ for each Cat w/ all dorks
  global cats
  if (os.path.isfile('time.time')):
    try:
      os.remove('time.time')
    except OSError as err:
      logging.critical('Unable to delete time.time; try deleting manually : ' + err.strerror)
      exit()

  stime = time.time()
  logging.info('Start Time: ' + time.ctime(stime))

  get_cats()

  for cat, meow in cats.items():
    ct = threading.Thread(name=str(cat), target=main_cat, args=(cat, meow))
    ct.daemon=True
    ct.start()
    time.sleep(sleepsec)
    while int(threading.activeCount()) >= maxthreads: pass

  while int(threading.activeCount()) > 1: pass

  etime = time.time()
  logging.info('Start Time: '+ time.ctime(stime))
  logging.info('End Time: '+ time.ctime(etime))

  try:
    file = open('time.time', 'w')
    file.write(str(etime))
    file.close()

  except IOError as err:
    logging.warning('Unable to write time.time : '+ err.strerror)

  return True

def main_cat(cat, meow):
    global cats

    logging.info('Pulling dorks for ' + str(cat) + '...')
    if (os.path.isfile(cat+'.base')):
      try:
        os.remove(cat+'.base')
      except OSError as err:
        logging.critical('Unable to remove '+cat+'.base; try deleting manually : ' + err.strerror)
        exit()

    dorks = []
    start = 0
    pagecount = 0
    totalpages = 1
    count = 0

    while pagecount <= totalpages:
      caturl = "https://www.exploit-db.com/google-hacking-database?category={}&start={}&length=120".format(meow, start)
      page = gbro(caturl, 0)
      resp = BeautifulSoup(page, 'html.parser') #
      data = json.loads(resp.text.replace('in the "Vulnerable Files" section.', "in the 'Vulnerable Files' section."))
      totaldorks = data['recordsTotal']
      totalpages = math.ceil(totaldorks/120)

      thedorks, count = get_dorks(data, count) #
      for dork in thedorks:
        dorks.append(dork)

      if pagecount <= totalpages:
        pagecount +=1
        start += 121

    try:
      file = open(cat+'.base', 'w')
      logging.info('Writing '+str(len(dorks))+' dorks to '+cat+'.base...')
      for dork in dorks:
        file.write(dork+"\n")
      file.close()
    except IOError as err:
      logging.critical('Unable to write to '+cat+'.base : ' + err.strerror)
      exit()

    logging.info(cat+" COMPLETED")
    return True

def gen_ghdb(dom): # Creates an HTML file containing every GHDB dork customized for the provided domain
  global cats
  reggoog = "http://www.google.com/search?q="
  savepath = outbase+dom+htmloutfile
  try:
    file = open(savepath, 'w')
    file.write("<html>\n<head>\n<title>GHDB queries for "+dom+"</title>\n</head>\n")
    file.write("<style type='text/css'>\nH1 { font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 1.6em; font-weight: bold; line-height: 1.0em; }\n.cat { font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 1.2em; font-weight: bold; line-height: 1.0em; }\nH3 { font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 0.8em; font-weight: bold; line-height: 1.0em; }\n.nav { font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 0.6em; font-weight: bold; line-height: 1.0em; }\n</style>\n")
    file.write("<body>\n")
    file.write("<H1>"+dom+" GHDB queries</H1><H3>Generated By: <a href='http://www.ecfirst.com'>ecfirst</a></H3><br>\n")
    file.write("<H1 id='0'>Categories</H1>\n")

    if (cats == {}): get_cats()
    catcnt = 1
    logging.debug("cat len: "+str(len(cats)))
    for cat, meow in cats.items():
      logging.debug(""+cat+" : "+meow)
      file.write("<p><a href='#"+str(catcnt)+"'>"+str(catcnt)+".\t"+cat+"</a></p>\n")
      catcnt += 1

    file.write("<br><br>\n")

    logging.info("Generating file '"+savepath+"'")

    catcnt = 1
    for cat, meow in cats.items():
      if not (os.path.isfile("./ghdb/"+cat+".base")):
        logging.critical("Can't find './ghdb/"+cat+".base'! You may need to re-run or check your run location")
        exit()
      file.write("<span class='cat' id='"+str(catcnt)+"'>"+cat+"</span>&nbsp&nbsp<a class='nav' href='#0'>Top</a><br>\n<ul>\n")
      catfile = open("./ghdb/"+cat+".base", 'r')
      for line in catfile.readlines():
        dork = line.rstrip("\n")
        newdork = "site:"+dom+" "+dork
        edork = quote_plus(newdork)
        file.write("\t<li><a href='"+reggoog+edork+"'>"+newdork+"</a></li>\n")

      catfile.close()
      file.write("</ul>\n<br><br>\n")
      catcnt += 1

    copyyear = date.today().year
    file.write("<p>Generated by <a href='http://www.ecfirst.com'>ecfirst</a> "+str(copyyear)+"</p>\n")
    file.write("</body>\n</html>")
    file.close()

  except IOError as err:
    logging.critical("Error accessing category files or creating HTML file : "+ err.strerror)
    exit()

  logging.info("\tHTML file '"+savepath+" created")

  return True

def try_ghdb(dom): # Gets the percentage of queries to try; tests against GCSE
  global cats
  global mycats
  global TEST
  savepath = outbase+dom+resoutfile
  
  if not (os.path.isdir("./ghdb/")):
    logging.critical("Can't find the 'ghdb' directory. You may need to re-run or check your run location")
    exit()

  trycent, depth = try_cents()
  if (depth or TEST): thecats = mycats
  else:
    if (cats == {}): get_cats()
    thecats = list(cats.keys())

  try:
    file = open(savepath, 'w')
    file.write("Query\tStatus\n")
    file.close()
  except IOError as err:
    logging.critical("Can't write to '"+savepath+"' : "+ err.strerror)
    exit()

  if (TEST):
    logging.debug("Defaulting to 11 tries per category max, as TEST was set to True")
    newdork = "site:"+dom
    myurl = gbaseurl+quote_plus(newdork)

    res = check_dork(gbro(myurl))
    if (res):
      logging.debug("! Hit for '"+newdork+"' !")
    else:
      logging.critical("! MISS for '"+newdork+"'?!?!")
      exit()

  stime = time.ctime(time.time())
  logging.info("Start Time: "+stime)

  mytevent = threading.Event()
  myqt = threading.Thread(name="queue", target=qwatch, args=(savepath,mytevent))
  myqt.start()

  for cat in thecats:
    if not (os.path.isfile("./ghdb/"+cat+".base")):
      logging.critical("Can't find the file './ghdb/"+cat+".base'. You may need to re-run or check your run location")
      exit()
    dorklist = open("./ghdb/"+cat+".base").readlines()
    numlinks = len(dorklist)
    trytimes = int(numlinks * trycent)
    if ((trytimes < 11) or TEST): trytimes = 11
    if (trytimes > numlinks): trytimes = numlinks
    randlist = list(range(0, numlinks))
    random.shuffle(randlist)

    logging.info("Trying "+str(trytimes)+" queries from '"+cat+"'...")
    
    trycount = 1
    while trycount <= trytimes:
      logging.debug("#"+str(trycount)+" of "+str(trytimes))
      rpop = randlist.pop()
      logging.debug("random: "+str(rpop))
      dork = dorklist[rpop].rstrip("\n")
      newdork = "site:"+dom+" "+dork
      myurl = gbaseurl+quote_plus(newdork)

      t = threading.Thread(name="trying", target=try_each, args=(myurl, newdork))
      t.daemon-True
      t.start()

      trycount += 1

      while int(threading.activeCount()) >= maxthreads+2: pass

  while int(threading.activeCount()) > 2:
    logging.debug("Waiting on "+str(int(threading.activeCount())-2)+" threads to complete...")
    time.sleep(2)
  mytevent.set()
  while not myq.empty():
    logging.debug("Waiting on queue to empty")
    time.sleep(2)

  logging.info("Results written to '"+savepath+"'")
  logging.info("Start Time: "+stime)
  etime = time.ctime(time.time())
  logging.info("End Time: "+etime)

  return True

def try_each(myurl, newdork):
  status = ""
  res = check_dork(gbro(myurl))
  if (res):
    logging.info("! Hit for '"+newdork+"' !")
    status = "Hit"
  else: status = "Miss"

  myq.put(newdork+"\t"+status)

  return

def qwatch(savepath, myevent):
  while not myevent.isSet():
    if not myq.empty():
      try:
        file = open(savepath, 'a')
        while not myq.empty():
          logging.debug("writing items from queue")
          file.write(myq.get()+"\n")
        file.close()
      except IOError as err:
        logging.critical("Can't write to '"+savepath+"' : "+ err.strerror)
        exit()

  return

def try_check(): # Gets the percentage; moved here to allow an easy redo
  ans = 0
  while ans == 0:
    ans = input("Enter the percentage of total tries to test as an integer(i.e. 23): ")
    try:
      ans = int(ans)
    except ValueError:
      ans = 0
    if (ans >= 100):
      qans = input("Are you sure you want to try EVERY query? This could result in over 3300 queries against your Google CSE (y, N): ")
      if not ("y" in qans.lower()): ans = 0
  
  return ans

def try_cents(): #Determines the percent of tries for testing queries; returns percentage, True or False for subset
  mycent = 1.11
  ans = 0
  limitq = True # Do we use the subset of cats

  while ans == 0:
    ans = try_check()
    if (ans < 1): ans = 1
    if (ans > 100): ans = 100

    logging.info("Using '"+str(ans)+"' as the percentage")
    totalt = count_queries(ans)
    logging.warning("This will result in @ "+str(totalt)+" queries against your Google CSE.")
    kans = input("Keep the percentage as "+str(ans)+"%? (Y, n)")
    if ('n' in kans.lower()): ans = 0

  mycent = old_div((ans+.00),100)

  if (ans == 100):
    sans = input("Do you want to test queries from all categories (3300+ queries)? (y, N): ")
    if ('y' in sans.lower()): limitq = False # Use all cats

  return mycent, limitq

def count_queries(cent): # Counts the number of queries based on percentage
  global mycats
  cent = old_div((cent+.00),100)
  tots = 0

  for names in mycats:
    thepath = "./ghdb/"+names+".base"
    fsz = (check_output(['wc', '-l', thepath])).decode()
    fsz = int(fsz.split(" ")[0])
    fsz = int(fsz * cent)
    if (fsz  < 10): fsz = 10
    tots += fsz

  return tots

def check_dork(resp): # Checks to see if GCSE result contains search results; Returns True if search results
  data = json.loads(resp)
  if (int(data['searchInformation']['totalResults']) >= 1): return True

  return False

### End functions ###

if __name__ == "__main__":

  domain = startchk()

  if (domain == ""):
    print("Done!")
    exit()

  ansint = 0

  while (ansint == 0):
    ans = ""
    print("")
    print("Enter your choice:")
    print("1: Generate queries only")
    print("2: Test queries only")
    print("3: Generate and test queries")
    ans = input("Choice: ")
    try:
      ans = int(ans)
      ansint = 1
    except ValueError:
      pass

  if (ans < 1 or ans > 3):
    print("Done!")
    exit()

  if (ans == 1): gen_ghdb(domain)
  elif (ans == 2): try_ghdb(domain)
  else:
    gen_ghdb(domain)
    try_ghdb(domain)

  print("")
  print("Done!")
