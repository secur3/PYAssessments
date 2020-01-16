#!/usr/bin/env python

# Brute force hostnames for a domain
# set 'domain' to the client domain name
# set 'base' to the IP address the 'domain' resolves to
#       this help to catch wildcard entries
# set 'maxt' to the number of concurrent threads
# requires "Recong-ng" installed in the default Kali location (we utilize it's hostname list)

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
import socket
import threading
import logging
import time
import queue
from sys import exit
import sys

myloglevel = logging.INFO
myq = queue.Queue()

if len(sys.argv) != 3:
  print("Usage: dnser.py <domain> <base>")
  exit()

domain = sys.argv[1]
base = sys.argv[2]
maxt = 4
outfile = "/client/"+domain+"-dnsresults.csv"

logging.basicConfig(level=myloglevel, format='[%(levelname)s] %(message)s')

def getaddr(name):
    try:
       res = socket.gethostbyname(name)
       if (str(res) != base):
           logging.info(name+" => "+str(res))
           myq.put(name+","+str(res))
    except Exception as err:
        logging.debug(name+" : "+str(err))
        if (err.errno == -3):
            logging.warning("Retrying '"+name)
            time.sleep(2)
            getaddr(name)

def checkdns(alist):
    progcount = 0
    for name in alist.readlines():
        nhost = str(name.rstrip())+"."
        hname = nhost + domain
        logging.debug("Checking "+ hname)
        t = threading.Thread(name=nhost, target=getaddr, args=(hname,))
        t.daemon=True
        t.start()
        progcount += 1
        if progcount == 20:
          logging.info("PROGRESS: "+hname)
          progcount = 0
        while int(threading.activeCount()) >= maxt+1: pass


lista = open('/usr/share/recon-ng/data/hostnames.txt')
listb = open('/client/scratch/hostnames.txt')

checkdns(lista)
checkdns(listb)

while int(threading.activeCount()) > 1: pass

try:
  f = open(outfile, 'w')
  f.write("Host,IP\n")
  while not myq.empty():
    f.write(myq.get()+"\n")

  f.close()
  logging.info(outfile+" written")

except Exception as err:
  logging.warning(str(err))
  exit()
