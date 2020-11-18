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
import ssl
from http import cookiejar
import subprocess
import re

from ecuseragent import * #assigns the useragent variable

parser = argparse.ArgumentParser()
parser.add_argument("savepath", help="The base path to create folder structure (e.g '/client/crypt/ACME/')")
parser.add_argument("domain", help="The client domain you were querying (e.g. ecfirst.com)")
parser.add_argument("-u", "--url", help="The Google search URL")
parser.add_argument("--links", help="Save the website links instead of the actual files (to be used with FOCA or when FOCA has download issues)", action="store_true")
parser.add_argument("-f", "--file", help="File to use instead of URL(s) from browser (e.g. /client/file.txt)")
parser.add_argument("--debug", help="Enable DEBUG output", action="store_true")
args = parser.parse_args()

if args.debug:
  LOGLEVEL = logging.DEBUG
else:
  LOGLEVEL = logging.INFO

if args.file and args.url:
  parser.error("You can't use --file and --url together")

logging.basicConfig(format='%(levelname)s:%(message)s', level=LOGLEVEL)

savepath=args.savepath
mydom=args.domain
linksfile="/{}{}.txt".format(savepath, mydom)
mylinks = []

startcookie = "/home/kali/Downloads/cookies.txt"
cj = cookiejar.MozillaCookieJar()
cookiefile = "/client/cookies.txt"

if Path(startcookie).is_file():
  if not Path(cookiefile).is_file():
    cookies = True
    subprocess.call(["sed", "-i", 's/^\.google\.com\tfalse/.google.com\tTRUE/g', startcookie])
    subprocess.call(["sed", "-i", 's/^www\.google\.com\ttrue/www.google.com\tFALSE/g', startcookie])
    shutil.copyfile(startcookie, cookiefile)
    subprocess.call(["sed", "-i", '1s/^/# Netscape HTTP Cookie File\\n/', cookiefile])

  cj.load(cookiefile)
else:
  cookies = False
  logging.info("Not using cookies")
#useragent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36' #update as needed

def argcheck (path, dom, aurl="http://notneeded"): #basic check that the args passed in are what we need
  if not os.path.isdir(path):
    logging.critical("")
    logging.critical("The supplied path ('{}') does not exist or is not a directory".format(path))
    exit()
  if not aurl.startswith("http"):
    print ("")
    logging.critical("The supplied Google URL ('{}') does not look like a web URL (not starting with 'http' or 'https')".format(aurl))
    exit()
  if not ("google.com/search" in aurl or "notneeded" in aurl) :
    logging.critical("")
    logging.critical("The supplied Google URL ('{}') does not look like a Google Search URL".format(aurl))
    exit()

def bro (aurl, savepath="", links=False): #takes a URL and returns a BeautifulSoup object of the response or saves the file if savepath is provided
  ctx = ssl.create_default_context()
  ctx.check_hostname = False
  ctx.verify_mode = ssl.CERT_NONE

  if args.debug: opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx), urllib.request.ProxyHandler({"https":"https://192.168.187.187:8888/"}))
  else: opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
  opener.addheaders = [('User-agent', useragent)]
  urllib.request.install_opener(opener)
  req = urllib.request.Request(aurl.strip())

  if not savepath and not links:
    try:
      with urllib.request.urlopen(req) as resp:
        response = BeautifulSoup(resp.read(), 'html.parser')
    except HTTPError as err:
        logging.critical("Error accessing Google: {}".format(err.reason))
        exit()
  elif not links:
    tfilename, tpath, mdom = getFilename (aurl)
    newpath = mdom + "/" + tpath
    if not savepath.endswith('/'): savepath = savepath +"/"
    newsavepath = savepath + newpath
    if not newsavepath.endswith('/'): newsavepath = newsavepath + "/"
    #outfile = newsavepath + filename
    Path(newsavepath).mkdir(parents=True, exist_ok=True)
    logging.debug("Creating '{}' if doesnt exist".format(newsavepath))
    #logging.info("Downloading '{}' :: from '{}'".format(filename, aurl.stip()))
    try:
      with urllib.request.urlopen(req) as resp:
        try:
          myheads = resp.headers['content-disposition']
          tfilename = re.findall("filename=(.+)", myheads)[0]
          filename = tfilename[1:-1]
          logging.info("Downloading '{}' :: from '{}'".format(filename, str(aurl).strip()))
          outfile = newsavepath + filename
          with open(outfile, 'wb') as out_file:
            shutil.copyfileobj(resp, out_file)
            logging.debug("Saved '{}'".format(filename))
            response = True
        except:
          response = False
    except HTTPError as err:
      if err.code == 404: logging.warning("\tUnable to download '{}', got 404 Not Found".format(aurl))
      else: logging.warning("\tError accessing client site for '{}' :: {}".format(aurl, err.reason))
      response = True
  else:
    try:
      if Path(linksfile).exists():
        logging.info("Saving link '{}'".format(aurl))
        with open(linksfile, "a") as outfile:
          outfile.write(aurl+"\n")
      else:
        logging.info("Saving First link '{}'".format(aurl))
        with open(linksfile, "w") as outfile:
          outfile.write(aurl+"\n")
      response = True
    except:
      response = False

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
  logging.debug("OPath: {}".format(parsed.path))
  if not os.path.basename(parsed.path):
    parsed = urlparse(path.strip("/"))
  filename = os.path.basename(parsed.path).strip()
  logging.debug("Filename: {}".format(filename))
  newpath = os.path.dirname(parsed.path)
  logging.debug("Path: {}".format(newpath))
  domain = parsed.netloc
  return filename, newpath, domain

### end functions ###
if __name__ == "__main__":
  docfile = ''
  if args.file:
    docfile = args.file #use the URL(s) in file instead of Google search URL
  elif args.url:
    URL = args.url #use the URL passed via command line, if there
  else:
    URL = input("Enter the Google search URL: ")
  if args.links:
    links = True
  else:
    links = False

  if docfile:
    argcheck(savepath, mydom)
  else:
    argcheck(savepath, mydom, URL) #check the passed args are what we need

  if docfile:
    logging.info("Getting links from '{}'...".format(docfile))
    with open(docfile) as fp:
      for link in fp:
        logging.debug("Using '{}'".format(link.strip()))
        resp = bro(link.strip(), savepath) #resp is True if no error saving
        if not resp:
          logging.warning("! Unable to download/save '{}' !".format(link.strip()))
  else:
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

    if links: logging.info("Saving links for '{}'".format(mydom))
    else: logging.info("Downloading files for '{}'...".format(mydom))

    for link in mylinks: #step through the links and download the file
      if links: resp = bro(link, False, True)
      else: resp = bro(link, savepath) #resp is True if no error saving
      if not resp:
        logging.warning("! Unable to download/save '{}' !".format(link))

  print("")
  logging.info("Done")
