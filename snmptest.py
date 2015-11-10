#!/usr/bin/env python

import csv
import logging
from pysnmp.hlapi import *
import sys

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

if len(sys.argv) < 2:
  logging.critical("You must supply the path to the csv file")
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
  elif errorStatus:
    logging.warning(mhost+"["+communitystring+"]"+" : "+ '%s at %s' % (
      errorStatus.prettyPrint(),
      errorIndex and varBinds[int(errorIndex)-1][0] or '?')
      )
  else:
    for name, value in varBinds:
      rval = str(value)

  return rval

with open(csvfl, 'r') as csvfile:
  hr = 1
  reader = csv.reader(csvfile)
  for row in reader:
    oName = oContact = oLocation = Desc = nName = nContact = nLocation = rName = rContact = rLocation = ""
    merr = 0
    if hr == 1:
      hr=0
      continue
    mhost = row[0]
    comstring = row[1]

    oName, oContact, oLocation, Desc, merr = get_snmp(comstring, mhost)
    if merr == 1: continue
    logging.info('%s[%s]::Name:%s ; Contact:%s ; Location:%s ; Description:%s' % (mhost, comstring, oName, oContact, oLocation, Desc))
    
    nName = set_snmp(comstring, mhost, "sysName", "ecfirst-Name")
    nLocation = set_snmp(comstring, mhost, "sysLocation", "ecfirst-Location")
    nContact = set_snmp(comstring, mhost, "sysContact", "ecfirst-contact")
    logging.info('Updated::Name:%s ; Contact:%s ; Location:%s' % (nName, nContact, nLocation))
    
    rName = set_snmp(comstring, mhost, "sysName", oName)
    rLocation = set_snmp(comstring, mhost, "sysLocation", oLocation)
    rContact = set_snmp(comstring, mhost, "sysContact", oContact)
    rName, rContact, rLocation, Desc, merr = get_snmp(comstring, mhost)
    logging.info('Reset::Name:%s ; Contact:%s ; Location:%s' % (rName, rContact, rLocation))
    print ""

print "Done!"

