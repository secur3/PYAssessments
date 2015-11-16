#!/usr/bin/env python

# Brute force hostnames for a domain
# set 'domain' to the client domain name
# set 'base' to the IP address the 'domain' resolves to
#       this help to catch wildcard entries
# set 'maxt' to the number of concurrent threads
# requires "Recong-ng" installed in the default Kali location (we utilize it's hostname list)

import socket
import threading
import logging
import time
import Queue
from sys import exit

myloglevel = logging.INFO
myq = Queue.Queue()

domain = "example.com"
base = "1.2.3.4"
maxt = 32
outfile = "/client/dnsresults.csv"

logging.basicConfig(level=myloglevel, format='[%(levelname)s] %(message)s')

def getaddr(name):
    try:
       res = socket.gethostbyname(name)
       if (str(res) != base):
           logging.info(name+" => "+str(res))
           myq.put(name+","+str(res))
    except Exception as err:
        logging.warning(name+" : "+str(err))
        if (err.errno == -3):
            logging.warning("Retrying '"+name)
            time.sleep(2)
            getaddr(name)

list = open('/usr/share/recon-ng/data/hostnames.txt')

for name in list.readlines():
    nhost = str(name.rstrip())+"."
    hname = nhost + domain
    logging.debug("Checking "+ hname)
    t = threading.Thread(name=nhost, target=getaddr, args=(hname,))
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

