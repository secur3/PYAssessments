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

if len(sys.argv) < 2:
  print "Usage: dnser.py <base> [startIP] [endIP]"
  exit()

base = sys.argv[1]
maxt = 8
outfile = "/client/"+str(base)+"-nsresults.csv"

logging.basicConfig(level=myloglevel, format='[%(levelname)s] %(message)s')
start = 1
end = 255

if len(sys.argv) > 2:
  if len(sys.argv) != 4:
    print "You must supply both a start and end number, between 1 and 255"
    print "Usage: dnser.py <base> [startIP] [endIP]"
    exit()
  start = int(sys.argv[2])
  end = int(sys.argv[3])
  if (start < 0) or (start > 254) or (end <= start) or (end > 255):
    print "Start and end must be between 1 and 255. You entered "+start+" and "+end
    print "Usage: dnser.py <base> [startIP] [endIP]"
    exit() 

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

for last in range(start,end):
    nhost = base + "." + str(last)
    logging.debug("Checking "+ nhost)
    t = threading.Thread(name=nhost, target=getaddr, args=(nhost,))
    t.daemon=True
    t.start()
    while int(threading.activeCount()) >= maxt+1: pass

while int(threading.activeCount()) > 1: pass

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

