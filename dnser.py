#!/usr/bin/env python

import socket
import threading
import logging
import time

myloglevel = logging.INFO

domain = "purfoods.com"
base = "198.71.196.31"
maxt = 32

logging.basicConfig(level=myloglevel, format='[%(levelname)s] %(message)s')

def getaddr(name):
    try:
       res = socket.gethostbyname(name)
       if (str(res) != base):
           logging.info(name+" => "+str(res))
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

