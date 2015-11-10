#!/usr/bin/env python

import telnetlib
import logging

def switchTor(mytorhost="localhost", mytorport=9051, mytorpass='""'): #Connects to the instance of the specified Tor controller and creates a new circut: tor host, port and password can be provided in call if desired
  mylogger = logging
  mylogger.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')

  try:
    mytel = telnetlib.Telnet(mytorhost, mytorport, 3)
    mytel.write('authenticate ' + mytorpass + "\n")
    if (mytel.expect(["250 OK"], 2)[0] == -1):
      mylogger.error("AUTHENTICATING TO TOR CONTROL FAILED")
      return False
    mytel.write("signal newnym\n")
    if (mytel.expect(["250 OK"], 2)[0] == -1):
      mylogger.error("CREATING NEW TOR CONNECTION FAILED")
      return False
    
    mylogger.info("New Tor Circut Created")

    mytel.write("quit\n")
    if (mytel.expect(["250 closing connection"], 2)[0] == -1): mylogger.debug("ERROR CLOSING TOR CONTROL CONNECTION")
  
  except EOFError as err:
    mylogger.error("CONNECTING/SWITCHING TOR: " + err)
    return False

  return True

if __name__ == "__main__":
  switchTor()
