#!/usr/bin/python

# Processes a Kismet netxml file to pull out select info
# and create a .csv file
#
#b.miller 05.12

import sys
import os
import re
import xml.etree.ElementTree as et

export_path = "/client/"
export_file = "wireless_networks"

if (len(sys.argv) < 2):
    print ""
    print "You must provide a Kismet xml file to parse"
    print ""
    sys.exit()

extras = 0

if (len(sys.argv) > 2):
    if sys.argv[2] == "extra":
        extras = 1
        export_file = export_file = "wireless_networks_extra"
    else:
        print ""
        print "Not sure what you mean with with option '"+sys.argv[2]+"'. Ignoring..."
        print ""

myfile = sys.argv[1]

if not os.path.isfile(myfile):
    print ""
    print "'"+myfile+"' does not appear to be a file!"
    print ""
    sys.exit()

clientname = raw_input("Enter client name: ")
export_file = clientname+"_"+export_file+".csv"

doc = et.parse(myfile)
base = doc.getroot()

try:
    wfh = open(export_path+export_file, "w")
    if extras == 1:
        wfh.write("MAC address`SSID`Signal`CH`Encryption`Cipher`Auth`Vendor`Info`Other MACs\n")
    else:
        wfh.write("MAC address`SSID`Signal`CH`Encryption`Cipher`Auth`Vendor`Info\n")
    wfh.close()

except IOError, (enum, err):
    print ""
    print "! "+err+" !"
    print ""
    sys.exit()

for nets in base.getiterator("wireless-network"):
    ssid = ""
    enc = []
    mac = ""
    chan = ""
    sig = ""
    manu = ""
    intmac = []
    info = ""
    encryption = ""
    cipher = ""
    auth = ""
    if nets.attrib["type"] =="infrastructure":
        for assid in nets.getiterator("SSID"):
            typ = assid.find("type")
            if typ.text == "Beacon":
                essid = assid.find("essid")
                if essid.attrib["cloaked"] == "true":
                    ssid = "<HIDDEN>"
                else:
                    ssid = essid.text

                for crypt in assid.getiterator("encryption"):
                    enc.append(crypt.text)

                tinfo = assid.find("info")
                if tinfo is not None:
                    info = tinfo.text

            if typ.text == "Probe Response":
                essid = assid.find("essid")
                if ssid == "<HIDDEN>":
                    ssid = ssid+" ("+essid.text+")"
                elif essid.attrib["cloaked"] == "false":
                    ssid = essid.text

                enc = []
                for crypt in assid.getiterator("encryption"):
                    enc.append(crypt.text)
            
        if ssid == "":
            ssid = "UNKNOWN"
            enc = []
            enc.append("UNKNOWN")

        mac = nets.find("BSSID").text
        manu = nets.find("manuf").text
        chan = nets.find("channel").text
        snr = nets.find("snr-info")
        if snr is not None:
            sig = snr.find("last_signal_dbm").text[1:]

        if (len(enc)) < 2:
            encryption = enc[0]
            cipher = ""
            auth = ""
            if re.search("\+", encryption):
                encryption = enc[0][:enc[0].find("+")]
                cipher = enc[0][enc[0].find("+")+1:]
        elif (len(enc)) == 2:
            encryption = enc[0][:enc[0].find("+")]
            auth = enc[0][enc[0].find("+")+1:]
            cipher = enc[1][enc[1].find("+")+1:]
        elif (len(enc)) == 3:
            encryption = enc[0][:enc[0].find("+")]
            cipher = enc[0][enc[0].find("+")+1:]+" & "+enc[2][enc[2].find("+")+1:]
            auth = enc[1][enc[1].find("+")+1:]

        for clients in nets.getiterator("wireless-client"):
            if clients.attrib["type"] == "fromds":
                if clients.find("client-manuf").text == manu:
                    if clients.find("client-mac").text != mac:
                        intmac.append(clients.find("client-mac").text)

        try:
            wfh = open(export_path+export_file, "a")
            if extras == 1:
                wfh.write(mac+"`"+ssid+"`"+sig+"`"+chan+"`"+encryption+"`"+cipher+"`"+auth+"`"+manu+"`"+info+"`"+str(intmac)+"\n")
            else:
                wfh.write(mac+"`"+ssid+"`"+sig+"`"+chan+"`"+encryption+"`"+cipher+"`"+auth+"`"+manu+"`"+info+"\n")
            wfh.close()

        except IOError, (enum, err):
            print ""
            print "! "+err+" !"
            print ""
            sys.exit()

