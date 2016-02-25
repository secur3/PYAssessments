#!/usr/bin/env python

# Brute force hostnames for a network range (/24)
# set 'base' to the IP address of the network range (1.2.3)
# set 'maxt' to the number of concurrent threads
# requires "Recong-ng" installed in the default Kali location (we utilize it's hostname list)

import socket
import threading
import logging
import time
import Queue
from sys import exit
import sys

myloglevel = logging.INFO
myq = Queue.Queue()

if len(sys.argv) != 2:
  print "Usage: dnser.py <base>"
  exit()

base = sys.argv[1]
maxt = 8
outfile = "/client/"+str(base)+"-nsresults.csv"

logging.basicConfig(level=myloglevel, format='[%(levelname)s] %(message)s')

def getaddr(mip):
    try:
       res = socket.gethostbyaddr(str(mip))
       if (str(res[0]) != ''):
           logging.info(mip+" => "+str(res[0]))
           myq.put(mip +","+ str(res[0]))
    except Exception as err:
        logging.warning(mip +" : "+ str(err))
        if (err.errno == -3):
            logging.warning("Retrying '"+mip)
            time.sleep(2)
            getaddr(mip)

for last in range(1,255):
    nhost = base + "." + str(last)
    logging.debug("Checking "+ nhost)
    t = threading.Thread(name=nhost, target=getaddr, args=(nhost,))
    t.daemon=True
    t.start()
    while int(threading.activeCount()) >= maxt+1: pass

try:
  f = open(outfile, 'w')
  f.write("IP,DNS\n")
  while not myq.empty():
    f.write(myq.get()+"\n")

  f.close()
  logging.info(outfile+" written")

except Exception as err:
  logging.warning(str(err))
  exit()

