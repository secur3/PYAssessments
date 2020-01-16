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

if len(sys.argv) != 2:
  print("Usage: dnser.py <list>")
  exit()

domain = sys.argv[1]
maxt = 4
outfile = "/client/dnsresults.csv"

logging.basicConfig(level=myloglevel, format='[%(levelname)s] %(message)s')

def getaddr(name):
    try:
       res = socket.gethostbyname(name)
       if (str(res) != ''):
           logging.info(name+" => "+str(res))
           myq.put(name+","+str(res))
    except Exception as err:
        logging.warning(name+" : "+str(err))
        if (err.errno == -3):
            logging.warning("Retrying '"+name)
            time.sleep(2)
            getaddr(name)

list = open(domain)

for name in list.readlines():
    name = name.rstrip()
    logging.debug("Checking "+ name)
    t = threading.Thread(name=name, target=getaddr, args=(name,))
    t.daemon=True
    t.start()
    while int(threading.activeCount()) >= maxt+1: pass

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

