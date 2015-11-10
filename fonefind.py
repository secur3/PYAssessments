#!/usr/bin/python

#Asks for domain names, company name, optional company nickname
#area codes, prefixes, and base numbers
#
#performs google CSE searchs to identify phone numbers belonging to company.

import mechanize
from urllib import quote
from BeautifulSoup import BeautifulSoup
import json
import os

gAPIkey = 'AIzaSyB5CincvQwb93zn_Sv85-l6aiDwOME-kgs'
gcseID = '001923894653744872258:ggafj6a9ckw'
gbaseurl = 'https://www.googleapis.com/customsearch/v1?key='+gAPIkey+'&cx='+gcseID+'&q='
outfile = '/Users/secur3/phones.txt'
grefer = 'https://mirusec.com/fonefind'

domain = ""
company = ""
compnick = ""
areas = []
prefixes = []
basenums = []
scnt = 0
schk = -1

def getcompinfo():
  dom = ""
  comp = ""
  nick = ""
  while (len(dom) == 0):
    dom = raw_input("Enter the company domain name (i.e. mirussecurity.com): ").rstrip("\n").lower()
    if ("." not in dom):
      print "\tDomain name required"
      dom = ""

  while (len(comp) == 0): comp = raw_input("Enter the company name (i.e. Mirus Security): ").rstrip("\n")
  nick = raw_input("Enter a shortened company name if applicable (i.e. Mirusec)\n\tBe careful with names commonly found in words (i.e. MS, ING, etc.): ").rstrip("\n")
 
  return dom, comp, nick

def getnuminfo(areas=[], prefixes=[], basenums=[], scnt=0, schk=-1, retry=0):
  if (retry == 1):
    areas = []
    prefixes = []
    basenums = []
    scnt = 0
    schk = -1
  
  area = 0
  prefix = 0
  basenum = 0
  while (area == 0):
    area = raw_input("Enter the area code (i.e. 515): ").rstrip("\n")
    if (not area.isdigit()):
      print "\tArea codes consist of 3 numbers"
      area = 0
    elif (len(area) != 3):
      print "\tArea codes consist of 3 numbers"
      area = 0
    elif ((int(area) <= 0) or (int(area) >= 1000)):
      print "\tArea codes are 3 numbers between 000 and 999"
      area = 0
  areas.append(area)
  
  while (prefix == 0):
    prefix = raw_input("Enter the prefix (i.e 555): ").rstrip("\n")
    if (not prefix.isdigit()):
      print "\tPrefixes consist of 3 numbers"
      prefix = 0
    elif (len(prefix) != 3):
      print "\tPrefixes consist of 3 numbers"
      prefix = 0
    elif ((int(prefix) <=0) or (int(prefix) >=1000)):
      print "\tPrefixes are 3 numbers between 000 and 999"
      prefix = 0
  prefixes.append(prefix)
  
  while (basenum == 0):
    basenum = raw_input("Enter the base number, using 'X' for the numbers to replace (i.e. 12XX): ").rstrip("\n")
    if ("X" not in basenum):
      print "\tWe need at least 1 substitution"
      basenum = 0
    elif (len(basenum) != 4):
      print "\tThe base number must be 4 characters"
      basenum = 0
    elif (basenum.find("X") == 0): scnt = 4
    elif (basenum.find("X") == 1):
      if (not basenum[0].isdigit()):
        print "\tCharacters preceeding 'X' must be numbers"
        basenum = 0
      else: scnt = 3
    elif (basenum.find("X") == 2):
      if (not basenum[:2].isdigit()):
        print "\tCharacters preceeding 'X' must be numbers"
        basenum = 0
      else: scnt = 2
    elif (basenum.find("X") == 3):
      if (not basenum[:3].isdigit()):
        print "\tCharacters preceeding 'X' must be numbers"
        basenum = 0
      else: scnt = 1

  if (schk == -1): schk = scnt
  elif (schk != scnt):
    print "Masks do not match. The same number of 'X' placeholders must be in both base numbers.\nTry again"
    getnuminfo(retry=1)

  if (basenum != 0): basenums.append(basenum)

  goagain = raw_input("Enter more numbers? (y,N): ").rstrip("\n").lower()
  if ('y' in goagain): getnuminfo(areas, prefixes, basenums, scnt, schk)

  return areas, prefixes, basenums, scnt

def numbuilder(area, pre, base):
  numvars = ""
  numvars += '"'+area+'-'+pre+'-'+base+'" OR '
  numvars += '"('+area+') '+pre+'-'+base+'" OR '
  numvars += '"('+area+')'+pre+'-'+base+'" OR '
  numvars += '"'+area+'.'+pre+'.'+base+'" OR '
  numvars += '"'+area+pre+base+'"'
  
  return numvars

def checklinksdom(resp, num):
  data = json.load(resp)
  if (int(data['searchInformation']['totalResults']) >= 1):
    print "\t Match for '"+num+"'!"
    winner(num, "confirmed")
    return True

  return False

def checklinks(resp, num, comp, nick):
  data = json.load(resp)
  if (int(data['searchInformation']['totalResults']) >= 1): return False
  for link in data.get("items"):
    if ((comp in link['title']) or (comp in link['snippet'])):
      print "\tPotential match for '"+num+"'!"
      winner(num, "potential")
      return True
    if (len(nick) > 2):
      if ((nick in link['title']) or (nick in link['snippet'])):
        print "\tPotential match for '"+num+"'!"
        winner(num, "potential")
        return True
 
  return False

def winner(num, status):
  try:
    file = open(outfile, 'a')
    file.write(num+"\t"+status+"\n")
    file.close()
  except (IOError) as err:
    print "Error writing to '"+outfile+"' : "+err.strerror
    exit()
  
  return

def gbro(url):
  br = mechanize.Browser()
  br.set_handle_robots(False)
  br.set_handle_refresh(True)
  br.addheaders=[('User-Agent', 'Linux Firefox (Mirus Security)')('Referer', grefer)]
  try:
    resp = br.open(url)
  except (mechanize.HTTPError) as err:
    if (err.code == 403):
      data = json.load(err)
      if (data['error']['errors'][0]['reason'] == "dailyLimitExceeded"):
        print ""
        print "You've exceeded the daily limit of your CSE. Purchase more queries from Google or try back later"
        print ""
        exit()
    else:
      print "uncaught error"
      raise

  return resp


#end functions

if (os.path.isfile(outfile)):
  ans = raw_input("Output file already exists; overwrite it? (Y,n): ")
  if not ("n" in ans.lower()):
    print "'"+outfile+"' deleted"
    print ""
    os.remove(outfile)

domain, company, compnick = getcompinfo()
areas, prefixes, basenums, scnt = getnuminfo()

therange = ''
if (scnt == 4): therange = range(10000)
elif (scnt == 3): therange = range(1000)
elif (scnt == 2): therange = range(100)
else: therange = range(10)

for num in therange:
  if (num < 1000):
    if (num < 100):
      if (num < 10):
        if (scnt > 1):
          num = "0"+str(num)
      if (scnt >= 3):
        num = "0"+str(num)
    if (scnt == 4):
      num = "0"+str(num)

  num = str(num)
  numdex = 0
  for area in areas:
    if (scnt == 4):
      realnum = area+"-"+prefixes[numdex]+"-"+num
      print "Trying '"+realnum+"'..."
      testnums = numbuilder(area, prefixes[numdex], num)
    else:
      realnum = area+"-"+prefixes[numdex]+"-"+basenums[numdex][:4-scnt]+num
      print "Trying '"+realnum+"'..."
      testnums = numbuilder(area, prefixes[numdex], basenums[numdex][:4-scnt]+num)

    cleannum = quote(testnums)
    domurl = gbaseurl+quote('site:'+domain+' '+testnums)
    url = gbaseurl+cleannum

    resp = gbro(domurl)
    if (checklinksdom(resp, realnum)):
      numdex += 1
      continue

    resp = gbro(url)
    checklinks(resp, realnum, company, compnick)

    numdex += 1

print "Done!\nResults written to '"+outfile+"'"
