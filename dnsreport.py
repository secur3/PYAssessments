#!/usr/bin/python

#Performs various DNS tests against the provided domain
#proxies some mail tests through scans.ecfirst.com

import dns.resolver
import argparse
import logging
import re
import ipaddress
from datetime import datetime
import smtplib
import socks
import spf

parser = argparse.ArgumentParser()
parser.add_argument('domain', help="The domain to perform testing on")
parser.add_argument("--debug", help="Enable DEBUG output", action="store_true")
args = parser.parse_args()

if args.debug:
  LOGLEVEL = logging.DEBUG
else:
  LOGLEVEL = logging.INFO

logging.basicConfig(format='%(levelname)s:%(message)s', level=LOGLEVEL)

def domTest(dom):
  try:
    a = dns.resolver.resolve(dom, 'SOA')
  except Exception as err:
    logging.critical("Unable to validate domain '{}': {}".format(dom, err.msg))
    exit()

def parentTest(nsresp):
  logging.info("Running 'parent' checks...")
  parent = {}
  #nsresp = dns.resolver.resolve(dom, 'NS')

  test = "Number of nameservers"
  text = 'At least 2 (RFC2182 section 5 recommends at least 3), but fewer than 8 NS records exist (RFC1912 section 2.8 recommends that you have no more than 7).\n\n'
  stat = ""

  nscount = len(nsresp.rrset)
  nslist = []
  for item in nsresp.rrset:
    name = item.target.to_text()
    nslist.append('{}\n'.format(name))

  if (nscount >= 2 and nscount < 8): stat = "PASS"
  else: stat = "FAIL"

  parent[test] = {text:nslist, "Status":stat}

  return parent

def nsTest(nsresp, dom):
  logging.info("Running 'ns' checks...")
  ns = {}
  nameservers = []
  servers = {}
  nsips = []

  test = "Unique nameserver IPs"
  text = 'All nameserver addresses are unique.\n\n'
  stat = ''

  dup = False

  for item in nsresp.rrset:
    name = item.target.to_text()
    try:
      namerec = dns.resolver.resolve(name, 'A')
    except Exception as err:
      logging.warning("Error trying to get IP from hostname '{}'".format(name))

    ip = namerec[0].to_text()
    nameservers.append('{} | {}\n'.format(name, ip))
    servers[name] = ip
    if ip in nsips: dup = True
    else: nsips.append(ip)

  if dup: stat = "FAIL"
  else: stat = "PASS"

  ns[test] = {text:nameservers, "Status":stat}

  dnser = dns.resolver.Resolver()

  test = "All nameservers respond"
  text = 'All nameservers responded.\n\n'
  stat = ''
  nsq = []
  allresp = True

  for name in servers:
    ip = servers[name]
    dnser.nameservers = [ip]
    try:
      a = dnser.resolve(dom, 'A')
      if len(a.rrset) > 0:
        nsq.append('{} | {}\n'.format(name, ip))
    except Exception as err:
      logging.warning("Error querying '{}[{}]'".format(name, ip))

      nsq.append('{} | {} - Failed\n'.format(name, ip))
      allresp = False

  if allresp: stat = "PASS"
  else: stat = "FAIL" 

  ns[test] = {text:nsq, "Status":stat}

  test = "Open DNS servers"
  text = 'Nameservers do not respond to recursive queries\n\n'
  stat = ''
  recs = []
  recurs = False

  for name in servers:
    ip = servers[name]
    dnser.nameservers = [ip]
    try:
      if dom == 'ecfirst.com': tdom = "example.com"
      else: tdom = "ecfirst.com"
      a = dnser.resolve(tdom, 'A')
      if len(a.rrset) > 0:
        recs.append('{} | {} - Recursive\n'.format(name, ip))
        recurs = True
    except Exception as err:
      if "answered REFUSED" not in err.msg:
        logging.warning("Error testing recursion on '{}': {}".format(ip, err.msg))
        recs.append('{} | {} - Error\n'.format(name, ip))
      else:recs.append('{} | {}\n'.format(name, ip))

  if recurs: stat = "FAIL"
  else: stat = "PASS"

  ns[test] = {text:recs, "Status":stat}

  test = "TCP allowed"
  text = 'All nameservers respond to queries via TCP\n\n'
  stat = ''
  noresp = []
  mtcp = True

  for name in servers:
    ip = servers[name]
    dnser.nameservers = [ip]
    try:
      a = dnser.resolve(dom, 'A', tcp=True)
      if len(a.rrset) > 0:
        noresp.append('{} | {}\n'.format(name, ip))
    except Exception as err:
      #logging.warning("Error connecting via TCP to'{}[{}]'".format(name, ip))
      noresp.append('{} | {} - Error\n'.format(name, ip))
      mtcp = False

  if mtcp: stat = "PASS"
  else: stat = "FAIL"

  ns[test] = {text:noresp, "Status":stat}

  test = "Nameserver software version"
  text = 'Responses from nameservers do not appear to be version numbers\n\n'
  stat = ''

  vers = False
  novers = []

  for name in servers:
    ip = servers[name]
    dnser.nameservers = [ip]
    try:  
      a = dnser.resolve("version.bind", 'TXT', "CH")
      if len(a.rrset) > 0:
        ans = a.rrset.to_text()
        vi = ans.index('"')
        vstr = ans[vi:].strip('"')
        x = re.search(r'[0-9]', vstr)
        if x:
          vers = True

        novers.append('{}[{}] | {}\n'.format(name, ip, vstr))
      else: novers.append('{}[{}] | EMPTY\n'.format(name, ip))
    except Exception as err:
      novers.append('{}[{}] | {}\n'.format(name, ip, err.msg))

  if vers: stat = "FAIL"
  else: stat = "PASS"

  ns[test] = {text:novers, "Status":stat}

  test = "All nameservers have identical records"
  text = 'All of your nameservers are providing the same list of nameservers\n\n'
  stat = ''

  ident = True
  diffs = []
  base = []

  for name in servers:
    ip = servers[name]
    dnser.nameservers = [ip]
    try:
      a = dnser.resolve(dom, 'NS')
      if len(a.rrset) > 0:
        dip = []
        if len(base) == 0:
          for item in a.rrset:
            base.append(item.to_text())
          diffs.append('{}[{}] | {}\n'.format(name, ip, base))
        else:
          for item in a.rrset:
            if item.to_text() not in base:
              logging.debug("Missing nameserver '{}' from {}".format(item.to_text(), base))
              ident = False
            dip.append(item.to_text())
          diffs.append('{}[{}] | {}\n'.format(name, ip, dip))
    except Exception as err:
      ident = False
      diffs.append('{}[{}] | {}\n'.format(name, ip, err.msg))

  if ident: stat = "PASS"
  else: stat = "FAIL"

  ns[test] = {text:diffs, "Status":stat}

  test = "All nameserver addresses are public"
  text = 'All of your nameserver addresses are public\n\n'
  stat = ''

  pub = True
  pips = []
  for name in servers:
    ip = servers[name]
    if ipaddress.ip_address(ip).is_private:
      pub = False
    pips.append('{} | {}\n'.format(name, ip))

  if pub: stat = "PASS"
  else: stat = "FAIL"

  ns[test] = {text:pips, "Status":stat}

  return ns, servers

def soaTest(nsresp, dom, servers):
  logging.info("Running 'soa' checks...")
  soa = {}
  soars = []
  slist = {}
  msoa = {}

  dnser = dns.resolver.Resolver()

  test = "SOA record check"
  text = 'All nameservers provided a SOA record for the zone\n\n'
  stat = ''

  rec = True

  for name in servers:
    ip = servers[name]
    dnser.nameservers = [ip]
    try:
      a = dnser.resolve(dom, 'SOA')
      if len(a.rrset) > 0:
        soar = parseSOA(a.rrset[0])
        if soar["primary"] == name: msoa = soar
        elif soar["primary"] not in servers and len(msoa) == 0:
          logging.warning("Primary NS ({}) not in the list of NS provided".format(soar["primary"]))
          msoa = soar
        slist["{}[{}]".format(name, ip)] = soar['serial']
      else:
        rec = False
        soars.append('{} | {} - NO SOA\n'.format(name, ip))
    except Exception as err:
      rec = False
      soars.append('{} | {} - NO SOA\n'.format(name, ip))

  if rec: stat = "PASS"
  else: stat = "FAIL"

  data = ''
  data += 'Primary: {}\nHostmaster: {}\nSerial: {}\nRefresh: {}\nRetry: {}\nExpire: {}\nMinimum: {}'.format(msoa['primary'], msoa['hostmaster'], msoa['serial'], msoa['refresh'], msoa['retry'], msoa['expire'], msoa['minimum'])

  text = text + data

  soa[test] = {text:soars, "Status":stat}

  test = "SOA serial agreement"
  text = "All nameserver SOAs agree on the serial number\n\n"
  stat = ''

  serials = []
  soap = True

  for name in slist:
    serial = slist[name]
    if serial != msoa['serial']: soap = False
    serials.append('{} | {}\n'.format(name, serial))

  if soap: stat = "PASS"
  else: stat = "FAIL"

  soa[test] = {text:serials, "Status":stat}

  test = "SOA field check"
  text = "SOA fields are within recommended ranges\n\n"
  stat = ''

  soac = soaFieldcheck(msoa, servers)
  soaf = []

  if len(soac) > 0:
    stat = "FAIL"
    for field in soac:
      soaf.append("{} {}".format(field, soac[field]))

  else: stat = "PASS"

  soa[test] = {text:soaf, "Status":stat}

  return soa

def soaFieldcheck(msoa, servers):
  soac = {}
  nowyr = (datetime.now()).year

  mnameText = "'mname' should match one of the listed nameservers\n"
  serialText = "'serial' should match the 'YYYYMMDDnn' scheme and must be replaced by proper values for the year (YYYY, four digits), month (MM, two digits), day of month (DD, two digits) and version per day (nn, two digits)\n"
  refreshText = "'refresh' should be a value between 1200 and 43200 seconds\n"
  retryText = "'retry' should be a value less than or equal to half the REFRESH\n"
  expireText = "'expire' should be a value between 1209600 to 2419200\n"
  minimumText = "'minimum' should be a value greater than 300\n"

  mname = msoa['primary']
  if mname not in servers: soac['mname'] = "| {} | {}".format(mname, mnameText)

  serial = str(msoa['serial'])
  if len(serial) != 10: soac['serial'] = "| {} | {}".format(serial, serialText)
  else:
    yr = serial[0:4]
    mn = serial[4:6]
    dy = serial[6:8]
    inc = serial[8:10]

    if int(yr) < 1990 or int(yr) > nowyr: soac['serial'] = "| {} | {}".format(serial, serialText)
    elif int(mn) > 12 or int(mn) < 1: soac['serial'] = "| {} | {}".format(serial, serialText)
    elif int(dy) > 31 or int(dy) < 1: soac['serial'] = "| {} | {}".format(serial, serialText)

  refresh = msoa['refresh']
  if int(refresh) < 1200 or int(refresh) > 43200: soac['refresh'] = "| {} | {}".format(refresh, refreshText)

  retry = msoa['retry']
  if int(retry) > int(refresh)/2: soac['retry'] = "| {} | {}".format(retry, retryText)

  expire = msoa['expire']
  if int(expire) < 1209600 or int(expire) > 2419200: soac['expire'] = "| {} | {}".format(expire, expireText)

  minimum = msoa['minimum']
  if int(minimum) < 300: soac['minimum'] = "| {} | {}".format(minimum, minimumText)

  return soac

def parseSOA(record):
  soar = {}

  soar["primary"] = record.mname.to_text()

  h = record.rname.to_text()
  hm = h.replace(".", "@", 1)
  soar["hostmaster"] = hm

  soar["serial"] = record.serial
  soar["refresh"] = record.refresh
  soar["retry"] = record.retry
  soar["expire"] = record.expire
  soar["minimum"] = record.minimum

  return soar

def mxTest(dom):
  logging.info("Running 'mx' checks...")
  mx = {}

  test = "MX records check"
  text = "More than one MX record exists within the zone (or MX record resolves to multiple IP addresses)\n\n"
  stat = ''

  mmx = True
  mxdup = False
  mc = 0
  mxs = []
  mxaddrs = []
  mails = {}

  try:
    mxrs = dns.resolver.resolve(dom, 'MX')

    for item in mxrs.rrset:
      addrs = []
      pref = item.preference
      name = item.exchange
      mc += 1

      a = dns.resolver.resolve(name, 'A')
      if len(a.rrset) > 1: mc += 1
      for rec in a.rrset:
        addrs.append(rec.address)
        if rec.address not in mxaddrs: mxaddrs.append(rec.address)
        else: mxdup = True
      mails[name] = addrs
      mxs.append("Preference: {} {} {}\n".format(pref, name, addrs))
  except Exception as err:
      if mc <= 1: mmx = False
      logging.warning("Issue getting MX records or IP addresses: {}".format(err.msg))

  if mc < 2: mmx = False
  if mc == 0: mxs.append("No MX records found\n")

  if mmx: stat = "PASS"
  else: stat = "FAIL"

  mx[test] = {text:mxs, "Status":stat}

  test = "Differing mailserver addresses"
  text = "Hostnames referenced by MX records resolve to different IP addresses\n\n"
  stat = ''
  diffadd = []

  for name in mails:
    addrs = mails[name]
    diffadd.append("{} | {}\n".format(name, addrs))

  if len(mxaddrs) < 2: stat = "WARNING"
  elif not mxdup: stat = "PASS"
  else:
    if len(mxaddrs) > 1: stat = "PASS"
    else: stat = "FAIL"

  mx[test] = {text:diffadd, "Status":stat}

  test = "Reverse DNS entries for MX servers"
  text = "All addresses referenced by MX records have matching reverse DNS entries\n\n"
  stat = ''

  rr = True
  rrs = []

  for name in mails:
    addrs = mails[name]
    for ip in addrs:
      try:
        r = dns.resolver.resolve_address(ip)
        ptr = r.rrset[0].target.to_text()
        logging.debug("'{}' | '{}'".format(ptr, name))
        if str(ptr) != str(name): rr = False

        rrs.append("{}[{}] | {}\n".format(ip, name, ptr))
      except Exception as err:
        logging.warning("Issue getting PTR for '{}': {}".format(ip, err.msg))
        rr = False

  if rr: stat = "PASS"
  else: stat = "FAIL"

  mx[test] = {text:rrs, "Status":stat}

  return mx, mails

def mailTest(mails, dom):
  logging.info("Running 'mail' checks...")
  mail = {}

  test = "All IP addresses public"
  text = "All mailserver IP addresses are public\n\n"
  stat = ''

  pub = True
  pips = []

  for name in mails:
    ips = mails[name]
    for ip in ips:
      if ipaddress.ip_address(ip).is_private:
        pub = False
      pips.append('{} | {}\n'.format(name, ip))

  if pub: stat = "PASS"
  else: stat = "FAIL"

  mail[test] = {text:pips, "Status":stat}

  test = "Connect to mail server"
  text = "All connections to Mailservers port 25 are successful\n\n"
  stat = ''

  open = False
  con = True

  connects = []
  relays = []

  socks.setdefaultproxy(socks.SOCKS5, 'scans.ecfirst.com', 1088)
  socks.wrapmodule(smtplib)

  for name in mails:
    try:
      logging.debug("Connecting to mail server '{}'".format(name))
      with smtplib.SMTP(str(name)) as smtp:
        b = smtp.helo('ecfirst.com')
        logging.debug("Hello sent: {}".format(str(b)))
        if " " in str(b[1]):
          bi = str(b[1]).index(" ")
          ban = str(b[1])[0:bi]
        else: ban = str(b[1])
        connects.append("{} | {}\n".format(name, ban))

        if dom == "ecfirst.com": tdom = "mirusec.com"
        else: tdom = 'ecfirst.com'
        sender = 'tester@{}'.format(tdom)
        recept = ['test.user@{}'.format(tdom)]
        message = "From: tester <tester@{}>\nTo: test user <test.user@{}>\nSubject: Testing\n\nThis is a test\n\n".format(tdom, tdom)

        m = smtp.sendmail(sender, recept, message)
        open = True
        relays.append("{} | OPEN RELAY\n".format(name))
    except Exception as err:
      if "Relay " in str(err) or "relay" in str(err):
        relays.append("{} | {}\n".format(name, str(err)))
      else:
        logging.warning("Issue connecting to '{}': {}".format(name, str(err)))
        con = False
        connects.append("{} | {}\n".format(name, str(err)))

  if con: stat = "PASS"
  else: stat = "FAIL"

  mail[test] = {text:connects, "Status":stat}

  test = "Open relay"
  text = "Mailserver does not appear to be an open relay\n\n"
  stat = ''

  if open: stat = "FAIL"
  else: stat = "PASS"

  mail[test] = {text:relays, "Status":stat}

  return mail

def dnssecTest(dom, mails):
  
  return

def spfTest(dom, mails):
  logging.info("Running 'spf' checks...")
  thespf = {}

  test = "SPF record check"
  text = "This domain does have an SPF record\n\n"
  stat = ''

  spfrec = False
  spfres = []
  spfrecord = ''

  a = dns.resolver.resolve(dom, 'TXT')
  if len(a.rrset) > 0:
    for rec in a.rrset:
      if (rec.to_text()).startswith('"v=spf1'):
        spfrec = True
        spfrecord = rec.to_text()
        spfres.append("{} | {}\n".format(dom, spfrecord))
        break

  if spfrec: stat = "PASS"
  else:
    stat = "FAIL"
    spfres.append("{} | NO SPF RECORD\n".format(dom))

  thespf[test] = {text:spfres, "Status":stat}

  test = "SPF coverage"
  text = "The SPF record contains all listed mail servers\n\n"
  stat = ''

  spfi = True
  spfres = []

  if spfrecord:
    for name in mails:
      ips = mails[name]
      for ip in ips:
        check = spf.check2(ip, "tester@{}".format(dom), dom)
        if check[0] != "pass":
          spfi = False
          spfres.append("{}[{}] | NOT IN SPF\n".format(name, ip))

    if spfi: stat = "PASS"
    else: stat = "FAIL"

    thespf[test] = {text:spfres, "Status":stat}

  test = "Permissive SPF record"
  text = "The SPF record does not contain the overly permissive modifier '+all'\n\n"
  stat = ''

  spfa = False

  if spfrecord:
    if "+all" in spfrecord: spfa = True

  if spfa: stat = "FAIL"
  else: stat = "PASS"

  thespf[test] = {text:[], "Status":stat}

  return thespf

def reswrite(res, file):
  #{test:{text:result/info, Status:stat}
  tests = ["parent", "ns", "soa", "mx", "mail", "spf"] #, "dnssec"]
  logging.info("Writing results...")
  with open(file, 'w') as f:
    f.write("Test,Status,Info\n")
    for item in tests:
      data = res[item]
      for ttest in data:
        test = text = status = info = ''
        result = data[ttest]
        test = ttest
        for text in result:
          if text == "Status": status = result[text]
          else:
            t = result[text]
            st = ''
            for s in t: st += s
            info = text + st
        f.write('{},{},"{}"\n'.format(test, status, info))

  logging.info("Results written to '{}'".format(file))

  return

### End Functions ###
dom = args.domain

file = "/client/{}_dns_report.csv".format(dom)

domTest(dom)

res = {}

nsresp = dns.resolver.resolve(dom, 'NS')
soa = dns.resolver.resolve(dom, 'SOA')

parent = parentTest(nsresp)
ns, servers = nsTest(nsresp, dom)
soa = soaTest(nsresp, dom, servers)
mx, mails = mxTest(dom)
mail = mailTest(mails, dom)
thespf = spfTest(dom, mails)

res['parent'] = parent
res['ns'] = ns
res['soa'] = soa
res['mx'] = mx
res['mail'] = mail
res['spf'] = thespf

reswrite(res, file)
