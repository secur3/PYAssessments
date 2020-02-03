#!/usr/bin/python
# provided a local save path, a target domain name and a Google search URL
# grabs the links for the target domain from the search results
# downloads those files and saves them in the same folder structure as the URL
#bmiller 01.2020

import urllib.request
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
from pathlib import Path
import os
import shutil
import argparse
import logging

from ecuseragent import * #assigns the useragent variable

parser = argparse.ArgumentParser()
parser.add_argument("savepath", help="The base path to create folder structure (e.g '/client/crypt/ACME/')")
parser.add_argument("domain", help="The client domain you were querying (e.g. ecfirst.com)")
parser.add_argument("-u", "--url", help="The Google search URL")
parser.add_argument("--debug", help="Enable DEBUG output", action="store_true")
args = parser.parse_args()

if args.debug:
  LOGLEVEL = logging.DEBUG
else:
  LOGLEVEL = logging.INFO

logging.basicConfig(format='%(levelname)s:%(message)s', level=LOGLEVEL)

savepath=args.savepath
mydom=args.domain
mylinks = []

#useragent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36' #update as needed

def argcheck (path, dom, aurl): #basic check that the args passed in are what we need
  if not os.path.isdir(path):
    logging.critical("")
    logging.critical("The supplied path ('{}') does not exist or is not a directory".format(path))
    exit()
  if not aurl.startswith("http"):
    print ("")
    logging.critical("The supplied Google URL ('{}') does not look like a web URL (not starting with 'http' or 'https')".format(aurl))
    exit()
  if not "google.com/search" in aurl:
    logging.critical("")
    logging.critical("The supplied Google URL ('{}') does not look like a Google Search URL".format(aurl))
    exit()

def bro (aurl, savepath=""): #takes a URL and returns a BeautifulSoup object of the response or saves the file if savepath is provided 
  req = urllib.request.Request(aurl, data=None, headers={'User-Agent': useragent})

  if not savepath:
    try:
      with urllib.request.urlopen(req) as resp:
        response = BeautifulSoup(resp.read(), 'html.parser')
    except HTTPError as err:
        logging.critical("Error accessing Google: {}".format(err.reason))
        exit()
  else:
    filename, tpath, mdom = getFilename (aurl)
    newpath = mdom + "/" + tpath
    if not savepath.endswith('/'): savepath = savepath +"/"
    newsavepath = savepath + newpath
    if not newsavepath.endswith('/'): newsavepath = newsavepath + "/"
    outfile = newsavepath + filename
    Path(newsavepath).mkdir(parents=True, exist_ok=True)
    logging.debug("Creating '{}' if doesnt exist".format(newsavepath))
    logging.info("Downloading '{}' :: from '{}'".format(filename, aurl))
    try:
      with urllib.request.urlopen(req) as resp, open(outfile, 'wb') as out_file:
        try:
          shutil.copyfileobj(resp, out_file)
          logging.debug("Saved '{}'".format(filename))
          response = True
        except:
          response = False
    except HTTPError as err:
      if err.code == 404: logging.warning("\tUnable to download '{}', got 404 Not Found".format(aurl))
      else: logging.warning("\tError accessing client site for '{}' :: {}".format(aurl, err.reason))
      response = True

  return response

def gscrape (resp, dom): #takes a BeautifulSoup object & domain and pulls out the links to the domain
  thelinks = []
  for divs in resp.find_all('div'):
    for links in divs.find_all('a'):
      if links.get('href'):
        link = links.get('href')
        logging.debug("FOUND: '{}'".format(link))
        if "webcache" in link: continue
        if "search?" in link and "q=" in link: continue
        if "google.com" in link: continue
        if dom in link:
          if not link in thelinks: thelinks.append(link)

  return thelinks

def getFilename (path): #takes the URL path and returns the filename and save path
  parsed = urlparse(path)
  filename = os.path.basename(parsed.path)
  newpath = os.path.dirname(parsed.path)
  domain = parsed.netloc
  return filename, newpath, domain

### end functions ###

if args.url:
  URL = args.url #use the URL passed via command line, if there
else:
  URL = input("Enter the Google search URL: ") 

argcheck(savepath, mydom, URL) #check the passed args are what we need

logging.info("Getting Google search page...")
logging.debug("Using '{}'".format(URL))

gres = bro(URL) #get the Google search page URL passed in

mylinks = gscrape(gres, mydom) #get the links to the client domain passed in

if not mylinks:
  logging.critical("")
  logging.critical("No links found! Maybe Google blocked access or there were no links on the page for '{}'".format(mydom))
  logging.critical("\tYou could try the link in a browser to confirm, and try again shortly")
  logging.info("You could enable --debug to see the links returned")
  exit()

logging.info("Downloading files for '{}'...".format(mydom))

for link in mylinks: #step through the links and download the file
  resp = bro(link, savepath) #resp is True if no error saving
  if not resp:
    logging.warning("! Unable to download/save '{}' !".format(link))

print("")
logging.info("Done")
