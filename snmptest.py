#!/usr/bin/python

# Takes a 2 column (IP,String) CSV file and tests each String
# on the listed IP to validate read vs write level SNMP access
# outputs results to 'resfile'
#
# Requires pysnmp to be installed

from __future__ import print_function
from builtins import input
from builtins import next
from builtins import str
import csv
import logging
from pysnmp.hlapi import *
import sys
from time import sleep
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("csv", help="Path to the CSV file (Headers:Host,String)")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
resfile = '/client/snmp_validated.csv'

if not args.csv:
  logging.critical("You must supply the path to the csv file [Headers:Host,String]")
  sys.exit()
csvfl = sys.argv[1]

def get_snmp(communitystring, mhost):
  sysName = ""
  sysContact = ""
  sysLocation = ""
  sysDescr = ""
  merr = 0

  errorIndication, errorStatus, errorIndex, varBinds = next(
    getCmd(SnmpEngine(),
      CommunityData(communitystring),
      UdpTransportTarget((mhost, 161)),
      ContextData(),
      ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0)),
      ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysName', 0)),
      ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysContact', 0)),
      ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysLocation', 0)))
  )

  # Check for errors and print out results
  if errorIndication:
    logging.critical(mhost+"["+communitystring+"]"+" : "+str(errorIndication))
    merr = 1
  else:
    if errorStatus:
      logging.warning(mhost+"["+communitystring+"]"+" : "+ '%s at %s' % (
        errorStatus.prettyPrint(),
        errorIndex and varBinds[int(errorIndex)-1] or '?'
        )
      )
      merr = 1
    else:
      for name, value in varBinds:
        if str(name) == '1.3.6.1.2.1.1.5.0': sysName = str(value)
        elif str(name) == '1.3.6.1.2.1.1.4.0': sysContact = str(value)
        elif str(name) == '1.3.6.1.2.1.1.6.0': sysLocation = str(value)
        elif str(name) == '1.3.6.1.2.1.1.1.0': sysDescr = str(value)

  return sysName, sysContact, sysLocation, sysDescr, merr

def set_snmp(communitystring, mhost, sysObj, nValue):
  rval = ""
  errorIndication, errorStatus, errorIndex, varBinds = next(
    setCmd(SnmpEngine(),
      CommunityData(communitystring),
      UdpTransportTarget((mhost, 161)),
      ContextData(),
      ObjectType(ObjectIdentity('SNMPv2-MIB', sysObj, 0), nValue))
  )

  if errorIndication:
    logging.critical(mhost+"["+communitystring+"]"+" : "+str(errorIndication))
    rval = "CON ERROR"
  elif errorStatus:
    logging.warning(mhost+"["+communitystring+"]"+" : "+ '%s at %s' % (
      errorStatus.prettyPrint(),
      errorIndex and varBinds[int(errorIndex)-1][0] or '?')
      )
    rval = "SNMP ERROR"
  else:
    for name, value in varBinds:
      rval = str(value)

  return rval

def writer(mhost, comstring, atype, desc, mode='a', ttype='rw'):
  if (mode == "w"): outfile = open(resfile, 'w')
  else: outfile = open(resfile, 'a')
  if (ttype == "ro"):
    outfile.write(mhost+","+comstring+',"'+desc+'"\n')
  else:
    outfile.write(mhost+","+comstring+","+atype+',"'+desc+'"\n')
  outfile.close()

### end functions ###

ansint = 0
while (ansint == 0):
  ans = ''
  print('')
  print('Enter your choice:')
  print("1) Read-only validation")
  print("2) Read-Write validation")
  ans = input("Choice: ")

  try:
    ans = int(ans)
    ansint = 1
  except ValueError:
    pass

  if (ans < 1 or ans > 3):
    print("Done!")
    exit()
if (ans == 1):
  writer("Host", "String", "Access", "Desc", "w", "ro")
else:
  writer("Host", "String", "Access", "Desc", "w", "rw")

with open(csvfl, 'r') as csvfile:
  hr = 1
  reader = csv.reader(csvfile)
  for row in reader:
    changed = 0
    atype = "none"
    Desc = ""

    oName = oContact = oLocation = Desc = nName = nContact = nLocation = rName = rContact = rLocation = ""
    merr = 0
    if hr == 1:
      hr=0
      continue
    mhost = row[0]
    comstring = row[1]

    oName, oContact, oLocation, Desc, merr = get_snmp(comstring, mhost)
    if merr == 1: continue
    atype = "read"
    logging.info('%s[%s]::Name:%s ; Contact:%s ; Location:%s ; Description:%s' % (mhost, comstring, oName, oContact, oLocation, Desc))

    if (ans == 2):
      nName = set_snmp(comstring, mhost, "sysName", "ecfirst-Name")
      if (nName == "ecfirst-Name"): changed = 1
      nLocation = set_snmp(comstring, mhost, "sysLocation", "ecfirst-Location")
      if (nLocation == "ecfirst-Location"): changed = 1
      nContact = set_snmp(comstring, mhost, "sysContact", "ecfirst-contact")
      if (nContact == "ecfirst-contact"): changed = 1
      logging.info('Updated::Name:%s ; Contact:%s ; Location:%s' % (nName, nContact, nLocation))
      if (changed == 1): atype = "read-write"

    if (ans == 1):
      writer(mhost, comstring, atype, Desc, 'a', 'ro')
    else:
      writer(mhost, comstring, atype, Desc)

    if (ans == 2):
      sleep(2)

    if (ans == 2):
      rName = set_snmp(comstring, mhost, "sysName", oName)
      rLocation = set_snmp(comstring, mhost, "sysLocation", oLocation)
      rContact = set_snmp(comstring, mhost, "sysContact", oContact)
      rName, rContact, rLocation, Desc, merr = get_snmp(comstring, mhost)
      logging.info('Reset::Name:%s ; Contact:%s ; Location:%s' % (rName, rContact, rLocation))
      print("")

print("Done!")

