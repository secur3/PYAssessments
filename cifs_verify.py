#!/usr/bin/python

import smbclient
import csv
import argparse
import logging
from pathlib import Path
import socket
import smbprotocol

parser=argparse.ArgumentParser()
parser.add_argument("username", help=r"Username to login with, including domain (e.g. 'internal.ecfirst.com\tester')")
parser.add_argument("password", help="Password for the username provided")
parser.add_argument("-f", "--file", help="CSV file containing server,path (NO header row)")
parser.add_argument("-s", "--server", help="Server to connect to (e.g. 'servername')")
parser.add_argument("-p", "--path", help=r"Path to test (e.g. 'path' or 'path\test\test')")
parser.add_argument("--debug", help="Enable DEBUG output", action="store_true")
args = parser.parse_args()

if args.file and (args.server or args.path):
  parser.error("You can't use --file and --server\--path")
if args.server and not args.path:
  parser.error("--server requires --path")
if args.path and not args.server:
  parser.error("--path requires --server")
if not (args.file or args.server):
  parser.error("You have to provide either --file or --server")

if args.debug:
  LOGLEVEL = logging.DEBUG
else:
  LOGLEVEL = logging.INFO
  logging.getLogger("smbprotocol").setLevel(logging.CRITICAL)

logging.basicConfig(format='%(levelname)s:%(message)s', level=LOGLEVEL)

if args.file: hfile = args.file
else:
  hfile = ""
  mserver = args.server
  mpath = args.path

username = args.username
password = args.password

def argcheck (hfile):
  if not Path(hfile).is_file():
    logging.critical("Unable to access '{}'".format(hfile))
    exit()

  return True

def testread (username, password, connect):
  logging.info("Testing '{}'".format(connect))
  success = False
  try:
    listing = smbclient.listdir(r"\\{}".format(connect), username=username, password=password, connection_timeout=15)
    if listing:
      logging.debug("Successful read for '{}'".format(connect))
      success = True
  except smbprotocol.exceptions.SMBResponseException as smberr:
    logging.debug(smberr)
  except (socket.timeout, socket.gaierror, ValueError) as conerr:
    logging.critical("Unable to connect to '{}'".format(connect))
  except smbprotocol.exceptions.SMBAuthenticationError as autherr:
    logging.critical("Bad Creds for '{}'".format(connect))
  return success

def testwrite (username, password, connect):
  logging.info("Testing '{}'".format(connect))
  success = False
  connect = connect+"\ecfirst.txt"
  try:
    with smbclient.open_file(r"\\{}".format(connect), mode="w", username=username, password=password, connection_timeout=15) as fd:
      mwrite = fd.write(u"ecfirst.com")
    if mwrite == 11:
      logging.debug("Successful write for '{}'".format(connect))
      success = True
      mdel = smbclient.remove(r"\\{}".format(connect))
      logging.debug("Successful delete from '{}'".format(connect))
  except smbprotocol.exceptions.SMBResponseException as smberr:
    logging.debug(smberr)
  except (socket.timeout, socket.gaierror, ValueError) as conerr:
    logging.critical("Unable to connect to '{}'".format(connect))
  except smbprotocol.exceptions.SMBAuthenticationError as autherr:
    logging.critical("Bad Creds for '{}'".format(connect))
  except smbprotocol.exceptions.SMBOSError as filerrr:
    logging.critical("Unable to delete from '{}'".format(connect))

  return success

if hfile: argcheck(hfile)

print("")
print("Which mode?")
print("1) Test Read")
print("2) Test Write")
ans = input("Select: ")

if not (ans == "1" or ans == "2"): exit()
if ans == "1": mode = "read"
else: mode = "write"

success = []

if hfile:
  with open(hfile, newline='') as csvfile:
    mcsv = csv.reader(csvfile)
    for row in mcsv:
      res = False
      mserver = row[0]
      mpath = row[1]
      connect = "{}\{}".format(mserver, mpath)
      if mode == "read": res = testread(username, password, connect)
      else: res = testwrite(username, password, connect)
      if res: success.append(connect) 

else:
  res = False
  connect = "{}\{}".format(mserver, mpath)
  if mode == "read": res = testread(username, password, connect)
  else: res = testwrite(username, password, connect)
  if res: success.append(connect)

print("")
if success:
  print("Success:")
  for item in success:
    print(item)

print("Done!")

