This file is a merged representation of the entire codebase, combined into a single document by Repomix.

<file_summary>
This section contains a summary of this file.

<purpose>
This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.
</purpose>

<file_format>
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  - File path as an attribute
  - Full contents of the file
</file_format>

<usage_guidelines>
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.
</usage_guidelines>

<notes>
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)
</notes>

</file_summary>

<directory_structure>
DL24_backup/
  DL24_backup_01.zip
  DL24_backup_02.zip
  DL24_backup_03.zip
  DL24_backup_04.zip
dl24_lib/
  __init__.py
_我自己的專案使用備註.txt
720p影片紀錄.mp4
螢幕錄製 2026-09-16 154251.mp4
AGENTS.md
battery_cycle_1_20260918_171135.csv
dl24_autotest_03.py
dl24_autotest_04_battery_cycling.py
dl24_autotest_05_battery_cycling.py
dl24_autotest_06_battery_cycling.py
Gen-Z JIG Board Automated Validation Report_EN.pptx
production_test_datalog.csv
README_CHT.md
README.md
RELEASE_NOTES.md
test_config.json
</directory_structure>

<files>
This section contains the contents of the repository's files.

<file path="dl24_lib/__init__.py">
#!/usr/bin/python3

import socket
import errno
from struct import pack
from time import sleep,monotonic
from sys import argv,exit,stdin,stderr
from select import select
# other imports are placed where they are needed, to avoid crashing whole software instead of a single function on a missing dependency


#DEFAULT_SERPORT='/dev/ttyUSB0'
DEFAULT_SERPORT='/dev/rfcomm0'
DEFAULT_BAUDRATE=9600
DEFAULT_TCPPORT=8888

CURRENT_LIMIT=24.1


#DEFAULT_MODBUS_ADDR=1

stdlog=stderr







####################
##
##  LOW LEVEL SERIAL
##
####################


class LowLevelSerPort:
  import serial
  serport='/dev/ttyUSB0'            # target serial port
  baudrate=0
  port=None                         # physical port instance
  verbconn=False
  verbport=False # DEBUG
  verblnk=False
  #verbconn=True
  #verbport=True # DEBUG
  timeout=3
  connretries=5
  connected=False

  def __init__(self,portname='/dev/ttyUSB0',baudrate=DEFAULT_BAUDRATE):
    self.serport=portname
    self.baudrate=baudrate
    pass

  def connect(self):
    if self.verbconn: print('SERPORT:connecting to',self.serport,'@',self.baudrate,file=stdlog)
    for t in range(0,self.connretries):
      try:
        if t>0: print('retrying...',t)
        #self.port=self.serial.Serial(self.serport,self.baudrate, timeout=self.timeout)
        self.port=self.serial.serial_for_url(self.serport,self.baudrate, timeout=self.timeout)
        self.connected=True
        break
      except Exception as e:
        print('PORTCONNERR:',e)
        sleep(1)
    if not self.connected:
      print('ERRPORTCONN: cannot connect to',self.serport,'- too many retries. Aborting.',file=stdlog)
      exit(12)
    if self.verbconn: print('SERPORT:connected',file=stdlog)
    return None

  def close(self):
    if self.port==None: print('SERPORT:neverOpened',file=stdlog);return None
    self.port.close()
    if self.verbconn: print('SERPORT:closed',file=stdlog)
    return None

  def send(self,raw,showpacket=None):
    if showpacket!=None and self.verbconn: showpacket(raw,name='SERPORT:SEND',check=False)
    self.port.write(raw)
    return False

  def recv(self,l,showpacket=None):
    res=self.port.read(l)
    if showpacket!=None and self.verbconn: showpacket(res,name='SERPORT:RECV',check=False)
    return res

  def recvflush(self):
    #n=self.port.in_waiting
    self.port.reset_input_buffer()
    return 0

  def avail(self):
    return self.port.in_waiting



####################
##
##  LOW LEVEL TCP/IP
##
####################

class LowLevelTcpPort:
  ipaddr=None             # target IP
  ipport=None             # target port
  sock=None
  verbconn=False
  verbport=False
  timeout=3
  flushtimeout=0.02
  connretries=5
  connected=False

  reconnect=True
  default_timeout=5 # reconnect timeout for data loss
  time_lastread=-1

  buf=None

  def __init__(self,addr,port):
    self.ipaddr=addr
    self.ipport=port

  def connect(self):
    if self.verbconn: print('SOCK:connecting to',self.ipaddr,':',self.ipport,file=stdlog)
    self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.settimeout(self.timeout)
    for t in range(0,self.connretries):
      try:
        if t>0: print('SOCK:connection retrying...',t,file=stdlog)
        self.sock.connect( (self.ipaddr,self.ipport) )
        self.connected=True
        break
      except Exception as e:
        print('SOCKCONNERR:',e)
        sleep(min(0.5+t,5)) # increase retries delay, max. 5s
    if not self.connected:
      print('ERRSOCKCONN: cannot connect to',self.ipaddr,':',self.ipport,'- too many retries. Aborting.',file=stdlog)
      exit(12)
    self.sock.setblocking(False) # nonblocking
    if self.verbconn: print('SOCK:connected',file=stdlog)
    self.time_lastread=monotonic()
    return self.sock

  def close(self):
    if self.verbconn: print('SOCK:closed',file=stdlog)
    self.sock.close()


  def send(self,raw,showpacket=None):
    if showpacket!=None and self.verbport: showpacket(raw,name='SOCK:SEND',check=False,file=stdlog)
    try:  return self.sock.sendall(raw)
    except socket.error as e:
      print('SOCK:SEND:ERR:',e,file=stderr)
      if self.reconnect: self.connect()

# WARN: ignores l
  def recv(self,l,showpacket=None):
#    res=self.sock.recv(l)
    res=self.buf
    if showpacket!=None and self.verbport: showpacket(res,name='SOCK:RECV',check=False,file=stdlog)
    return res

  def recvflush(self):
    #print('flush')
    self.sock.settimeout(self.flushtimeout)
    try: n=len(self.sock.recv(1024))
    except socket.timeout: n=0
    self.sock.settimeout(self.timeout)
    return n

  # actual reading happens here, do recv() if result nonzero!
  def avail(self):
    #return self.port.in_waiting
    try: self.buf=self.sock.recv(256)
    except socket.error as e:
      err=e.args[0]
      if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
        if monotonic()-self.time_lastread>self.default_timeout:
          print('SOCK:RECV:TIMEOUT',file=stderr)
          try: self.close()
          except Exception as e: print('SOCK:CLOSE:ERR:',e,file=stderr)
          self.connect()
        return 0
      print('SOCK:RECV:ERR:',e,file=stderr)
      if self.reconnect: self.connect()
    self.time_lastread=monotonic()
    return len(self.buf)



############################
##
##  ATORCH OVER SERIAL OR IP
##
############################

def getint32(l,n):
  return (l[n]<<24) + (l[n+1]<<16) + (l[n+2]<<8) + l[n+3]

def getint24(l,n):
  return (l[n]<<16) + (l[n+1]<<8) + l[n+2]

def getint16(l,n):
  return (l[n]<<8) + l[n+1]





class Instr_Atorch:
  #verbcmd=True
  #verbcom=True
  verblnk=False
  verbcom=False
  verbcomsr=False
  #verblnk=False

  dodelay=False

  usesocket=False
  comm=None

  timeout=3
  retries=10

  retries=3 # command send retries, low level
  retriescmd=3 # setting command retries
#  waitretries=20 # response wait retries
  waitretries=50 # response wait retries
  retrydelay=0.05 # response wait

  default_minimize=True  # True for wireless, False for wired


  expectshort=False   # expect short single-byte reply confirmation
  expectans=False
  packet=[]
  pacletlong=[]
  longpacketcnt=0
  longpacketcntold=0

  offoff=False        # switch output off at program close

  out=None
  stopoff=False

  instrtype=None
  ADU=2 # read from instrtype, this is default; possibly specify in config

  PROTO_SHORTACK=0x6F

  CMD_A_CLRALL=0x01
  CMD_A_CLRCAP=0x02
  CMD_A_CLRTIME=0x03
  CMD_A_SETBACKLIGHT=0x21
  CMD_A_SETCOST=0x22
  CMD_A_BUTTON_SET=0x31
  CMD_A_BUTTON_OK=0x32
  CMD_A_BUTTON_RIGHT=0x33
  CMD_A_BUTTON_LEFT=0x34

  BUTTON_SETUP=CMD_A_BUTTON_SET
  BUTTON_ONOFF=CMD_A_BUTTON_OK
  BUTTON_PLUS=CMD_A_BUTTON_RIGHT
  BUTTON_MINUS=CMD_A_BUTTON_LEFT

  CMD_ONOFF=0x01
  CMD_SETCURRENT=0x02
  CMD_SETCUTOFF=0x03
  CMD_SETTIMEOUT=0x04
  CMD_RESET=0x05

  CMD_GETONOFF=0x10
  CMD_GETV=0x11
  CMD_GETA=0x12
  CMD_GETTIMER=0x13
  CMD_GETMAH=0x14
  CMD_GETMWH=0x15
  CMD_GETTEMP=0x16
  CMD_GETSETCUTOFF=0x18
  CMD_GETSETCURRENT=0x17
  CMD_GETSETTIMER=0x19


  def __init__(self):
    #self.buf=Queue()
    self.buf=[]
    self.packet=[]
    self.packetlong=[]
    self.state={}
    pass

  def initport(self,comm):
    #print('INITPORT')
    self.comm=comm

  def connect(self):
    self.comm.connect()

#  def disconnect(self):
#    #print('xxx',self.comm)
#    self.comm.close()

  def close(self):
    if self.offoff: self.setOFF();
    self.comm.close()



  def strpacket(self,p):
    return ':'.join(f'{x:02x}' for x in p)

  # show hexdump of packet, optionally check crc
  def showpacket(self,p,name='',check=False,force=False):
    if self.verbcom or force:
      print(name,':'.join(f'{x:02x}' for x in p),end='',file=stdlog)
      if p==b'': print(name,'(empty)')
      elif check:
        #print(' CRC:',f'{self.atorch_get_crc(p[2:-1]):02x}',file=stdlog)
        if self.atorch_check_crc(p): print(' (correct)',file=stdlog)
        else: print(' (CRC FAIL)',file=stdlog)
      else: print(file=stdlog)


  def atorch_get_crc(self, data):
    sum=0
    #for x in range(2,len(data)-1): sum+=data[x]
    for x in range(0,len(data)): sum+=data[x]
    sum=(sum^0x44) & 0xff
    return sum # dummy function

  def atorch_check_crc(self,data):
    sum=self.atorch_get_crc(data[2:-1])
    #print('[',sum,']')
    if sum==data[-1]: return True;return False



# Bluetooth initialization:
# AT+BMDL24_BLE



# https://github.com/devanlai/webvoltmeter/blob/master/REVERSE.md
# DL24P protocol, 1-per-second, 36-byte: (pfct=power factor, bk=backlight)
#                  x4               x8               xc               x10              x14              x18              x1c              x20
#                  4                8                12               16               20               24               28               32
# [FF][55][01][02] [00][00][00][00] [00][00][00][00] [12][00][00][00] [00][00][00][00] [00][00][00][00] [00][17][00][00] [0A][33][3c][00] [00][00][00][E1]
# [FF][55][01][02] [00][00][33][00] [00][00][00][00] [12][00][00][00] [00][00][00][00] [00][00][00][00] [00][17][00][00] [0A][33][3c][00] [00][00][00][9C]
#              01   -voltage--  -milliamps-  ---power---  ----energy-----  --price?--   -freq-  -pfct-   -temp-                   bk
#              02   -voltage--  -milliamps-  -amphours--  ----energy-----  --price?--           -pfct-   -temp-  --hhhh---mm--ss  bk
#              03   -voltage--  -milliamps-  -amphours--  ----energy-----   usbd+   usbd-   -temp-  --hhhh---mm--ss  bk
#             ADU      0.1v       0.001a       0.01Ah

# command packet: (unspec=00, except ADU=1..3)
# FF 55 11 <adu> <a2> <a3> 00 <a4> <a5> <checksum>
# clr_all         01
# clr_cap         02
# clr_time        03
# set_bklit       21                val
# set_cost        22 [23:16] 00 [15:8][7:0]
# butt_set        31
# butt_ok         32
# butt_right      33
# butt_left       34


# https://github.com/misdoro/Electronic_load_px100/blob/master/protocol_PX-100_2_70.md
# PX100 command packet:
#            B1 B2 [cmd] [d1] [d2] B6
# on/off            01    xx   00       xx=01 for on, 00 for off
# set current       02    xx   yy       xx=integer, yy=decimal (00..99d)
# set cutoff v      03    xx   yy       ""
# set timeout       04    xx   yy       xxyy as unsigned int in seconds
# reset counters    05    00   00
#
# command response: 0x6F = self.PROTO_SHORTACK
#
# query response data:
#               cmd:   CA CB [d1] [d2] [d3] CE CF
# load enabled   10           00   00   xx          xx=00 or 01
# measured mV    11           xx   yy   zz          xxyyzz, 24bit int
# measured mA    12           xx   yy   zz
# timer value    13           hh   mm   ss
# cap mAh        14           xx   yy   zz
# cap mWh        15           xx   yy   zz
# mosfet 'c      16           xx   yy   zz
# set current    17           xx   yy   zz          10s mA
# set cutoff     18           xx   yy   zz          10s mV
# set timer      19           hh   mm   ss

#  buf=bytearray()




  def flushbuf(self,discard=False,cmt=''):
    disc=False # was anything discarded?
    if discard:
      disc=True
      print(f'discard: {cmt} {self.buf.pop(0):02x}',end='',file=stdlog)
    while len(self.buf)>0:
      if (self.expectshort and self.buf[0]==self.PROTO_SHORTACK) \
      or (self.expectans and self.buf[0]==0xCA) \
      or (self.buf[0]==0xff):
         if disc: print(file=stdlog)
         return True
      if not disc: disc=True;print('discard:',end='',file=stdlog)
      print(f' {self.buf.pop(0):02x}',end='',file=stdlog)
    if disc: print(file=stdlog)
    return False

  def clearbuf(self):
    self.buf=[]

  def recvpacket(self):#
    if not self.flushbuf(): return False

    if self.buf[0]==self.PROTO_SHORTACK:
      self.packet=[self.buf.pop(0)]
      self.expectshort=False
      self.showpacket(self.packet,name='short ANS')
      return True

    while len(self.buf)>0:
      if self.buf[0]==0xCA:
        if len(self.buf)<7: return False # too short
        if self.buf[1]!=0xCB or self.buf[5]!=0xCE or self.buf[6]!=0xCF:
          self.flushbuf(discard=True,cmt='in_shortreply');continue
        self.packet=self.buf[:7].copy()
        self.buf=self.buf[7:]
        self.showpacket(self.packet,name='ANS: ')
        return True
      if self.buf[0]==0xFF:
        if len(self.buf)<3: return False
        if self.buf[1]==0x55: #self.flushbuf(discard=True,cmt='2');continue
          if self.buf[2]==0x01: # FF 55 01 - repeated status message
            if len(self.buf)<36: return False
            self.packetlong=self.buf[:36].copy()
            self.buf=self.buf[36:]
#            self.showpacket(self.packetlong,name='long status',check=True)
            if self.atorch_check_crc(self.packetlong): return True
            self.packetlong=[]
            return False
          if self.buf[2]==0x02: # FF 55 02 - 8-byte command response
            if len(self.buf)<8: return False
            self.packet=self.buf[:8].copy()
            self.buf=self.buf[8:]
            if self.packet[3]==1: s='reply'
            elif self.packet[3]==3: s='reply:UNSUPPORTED'
            else: s=f'reply:UNKNOWN:{self.packet[3]:02x}'
            self.showpacket(self.packet,name=s,check=True)
            if self.atorch_check_crc(self.packet): return True
            self.packet=[]
            return False
      self.flushbuf(discard=True,cmt='in_statusmsg')
    return False


  def handlelongpacket(self):
#                  4                8                12               16               20               24               28               32
# [FF][55][01][02] [00][00][00][00] [00][00][00][00] [12][00][00][00] [00][00][00][00] [00][00][00][00] [00][17][00][00] [0A][33][3c][00] [00][00][00][E1]
# [FF][55][01][02] [00][00][33][00] [00][00][00][00] [12][00][00][00] [00][00][00][00] [00][00][00][00] [00][17][00][00] [0A][33][3c][00] [00][00][00][9C]
#              01   -voltage--  -milliamps-  ---power---  ----energy-----  --price?--   -freq-  -pfct-   -temp-                   bk
#              02   -voltage--  -milliamps-  -amphours--  ----energy-----  --price?--           -pfct-   -temp-  --hhhh---mm--ss  bk
#              03   -voltage--  -milliamps-  -amphours--  ----energy-----   usbd+   usbd-   -temp-  --hhhh---mm--ss  bk
#             ADU      0.1v       0.001a       0.01Ah
    self.longpacketcnt+=1
    a=self.state
    l=self.packetlong
    self.instrtype=l[3]
    self.ADU=self.instrtype
    # for ADU=2; todo, other decoding
    a['V']=getint24(l,4)/10
    a['A']=getint24(l,7)/1000
    a['temp']=getint16(l,24)
    #a['aH']=getint24(l,10)/100
    #a['energy']=getint24(l,13)
    #a['price']=getint24(l,16)/100
    #print('state',a)
    self.packetlong=[]

  def gotupdate(self):
    if self.longpacketcnt==self.longpacketcntold: return False
    self.longpacketcntold=self.longpacketcnt
    return True

  def recvdata(self):
    avail=self.comm.avail()
    #print(avail)
    if avail==0: return False
    r=self.comm.recv(avail)
    self.showpacket(r,name='RECV:',force=self.verbcomsr)
    for x in r: self.buf.append(x)
    r=self.recvpacket()
    if r and self.packetlong!=[]: self.handlelongpacket();r=False
    if self.verbcom: print('receivedAns:',r,file=stdlog)
    return r


  def waitreply(self,expectshort=False,retries=0):
    #if retries<1: retries=self.waitretries
    if retries<1: retries=self.waitretries
    for t in range(0,retries):
      sleep(self.retrydelay)
      self.packet=[]
      self.recvdata()
      if self.packet!=[]:
        #self.showpacket(self.packet,name='wait:',force=True)
        if self.packet[0]==self.PROTO_SHORTACK and not expectshort: continue
        return True
    print('REPLY TIMEOUT',file=stdlog)
    return False

  def send_px100cmd_raw(self,cmd,d=[0,0]):
    packet=pack('>BBBBBB',0xb1,0xb2,cmd,d[0],d[1],0xb6)
    for t in range(0,self.retries):
      if cmd<0x10: self.expectshort=True
      else:        self.expectans=True
      self.showpacket(packet,name='SEND:',force=self.verbcomsr)
      sleep(self.retrydelay)
      self.clearbuf()
      self.comm.send(packet)
      if self.waitreply(expectshort=(cmd<0x10), retries=self.waitretries*(t+1)): return True
    return False

  def send_atorch_raw(self,cmd,d=[0,0,0,0]): # second byte, d[1], seems to always be 0
    # FF 55 11 <adu> <a2> <a3> 00 <a4> <a5> <checksum>
    for t in range(0,self.retries):
      packet=pack('>BBBBBBBBB',0xff,0x55,0x11,self.ADU, cmd,d[0],d[1],d[2],d[3])
      sum=self.atorch_get_crc(packet[2:])
      packet=packet+pack('>B',sum)
      self.showpacket(packet,name='SEND:',force=self.verbcomsr)
      sleep(self.retrydelay)
      self.clearbuf()
      self.comm.send(packet)
      if self.waitreply(): return True
    return False

  def px100_query(self,cmd,id='',div=1):
    if self.verbcom: print(f'sending PX100 query ({id})',file=stdlog)
    r=self.send_px100cmd_raw(cmd)
    if not r:
      print(f'ERR: no PX100 response ({id})',file=stdlog)
      return None
    if self.packet[0]!=0xCA or self.packet[1]!=0xCB or self.packet[5]!=0xCE or self.packet[6]!=0xCF:
      self.showpacket(self.packet,name=f'ERR: bad PX100 response ({id})',force=True)
      self.packet=[]
      return None
    self.showpacket(self.packet[2:5],name=f'PX100-value ({id})')
    val=getint24(self.packet,2)
    self.packet=[]
    if div!=1: return val/div
    return val


  def float2pair(self,f):
    int1=int(f)
    int2=int((f-int1)*100)
    return [int1,int2]

  def cmd_setcurrent(self,val=0):
    r=self.send_px100cmd_raw(self.CMD_SETCURRENT,self.float2pair(val))
    if not r: print('ERR: cannot send command!',file=stdlog)

  def cmd_setcutoff(self,val=0):
    r=self.send_px100cmd_raw(self.CMD_SETCUTOFF,self.float2pair(val))
    if not r: print('ERR: cannot send command!',file=stdlog)

  def cmd_setonoff(self,val=0):
    r=self.send_px100cmd_raw(self.CMD_ONOFF,[val,0])
    if not r: print('ERR: cannot send command!',file=stdlog)

  def cmd_resetcounters(self):
    r=self.send_px100cmd_raw(self.CMD_RESET)
    if not r: print('ERR: cannot send command!',file=stdlog)

  def cmd_getonoff(self):
    res=self.px100_query(self.CMD_GETONOFF,id='onoff')
    self.out=res
    return res

  def cmd_getvolt(self,div=1000):
    return self.px100_query(self.CMD_GETV,id='setcurrent',div=div)

  def cmd_getamp(self,div=1000):
    return self.px100_query(self.CMD_GETA,id='setcurrent',div=div)

  def cmd_getsetcurrent(self):
    return self.px100_query(self.CMD_GETSETCURRENT,id='setcurrent',div=100)

  def cmd_getsetcutoff(self):
    return self.px100_query(self.CMD_GETSETCUTOFF,id='setcutoff',div=100)

  def cmd_getah(self,div=1000):
    return self.px100_query(self.CMD_GETMAH,id='Ah',div=div)

  def cmd_getwh(self,div=1000):
    return self.px100_query(self.CMD_GETMWH,id='Wh',div=div)

  def cmd_gettemp(self):
    return self.px100_query(self.CMD_GETTEMP,id='temp')

  def cmd_button(self,butt):
    return self.send_atorch_raw(butt,d=[0,0,0,0])


  def cmd_readstate(self,energy=True,limits=True,temp=True,timestr=None,short=True,listenonly=False):
    #return self.state
    a={}

    if timestr!=None: a['time']=timestr
    if not listenonly:
      a['out']=self.cmd_getonoff()
      self.out=a['out']

    a.update(self.state)
    if listenonly: return a

    a['V']=self.cmd_getvolt()
    if short: return a

    a['A']=self.cmd_getamp()
    if energy:
      a['Ah']=self.cmd_getah()
      a['Wh']=self.cmd_getwh()
    if limits:
      a['Iset']=self.cmd_getsetcurrent()
      a['Vcut']=self.cmd_getsetcutoff()
    if temp:
      a['temp']=self.cmd_gettemp()
    return a


  def setOnOff(self,val,verify=True):
    if val!=0 and val!=1: val=0 # todo, error
    for x in range(0,self.retriescmd):
      self.cmd_setonoff(val)
      if not verify: return True
      res=self.cmd_getonoff()
      if res==val: return True
      print(f'ERR: cannot set output, desired={val}, actual={res}')
    print('ERR: output set failed')
    return False

  def setON(self):
    self.setOnOff(1)

  def setOFF(self):
    self.setOnOff(0)

  def setTOGGLE(self):
    if self.cmd_getonoff()==1: self.cmd_setonoff(0)
    else: self.cmd_setonoff(1)


  def setamp(self,val,rel,verify=True):
    if rel: val=val+self.cmd_getsetcurrent()
    val=round(val,2) # for readback
    if val<0: val=0
    if val>CURRENT_LIMIT: val=CURRENT_LIMIT
    for x in range(0,self.retriescmd):
      self.cmd_setcurrent(val)
      if not verify: return True
      res=self.cmd_getsetcurrent()
      if res==val: return True
      print(f'ERR: cannot set current, desired={val}, actual={res}')
    print('ERR: current set failed')
    return False

  def setcutoff(self,val,verify=True):
    val=round(val,2) # for readback
    if val<0: val=0
    if val>255.2: val=255.2
    for x in range(0,self.retriescmd):
      self.cmd_setcutoff(val)
      if not verify: return True
      res=self.cmd_getsetcutoff()
      if res==val: return True
      print(f'ERR: cannot set cutoff voltage, desired={val}, actual={res}')
    print('ERR: cutoff voltage set failed')
    return False

  def printtype(self):
    typeid={1:'AC sensor',2:'DC sensor',3:'DC/USB sensor'}
    while self.instrtype==None:
      self.recvdata()
    print(f'TYPE: {self.instrtype},',typeid[self.instrtype] if self.instrtype in typeid else 'unknown')

  statopts=''
  def printstate(self,opts='',help=False):
    if help:
      print('          opts:  J=JSON, S=short (V/A only), T=show time, U=show UTC time, A=show all, B=force battery, M=minimize queries, L=listen-only');return
    opts=opts.upper()
    if opts=='': opts=self.statopts
    else: self.statopts=opts
    energy=True
    limits=True
    temp=True
    showtime=False
    showtimeutc=False
    json=False
    listenonly=False
    minimize=True
    if 'S' in opts: energy=False;limits=False;temp=False;minimize=False
    if 'A' in opts: energy=True;limits=True;temp=True;minimize=False
    if 'B' in opts: energy=True
    if 'T' in opts: showtime=True
    if 'U' in opts: showtimeutc=True;showtime=True
    if 'J' in opts: json=True
    if 'L' in opts: listenonly=True
    if 'M' in opts: minimize=True
    timestr=None
    if showtime:
      from datetime import datetime
      if showtimeutc: timestr=datetime.utcnow().isoformat()[:23]
      else: timestr=datetime.now().isoformat()[:23]
    a=self.cmd_readstate(energy=energy,limits=limits,temp=temp,timestr=timestr,short=minimize,listenonly=listenonly)
    if json:
      from json import dumps
      print(dumps(a))
    else:
      print(a) # TODO: formatting



###############################
##
##  HIGH LEVEL COMMAND HANDLING
##
###############################



class PowerLoad:

  verbcmd=False
  verbcomm=False
  verbrun=False

  qend='\n'
  #qend=' '
  lastcmd=''

  def __init__(self):
    self.instr=Instr_Atorch()

  strin=''

  # console input with timeout, returns '' when timeout, False when stdin closed
  def timeout_stdin(self,timeout=0.1, default=""):
    inputs, outputs, errors = select([stdin], [], [], timeout)
    if not inputs: return ''
    s=stdin.readline()
    if len(s)==0: return False # stdin closed
    return s.strip()


  # return float and if it is absolute or relative
  def floatrel(self,val):
    rel=False
    if val[0]=='+' or val[0]=='-': rel=True
    f=float(val)
    return f,rel


  def xint(self,n):
    try: return int(n)
    except: return n

  # handle individual command; dryrun only checks validity, help only prints command description
  def handlecommand(self,cmdorig,dryrun,help=False,verb=verbcmd,mainhelp=False,singlelisten=False):
    #if verb or self.verbcmd: print('cmd:',cmdorig,dryrun,file=stdlog)
    if verb or (self.verbcmd and not dryrun): print('CMD:',cmdorig,file=stdlog)
    cmdarr=(cmdorig+':::').split(':') # enforce minimal length of parameters array
    cmd=cmdarr[0].upper()
    self.lastcmd=cmd
    if cmd=='': return True

    # help
    elif cmd in ['HELP','LIST','?','-H','--HELP']:
      if help: print(' HELP            list commands');return False
      if mainhelp:
        self.helpcommands()
        exit(0)
      elif not dryrun: self.helpcommands()
    elif cmd=='CFGFILE':
      if help: print('  CFGFILE        generate config file template to stdout');return False
      self.makecfgfile()
    elif cmd=='-':
      if help or not dryrun: print();return True

    elif cmd[:4]=='TCP=':
      if help: print('  TCP=addr[:port]           set connection via TCP');return False
      if dryrun:
        a=(cmdorig[4:]+':'+str(DEFAULT_TCPPORT)).split(':')
        self.conf['host']=a[0]
        self.conf['port']=int(a[1])
        for x in ['serport','baudrate']:
          if x in self.conf: self.conf.pop(x)

    elif cmd[:5]=='PORT=':
      if help: print('  PORT=/dev/ttyport[@baud]  set connection via serial port');return False
      if dryrun:
        a=(cmdorig[5:]+'@'+str(DEFAULT_BAUDRATE)).split('@')
        self.conf['serport']=DEFAULT_SERPORT if a[0]=='' else a[0]
        self.conf['baudrate']=a[1]
        for x in ['host','port']:
          if x in self.conf: self.conf.pop(x)


    # single-word queries
    elif cmd=='QV':
      if help: print('  QV             query actual voltage');return False
      if not dryrun: print(self.instr.cmd_getvolt(),end=self.qend)
    elif cmd=='QA' or cmd=='QI':
      if help: print('  QA             query actual current');return False
      if not dryrun: print(self.instr.cmd_getamp(),end=self.qend)
#    elif cmd=='QBV' or cmd=='QVB':
#      if help: print('  QBV            query battery voltage');return False
#      if not dryrun: self.instr.sync();print(self.instr.getreg('V_BAT')/self.instr.vmult,end=self.qend)
    elif cmd=='QMV':
      if help: print('  QMV            query actual voltage, integer millivolts');return False
      if not dryrun: print(self.instr.cmd_getvolt(div=1),end=self.qend)
    elif cmd=='QMA':
      if help: print('  QMA            query actual current, integer milliamps');return False
      if not dryrun: print(self.instr.cmd_getamp(div=1),end=self.qend)
    elif cmd=='QVCUT':
      if help: print('  QVCUT          query cutoff voltage');return False
      if not dryrun: print(self.instr.cmd_getsetcutoff(),end=self.qend)
    elif cmd=='QOUT':
      if help: print('  QOUT           query output state');return False
      if not dryrun: print(self.instr.cmd_getonoff(),end=self.qend)
#    elif cmd=='QTE':
#      if help: print('  QTE            query external temperature');return False
#      if not dryrun: self.instr.sync();print(self.instr.getreg('EXT_C'),end=self.qend)
    elif cmd=='QTI':
      if help: print('  QTI            query internal temperature');return False
      if not dryrun: print(self.instr.cmd_gettemp(),end=self.qend)

    # energy counters
    elif cmd=='RESET':
      if help: print('  RESET          reset energy counters');return False
      if not dryrun: self.instr.cmd_resetcounters()
    elif cmd=='QAH':
      if help: print('  QAH            query amp-hour counter');return False
      if not dryrun: print(self.instr.cmd_getah(div=1000),end=self.qend)
    elif cmd=='QMAH':
      if help: print('  QMAH           query amp-hour counter in integer mAh');return False
      if not dryrun: print(self.instr.cmd_getah(div=1),end=self.qend)
    elif cmd=='QWH':
      if help: print('  QWH            query watt-hour counter');return False
      if not dryrun: print(self.instr.cmd_getwh(div=1000),end=self.qend)
    elif cmd=='QMWH':
      if help: print('  QMWH           query watt-hour counter in integer mWh');return False
      if not dryrun: print(self.instr.cmd_getwh(div=1),end=self.qend)


    # output switch control
    elif cmd=='ON':
      if help: print('  ON             enable output');return False
      if not dryrun: self.instr.setON()
    elif cmd=='OFF':
      if help: print('  OFF            disable output');return False
      if not dryrun: self.instr.setOFF()
    elif cmd=='TOGGLE':
      if help: print('  TOGGLE         toggle output');return False
      if not dryrun: self.instr.setTOGGLE()


    # volt/amp settings
    elif cmd[-4:]=='VCUT':
      if help: print('  nn.nnVCUT      set cutoff voltage');return False
      try: val,rel=self.floatrel(cmd[:-4])
      except: print('[Unknown voltage to set:',cmd,']',file=stderr);return False
      if rel: print('[No relative value for voltage cutoff!]');return False
      if not dryrun: self.instr.setcutoff(val)
    elif cmd[-2:]=='MA':
      if help: print('  nn.nnMA        set output current');return False
      try: val,rel=self.floatrel(cmd[:-2])
      except: print('[Unknown current to set:',cmd,']',file=stderr);return False
      if not dryrun: self.instr.setamp(val/1000,rel=rel)
    elif cmd[-1:]=='A':
      if help: print('  nn.nnA         set output current');return False
      try: val,rel=self.floatrel(cmd[:-1])
      except: print('[Unknown current to set:',cmd,']',file=stderr);return False
      if not dryrun: self.instr.setamp(val,rel=rel)


    # take commands from stdin, help-only here
    elif cmd in ['STDIN']:
      if help: print('  STDIN          read commands from stdin');return False
      #self.instr.bat=True

    elif cmd=='LISTEN':
      if help: print('  LISTEN[:opts[:count]]  listen to status reports, query data, handle stdin')
      if help: print('  LISTEN[:opts[:off]]    listen, until off')
      if help: self.instr.printstate(help=True);return False
      stopoff=False;cnt=-1
      if cmdarr[2]=='': pass
      elif cmdarr[2].upper()=='OFF': stopoff=True
      else:
        try: cnt=int(cmdarr[2])
        except: print('[Unknown count:',cmdorig,']');return False
        if cmdarr[2].upper()=='OFF': stopoff=True
      if not dryrun:
        while True:
          if not singlelisten:
            s=self.timeout_stdin()
            if s:
              #print('STDIN:',s)
              if s.upper()[:6]=='LISTEN': print('ERR: cannot recurse LISTEN',file=stderr);continue
              if self.handlecommand(s,True): self.handlecommand(s,False) # check validity, execute if good
          self.instr.recvdata()
          if self.instr.gotupdate():
            #print(self.instr.state,self.instr.cmd_readstate())
            #d=self.instr.state.copy()
            #d.update(self.instr.cmd_readstate())
            #print(d)
            self.instr.printstate(opts=cmdarr[1])
            if singlelisten: break
            cnt-=1
            if cnt==0: break
            if (stopoff or self.instr.stopoff) and self.instr.out==0: break

    # output formatting
    elif cmd in ['LINE','ONELINE']:
      if help: print('  LINE           output the Q-queries as space-separated instead of newline-separated');return False
      self.qend=' '


    elif cmd in ['WAIT']:
      if help: print('  WAIT           wait for communication from device');return False

    elif cmd in ['ROBUST']:
      if help: print('  ROBUST         increase timeouts and retries');return False
      self.instr.robust=True

    elif cmd in ['OFFOFF']:
      if help: print('  OFFOFF         switch output off on program exit');return False
      self.instr.offoff=True

    elif cmd in ['STOPOFF']:
      if help: print('  STOPOFF        stop loop on output off');return False
      self.instr.stopoff=True

    # verbosity
    elif cmd in ['VERB']:
      if help: print('  VERB[:opts]    list operations')
      if help: self.setverb(help=True);return False
      if not dryrun: self.setverb(opts=cmdarr[1])

    # force delay in processing
    elif cmd[:5]=='SLEEP':
      if help: print('  SLEEPxx        sleep for xx seconds');return False
      s=cmd[5:]+cmdarr[1]
      if s!='':
        try: secs=float(s)
        except: print('['+cmd+': Unknown delay to set:',s,']');return False
      else: secs=1
      if not dryrun:
        for x in range(0,int(secs/0.1)):
          sleep(0.1)
          self.instr.recvdata()

    # perform loop, help and validation only here
    elif cmd=='LOOP':
      if help: print('  LOOP:[xx]      loop for xx time or endless if not specified');return False
      no=cmdarr[1]
      if no!='':
        try: int(no)
        except: print('[Unknown loops count:',cmd,' seen as "'+no+'" ]');return False

    # show device type
    elif cmd=='TYPE':
      if help: print('  TYPE           print detected device type');return False
      if not dryrun: self.instr.printtype()

    # show device type
    elif cmd=='BUTTON':
      if help: print('  BUTTON:[+-SO]  press button (Plus, Minus, Setup, OnOff)');return False
      butt=cmdarr[1][:1].upper()
      if   butt=='+': b=self.instr.BUTTON_PLUS
      elif butt=='-': b=self.instr.BUTTON_MINUS
      elif butt=='S': b=self.instr.BUTTON_SETUP
      elif butt=='O': b=self.instr.BUTTON_ONOFF
      else: print('[Unknown button code:'+cmdorig+' ]');return False
      if not dryrun: self.instr.cmd_button(b)

    elif cmd=='RAWPROTO':
      if help: print('  RAWPROTO:xx[:xx:xx:xx:xx]   raw Atorch protocol send, cmd + 4 payloads');return False
      try: barr=bytearray.fromhex((cmdorig[9:]+' 00 00 00 00 00').replace(':',' '))[:5]
      except: print('[cannot interpret hex string: "'+cmdorig+'" ]');return False
      if not dryrun: self.instr.send_atorch_raw(barr[0],d=barr[1:])

    elif cmd=='RAWPX100':
      if help: print('  RAWPX100:xx[:xx:xx]         raw PX100 protocol send, cmd + 2 payloads');return False
      try: barr=bytearray.fromhex((cmdorig[9:]+' 00 00 00').replace(':',' '))[:3]
      except: print('[cannot interpret hex string: "'+cmdorig+'" ]');return False
      if not dryrun: self.instr.send_px100cmd_raw(barr[0],d=barr[1:])

    elif cmd=='RAWSEND':
      if help: print('  RAWSEND:xx[:xx:xx:...]      raw serial protocol data send');return False
      try: barr=bytearray.fromhex(cmdorig[8:].replace(':',' '))
      except: print('[cannot interpret hex string: "'+cmdorig+'" ]');return False
      if not dryrun:
        self.instr.showpacket(barr,name='SEND:',force=self.instr.verbcomsr)
        self.instr.comm.send(barr)
        sleep(0.1)
        self.instr.waitreply(retries=30)

    elif cmd=='NORETRY':
      if help: print('  NORETRY                     do not retry timeouted commands');return False
      self.instr.retriescmd=1
      self.instr.retries=1

    elif cmd in ['STATE','STAT','STATUS']:
      if help: print('  STATE[:opts]   print setting state in JSON format')
      if not dryrun: self.instr.printstate(opts=cmdarr[1])

    elif cmd in ['JSTATE','JSTAT','JSTATUS','STATEJ','STATJ','STATUSJ']:
      if help: print('  STATEJ[:opts]  print setting state in JSON format, like opts=J')
      if help: self.instr.printstate(help=True);return False
      if not dryrun: self.instr.printstate(opts='J'+cmdarr[1])
      #if self.instr.stopoff and self.instr.out==0: 

    else: print('[Unknown command:',cmdorig,']',file=stderr);return False

    return True



  # list help of commands
  def helpcommands(self):
    helparr=['ON','OFF',
             '-','xVCUT','xMA','xA',
             '-','QV','QMV','QA','QMA','QTI','QVCUT',
             '-','QAH','QMAH','QWH','QMWH','RESET',
             '-','STAT','JSTAT','LISTEN',
             '-','TCP=','PORT=','WAIT','ROBUST','OFFOFF','STOPOFF',
             '-','STDIN','LOOP:','SLEEP','VERB','LINE','TYPE','CFGFILE',
             '-','RAWPROTO','RAWPX100','RAWSEND','NORETRY']
    print('Atorch DL24 artificial control')
    print('Usage:',argv[0],'<command> [command]...')
    print('Commands:')
    print()
    for x in helparr: self.handlecommand(x.upper(),dryrun=True,help=True)
    print()
    print('For volt and amp setting, prefixing the value with + or - marks it as relative, to be added/subtracted to the current value')
    print('Commands are executed in sequence. Writes are cached and grouped together to minimize bus transactions.')
    print('Commands are case-insensitive.')
    print('Command "-" forces a newline into output.')


  # dryrun of commands list
  def verifycommands(self,cmds):
    ok=True
    for x in cmds:
      if not self.handlecommand(x,True,mainhelp=True): ok=False
    return ok

  # dryrun of commands to check validity, then run live
  def handlecommands(self,cmds):
    #print("COMMANDS:",cmds)
#    for x in cmds: self.handlecommand(x,False)
    for t in range(0,len(cmds)):
      cmd=cmds[t].upper()
      #print('CMD:',cmd)
      counter=-1 # endless
      # recursive running of loop
      if cmd[:5]=='LOOP:':
        if len(cmd)>5: counter=int(cmd[5:]) # error check already done in dryrun parse
        while counter!=0:
          counter-=1
          self.handlecommands(cmds[t+1:])
          #if counter==0: break
        break

      # from now, everything comes from stdin
      elif cmd=='STDIN':
        #print('STDIN')
        while True:
          self.instr.recvdata()
          s=self.timeout_stdin()
          if s==False: break # pipe closed
          if s!='':
            #print('STDIN:',s)
            #if s.upper()[:6]=='LISTEN': print('ERR: cannot recurse LISTEN',file=stderr);continue
            if s.upper()=='STDIN':      print('ERR: cannot recurse STDIN',file=stderr);continue
            if self.handlecommand(s,True): self.handlecommand(s,False,singlelisten=True) # check validity, execute if good

      else:
        if self.qend==' ' and cmd[:5]=='SLEEP': print()
        self.handlecommand(cmd,False,verb=False)







  conf={}
  configfilename=None

  def getprocessbarename(self):
    cmdn=('/'+argv[0]).split('/')[-1]
    if cmdn[-3:]=='.py': cmdn=cmdn[:-3]
    return cmdn

  # generate configuration file name from running file name or from name or direct filename
  # TODO: windows compatibility
  def setconfigfilename(self,name=None,filename=None):
    if filename==None:
      if name==None: name=self.getprocessbarename()
      filename='~/.'+name+'.cfg'
    self.configfilename=filename

  # output configfile template to stdout
  def makecfgfile(self):
    if self.configfilename==None: self.setconfigfilename()
    print('# config file goes to '+self.configfilename)
    print("""
# physical serial TTY
# serport=/dev/ttyUSB0
# baudrate=115200
## wait for communication from device before sending data
# waitcomm=1

# plain TCP socket
# host=dt24p.local
# port=8888

# physical port takes precedence if both are defined
""")
    exit(0)

  # integer from string, with error handling
  def cfgint(self,s,msg='Configfile error:',default=-1):
    try: return int(s)
    except:
      print(msg,'Invalid value "'+s+'"',file=stderr)
      print('substituting',default,file=stderr)
      return default

  def isparm(self,parm):
    for x in argv:
      if x.upper()==parm.upper(): return True
    return False

  # read configfile - name=process name, filename=direct config file name
  def readconf(self,name=None,filename=None):
    from os.path import expanduser
    self.setconfigfilename(name=name,filename=filename)
    fn=expanduser(self.configfilename)
    if self.verbrun: print('CONFIGFILE:filename:',fn,file=stdlog)
    try:
      with open(fn,'r') as f:
        all=f.read().split('\n')
        for s in all:
          if '#' in s: continue
          if '=' not in s: continue
          a=(s+'=').split('=')
          self.conf[a[0].strip()]=a[1].strip()
    except Exception as e:
      if self.verbrun: print('CONFIGFILE:FAIL:',e,file=stderr)
      return False
    if self.verbrun: print('CONFIGFILE:',self.conf,file=stdlog)
    return True


  # initialize port from configuration in self.conf
  def initport(self):
    #global comm,port,self.instr
    if 'serport' in self.conf:
      port=self.conf['serport']
      baud=DEFAULT_BAUDRATE if 'baudrate' not in self.conf else self.cfgint(self.conf['baudrate'],default=DEFAULT_BAUDRATE)
      self.instr.initport(LowLevelSerPort(port,baud))
      self.default_minimize=False
    elif 'host' in self.conf:
      host=self.conf['host']
      port=DEFAULT_TCPPORT if 'port' not in self.conf else self.cfgint(self.conf['port'],default=DEFAULT_TCPPORT)
      self.instr.initport(LowLevelTcpPort(host,port))
      self.default_minimize=True
    else:
      print('ERROR: unknown serial port or TCP host',file=stderr)
      print('Use TCP=<host>[:port] or PORT=[/dev/tty...]',file=stderr)
      exit(1)



  def setverb(self,opts='',help=False):
    def setverbopts(opts):
      #if opts=='': opts='L'
      pload.verbrun=True
      if 'C' in opts: self.instr.verbcomsr=True
      if 'D' in opts: self.instr.verbcom=True
      if 'M' in opts: self.verbcmd=True
      if self.instr.comm!=None:
        if 'P' in opts: self.instr.comm.verbconn=True;pload.instr.comm.verbport=True

    if help:
      print('          opts:  P=port, C=communication, D=dataflow, M=commands');return
    if opts!='': setverbopts(opts);return
    for x in argv:
      if x.upper()[:4]=='VERB':
        a=(x.upper()+':').split(':')
        setverbopts(a[1])


#######################################
##
##  user code, no more objects
##
#######################################


if __name__=="__main__":
  cmds=argv[1:]

  pload=PowerLoad()
  pload.setverb() # set verbose flags
  pload.readconf() # set config file

  if len(cmds)==1 and (cmds[0][:4].upper()=='TCP=' or cmds[0][:5].upper()=='PORT='): cmds.append('STATE')
  elif cmds==[]: cmds=['STATE']

  if not pload.verifycommands(cmds):
    print(cmds)
    print('Command error.',file=stderr)
    exit(1)

  # now we read the config, processed parameters by a dry run, and know the port to use
  pload.initport()
  pload.setverb() # set verbose flags again, now for port


  #if pload.isparm('VERB'):    pload.instr.verblnk=True
  #if pload.isparm('VERBCOM'): pload.instr.verbcom=True
  #if pload.isparm('VERBSR'):  pload.instr.verbcomsr=True
  #if pload.isparm('VERBPORT'): pload.instr.comm.verbconn=True;pload.instr.comm.verbport=True

  #if pload.instr.verblnk: print('opening port',file=stdlog)
  pload.instr.connect()
  if pload.isparm('WAIT') or ('waitcomm' in pload.conf and pload.conf['waitcomm']=='1'):
    if pload.verbrun:
      print('waiting for incoming data',file=stdlog)
    while not pload.instr.gotupdate(): sleep(0.05);pload.instr.recvdata()

  if False:
    pload.handlecommands(cmds)
    pload.instr.close() # no exception catching, for debug
  else:
    try:
      pload.handlecommands(cmds)
    except KeyboardInterrupt: pass # clean break
    finally:
      if pload.lastcmd[:5]=='SLEEP' and pload.qend==' ': print()
      pload.instr.close()
</file>

<file path="_我自己的專案使用備註.txt">
將專案打包單一檔案讓 Gemini Notebook 讀取（Windows CMD）：
cd /d "C:\Users\Test\Desktop\Jim\2026_0922_DL24"
npx repomix


步驟 3：使用 AI 產出 AGENTS.md
開啟 ChatGPT、Claude 或 Gemini 網頁端/桌面端。

將剛產生的 repomix-output.xml 檔案附加（上傳）給 AI。

輸入以下提示詞 (Prompt)：

「這是我 USB-PD 3.2 Protocol Log 分析工具的完整專案打包檔。請幫我在專案根目錄下生成一份標準的 AGENTS.md 檔案。內容需包含：

Project Overview：說明這是一個基於 Python 的 USB-PD 3.2 分析與驗證系統。

Architecture & Directory Responsibilities：詳細說明 core/、domain/、rules/、storage/、exporters/、ui/ 與 specs/ 各模組職責。

Core Workflow & FSM：說明資料流向（Parser -> FSM Tracker -> Rule Engine -> Exporter）。

Coding Style & Rules for Agents：提示 Agent 未來修改程式碼時應遵循的原則（例如：保持 Domain 邏輯純粹、新增規則時需於 rules/ 新增並加上 Unit Test 等）。

Common Commands：如何執行測試或主程式（如 python main.py 或 pytest）。」

將 AI 輸出的 Markdown 內容複製，並在專案根目錄建立名為 AGENTS.md 的檔案貼上即可！
</file>

<file path="AGENTS.md">

</file>

<file path="battery_cycle_1_20260918_171135.csv">
Timestamp,Cycle_Index,Phase,Voltage_V,Current_A,Power_W,Temp_C,Capacity_Ah,Energy_Wh,DCIR_mOhm,Status
2026-09-18 17:11:40,1,DISCHARGE,4.383,2.001,8.77,23.0,0.0008,0.0033,313.598,RUNNING
2026-09-18 17:11:42,1,DISCHARGE,4.386,2.002,8.781,23.0,0.0016,0.0069,313.598,RUNNING
2026-09-18 17:11:43,1,DISCHARGE,4.387,1.999,8.77,23.0,0.0024,0.0105,313.598,RUNNING
2026-09-18 17:11:45,1,DISCHARGE,4.385,2.0,8.77,23.0,0.0032,0.014,313.598,RUNNING
2026-09-18 17:11:46,1,DISCHARGE,4.383,2.0,8.766,24.0,0.004,0.0176,313.598,RUNNING
2026-09-18 17:11:48,1,DISCHARGE,4.385,2.003,8.783,23.0,0.0048,0.0212,313.598,RUNNING
2026-09-18 17:11:49,1,DISCHARGE,4.382,2.001,8.768,24.0,0.0057,0.0248,313.598,RUNNING
2026-09-18 17:11:51,1,DISCHARGE,4.385,1.998,8.761,24.0,0.0065,0.0284,313.598,RUNNING
2026-09-18 17:11:52,1,DISCHARGE,4.381,2.004,8.78,24.0,0.0073,0.0319,313.598,RUNNING
2026-09-18 17:11:54,1,DISCHARGE,4.382,2.002,8.773,24.0,0.0081,0.0355,313.598,RUNNING
2026-09-18 17:11:55,1,DISCHARGE,4.004,1.999,8.004,24.0,0.0089,0.0389,313.598,RUNNING
2026-09-18 17:11:57,1,DISCHARGE,3.252,2.003,6.514,24.0,0.0097,0.0419,313.598,RUNNING
2026-09-18 17:11:58,1,DISCHARGE,2.793,2.0,5.586,24.0,0.0106,0.0444,313.598,CUTOFF_REACHED
2026-09-18 17:12:00,1,REST,3.214,0.0,0.0,24.0,0.0106,0.0444,313.598,REST_OCV_RECOVERY
2026-09-18 17:12:02,1,REST,3.211,0.0,0.0,24.0,0.0106,0.0444,313.598,REST_OCV_RECOVERY
2026-09-18 17:12:03,1,REST,3.212,0.0,0.0,24.0,0.0106,0.0444,313.598,REST_OCV_RECOVERY
2026-09-18 17:12:24,1,REST,3.213,0.0,0.0,24.0,0.0106,0.0444,313.598,REST_OCV_RECOVERY
</file>

<file path="dl24_autotest_03.py">
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import csv
import json
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from dl24_lib import Instr_Atorch, LowLevelSerPort
except ImportError as e:
    messagebox.showerror("Error", f"Could not import dl24_lib. Error: {e}\nPlease ensure dl24_lib/__init__.py exists and pyserial is installed.")
    sys.exit(1)

MODES = ["SKYFALL JIG Mode", "FA Direct Mode"]
ALL_PORTS = ["TBTB", "TBTC", "TBTD"]
CSV_HEADER = ["Timestamp", "PCBA_SN", "JIG_ID", "Test_Mode", "Port_ID", "Step_Current_A", "Measured_Volt_V", "Measured_Curr_A", "Vdrop_mV", "OCP_Status", "Step_Result", "Final_Port_Result"]
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_config.json")

DEFAULT_CONFIG = {
    "SKYFALL_JIG_MODE": {
        "STEPS": [1.5, 2.5, 3.0],
        "STEP_DURATION_SEC": 5,
        "V3_0A_PASS_MIN": 4.52,
        "V3_0A_BORDERLINE_MIN": 4.47,
        "OCP_START_CURRENT": 3.5,
        "OCP_MAX_CURRENT": 4.0,
        "OCP_STEP_CURRENT": 0.1,
        "OCP_TRIP_MAX_VOLT": 1.0,
        "RECOVERY_MIN_VOLT": 4.75
    },
    "FA_DIRECT_MODE": {
        "DEFAULT_CURRENT": 1.0,
        "DEFAULT_DURATION": 5,
        "DEFAULT_VMIN": 4.75,
        "DEFAULT_VMAX": 5.25
    }
}

def load_config():
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG


class DL24AutoTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DL24 生產線自動化測試工具 - 進階版")
        self.root.geometry("1100x780")
        self.root.resizable(False, False)
        self.is_running = False
        self.instr = None
        self.config = load_config()
        self.setup_ui()

    def setup_ui(self):
        ttk.Style().theme_use('clam')

        left_panel = ttk.Frame(self.root, width=500)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Notebook tabs
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill=tk.X, pady=(0, 5))

        skyfall_tab = ttk.Frame(self.notebook)
        fa_tab = ttk.Frame(self.notebook)
        self.notebook.add(skyfall_tab, text="SKYFALL JIG Mode")
        self.notebook.add(fa_tab, text="FA Direct Mode")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # FA Direct Mode tab: Test Profile
        fa_cfg = self.config["FA_DIRECT_MODE"]
        fa_profile = ttk.LabelFrame(fa_tab, text="Test Profile", padding=(10, 8))
        fa_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(fa_profile, text="Current (A):", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_current_var = tk.StringVar(value=str(fa_cfg["DEFAULT_CURRENT"]))
        ttk.Entry(fa_profile, textvariable=self.fa_current_var, width=10, font=("Arial", 11)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Duration (Sec):", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_duration_var = tk.StringVar(value=str(fa_cfg["DEFAULT_DURATION"]))
        ttk.Entry(fa_profile, textvariable=self.fa_duration_var, width=10, font=("Arial", 11)).grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmin (V):", font=("Arial", 11)).grid(row=2, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmin_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMIN"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmin_var, width=10, font=("Arial", 11)).grid(row=2, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmax (V):", font=("Arial", 11)).grid(row=3, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmax_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMAX"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmax_var, width=10, font=("Arial", 11)).grid(row=3, column=1, padx=5, pady=4)

        # Connection settings
        conn_frame = ttk.LabelFrame(left_panel, text="連線設定 (Connection)", padding=(10, 10))
        conn_frame.pack(fill=tk.X, pady=5)

        ttk.Label(conn_frame, text="COM Port:", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM3")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=15, font=("Arial", 11)).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(conn_frame, text="Baud Rate:", font=("Arial", 11)).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.baud_var = tk.StringVar(value="9600")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=15, font=("Arial", 11)).grid(row=0, column=3, padx=5, pady=5)

        # Traceability
        trace_frame = ttk.LabelFrame(left_panel, text="資料追蹤 (Traceability)", padding=(10, 10))
        trace_frame.pack(fill=tk.X, pady=5)

        ttk.Label(trace_frame, text="PCBA S/N:", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.pcba_sn_var = tk.StringVar()
        self.pcba_sn_entry = ttk.Entry(trace_frame, textvariable=self.pcba_sn_var, width=25, font=("Arial", 12, "bold"))
        self.pcba_sn_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(trace_frame, text="JIG ID:", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.jig_id_var = tk.StringVar()
        self.jig_id_entry = ttk.Entry(trace_frame, textvariable=self.jig_id_var, width=25, font=("Arial", 12))
        self.jig_id_entry.grid(row=1, column=1, padx=5, pady=5)

        self.autofocus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trace_frame, text="測試完成後自動聚焦 PCBA S/N 欄位", variable=self.autofocus_var).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Port selection
        port_frame = ttk.LabelFrame(left_panel, text="測試連接埠 (Ports)", padding=(10, 10))
        port_frame.pack(fill=tk.X, pady=5)

        self.port_mode_var = tk.StringVar(value="ALL")
        ttk.Radiobutton(port_frame, text="自動測試所有埠 (TBTB -> TBTC -> TBTD)", variable=self.port_mode_var, value="ALL").grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(port_frame, text="單一埠測試:", variable=self.port_mode_var, value="SINGLE").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.single_port_var = tk.StringVar(value="TBTB")
        self.single_port_cb = ttk.Combobox(port_frame, textvariable=self.single_port_var, values=ALL_PORTS, state="readonly", width=15, font=("Arial", 11))
        self.single_port_cb.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Controls
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=15)

        self.start_btn = tk.Button(control_frame, text="開始測試\n(START)", font=("Arial", 18, "bold"), bg="#4CAF50", fg="white", height=2, command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.stop_btn = tk.Button(control_frame, text="強制停止\n(STOP)", font=("Arial", 18, "bold"), bg="#F44336", fg="white", height=2, command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # Live Monitor
        monitor_frame = ttk.LabelFrame(right_panel, text="即時監控 (Live Monitor)", padding=(20, 20))
        monitor_frame.pack(fill=tk.X, pady=(0, 10))

        info_frame = ttk.Frame(monitor_frame)
        info_frame.pack(fill=tk.X, pady=5)

        self.lbl_active_port = tk.Label(info_frame, text="---", font=("Arial", 20, "bold"), fg="blue")
        self.lbl_active_port.pack(side=tk.LEFT, padx=10)

        self.lbl_active_step = tk.Label(info_frame, text="準備中", font=("Arial", 18))
        self.lbl_active_step.pack(side=tk.LEFT, padx=20)

        self.lbl_target_curr = tk.Label(info_frame, text="Target: 0.0 A", font=("Arial", 16, "bold"), fg="darkorange")
        self.lbl_target_curr.pack(side=tk.RIGHT, padx=10)

        reading_frame = ttk.Frame(monitor_frame)
        reading_frame.pack(fill=tk.X, pady=10)

        v_frame = ttk.Frame(reading_frame)
        v_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(v_frame, text="Voltage (V)", font=("Arial", 14)).pack()
        self.lbl_volt = tk.Label(v_frame, text="0.00", font=("Consolas", 42, "bold"), fg="black")
        self.lbl_volt.pack()

        a_frame = ttk.Frame(reading_frame)
        a_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(a_frame, text="Current (A)", font=("Arial", 14)).pack()
        self.lbl_curr = tk.Label(a_frame, text="0.00", font=("Consolas", 42, "bold"), fg="black")
        self.lbl_curr.pack()

        self.result_label = tk.Label(monitor_frame, text="WAITING", font=("Arial", 32, "bold"), fg="white", bg="gray")
        self.result_label.pack(fill=tk.X, pady=10)

        # Logs
        log_frame = ttk.LabelFrame(right_panel, text="測試日誌 (Logs)", padding=(5, 5))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, font=("Consolas", 11), state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


    def on_tab_changed(self, event):
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "FA Direct Mode":
            self.jig_id_var.set("DIRECT_NO_JIG")
            self.jig_id_entry.config(state=tk.DISABLED)
        else:
            if self.jig_id_var.get() == "DIRECT_NO_JIG":
                self.jig_id_var.set("")
            self.jig_id_entry.config(state=tk.NORMAL)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_monitor(self, port=None, step_text=None, volt=None, curr=None, target_a=None):
        if port is not None:
            self.lbl_active_port.config(text=f"Port: {port}")
        if step_text is not None:
            self.lbl_active_step.config(text=step_text)
        if volt is not None:
            self.lbl_volt.config(text=f"{volt:.2f}")
        if curr is not None:
            self.lbl_curr.config(text=f"{curr:.2f}")
        if target_a is not None:
            self.lbl_target_curr.config(text=f"Target: {target_a:.1f} A")
        self.root.update_idletasks()

    def set_ui_state(self, running):
        state = tk.DISABLED if running else tk.NORMAL
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if running else tk.DISABLED)
        self.pcba_sn_entry.config(state=state)
        self.single_port_cb.config(state=state)
        tab_idx = self.notebook.index(self.notebook.select())
        if not running and MODES[tab_idx] == "FA Direct Mode":
            self.jig_id_entry.config(state=tk.DISABLED)
        else:
            self.jig_id_entry.config(state=state)

    def set_big_status(self, text, bg_color):
        self.result_label.config(text=text, bg=bg_color, fg="white" if bg_color not in ["yellow", "lime"] else "black")
        self.root.update_idletasks()

    def start_test(self):
        pcba_sn = self.pcba_sn_var.get().strip()
        jig_id = self.jig_id_var.get().strip()
        if not pcba_sn:
            messagebox.showerror("錯誤", "請輸入 PCBA S/N")
            return
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode != "FA Direct Mode" and not jig_id:
            messagebox.showerror("錯誤", "請輸入 JIG ID")
            return
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "Baud Rate 格式錯誤")
            return
        self.is_running = True
        self.set_ui_state(True)
        self.set_big_status("TESTING", "blue")
        self.update_monitor("---", "Initializing...", 0.0, 0.0, 0.0)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("=== 開始新測試 ===")
        threading.Thread(target=self.run_full_sequence, args=(port, baud, mode, pcba_sn, jig_id), daemon=True).start()

    def stop_test(self):
        self.log("收到停止指令，正在中斷測試...")
        self.is_running = False

    def run_full_sequence(self, com_port, baud, mode, pcba_sn, jig_id):
        final_result_overall = "PASS"
        self.instr = None
        try:
            self.log(f"嘗試連線至 {com_port} ({baud} bps)...")
            self.instr = Instr_Atorch()
            self.instr.initport(LowLevelSerPort(com_port, baud))
            self.instr.connect()
            self.log("串列埠已開啟，等待設備回應...")
            time.sleep(1.0)
            for _ in range(5):
                self.instr.recvdata()
                time.sleep(0.1)
            self.log("連線成功，重置計數器...")
            self.instr.cmd_resetcounters()
            time.sleep(0.5)
            test_v = self.instr.cmd_getvolt()
            if test_v is None:
                self.log("警告: 無法讀取電壓，請確認 DL24 已開機並連接正確 COM Port")
            else:
                self.log(f"通訊確認成功，目前電壓: {test_v} V")

            if mode == "FA Direct Mode":
                final_result_overall = self.run_fa_direct(pcba_sn, jig_id)
            else:
                ports_to_test = ALL_PORTS if self.port_mode_var.get() == "ALL" else [self.single_port_var.get()]
                for i, p in enumerate(ports_to_test):
                    if not self.is_running:
                        break
                    if i > 0 and self.is_running:
                        self.set_big_status("WAITING", "orange")
                        self.update_monitor(p, "Waiting for cable change", 0.0, 0.0, 0.0)
                        response = messagebox.askokcancel("換線提示", f"Please move TBT5 0.8m cable to Port {p} and press [OK] to Continue...", parent=self.root)
                        if not response:
                            self.log("使用者取消後續測試。")
                            self.is_running = False
                            break
                        self.set_big_status("TESTING", "blue")
                    self.log(f"\n--- 準備測試連接埠: {p} ---")
                    port_result = self.run_skyfall_port(pcba_sn, jig_id, p)
                    if port_result == "FAIL":
                        final_result_overall = "FAIL"
                    elif port_result == "BORDERLINE" and final_result_overall == "PASS":
                        final_result_overall = "BORDERLINE"
        except Exception as e:
            self.log(f"發生錯誤: {str(e)}")
            final_result_overall = "FAIL"
        finally:
            if self.instr:
                try:
                    self.instr.setamp(0, rel=False)
                    self.instr.setOFF()
                    self.instr.close()
                except:
                    pass
            self.root.after(0, self.finish_test, final_result_overall)

    def measure_stable(self, retries=3):
        v, a = 0.0, 0.0
        time.sleep(1.0)
        for _ in range(3):
            self.instr.recvdata()
            time.sleep(0.1)
        for _ in range(retries):
            if not self.is_running:
                break
            v_tmp = self.instr.cmd_getvolt()
            if v_tmp is not None:
                v = v_tmp
            a_tmp = self.instr.cmd_getamp()
            if a_tmp is not None:
                a = a_tmp
            time.sleep(0.1)
        return v, a

    # --- FA Direct Mode ---
    def run_fa_direct(self, pcba_sn, jig_id):
        try:
            current = float(self.fa_current_var.get())
            duration = int(self.fa_duration_var.get())
            vmin = float(self.fa_vmin_var.get())
            vmax = float(self.fa_vmax_var.get())
        except ValueError:
            self.log("FA Direct Mode 參數格式錯誤")
            return "FAIL"

        self.update_monitor(port="DIRECT", step_text=f"Load {current}A", target_a=current)
        self.log(f"[FA] 設定電流 {current} A，持續 {duration} 秒")
        self.instr.setamp(current, rel=False)
        time.sleep(0.5)
        self.instr.setON()

        for i in range(duration):
            if not self.is_running:
                self.log("[FA] 使用者中斷測試")
                break
            self.log(f"[FA] 抽載中... 剩餘 {duration - i} 秒")
            time.sleep(1)

        v_meas, a_meas = self.measure_stable()
        self.update_monitor(volt=v_meas, curr=a_meas)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()

        if vmin <= v_meas <= vmax:
            step_result = "PASS"
        else:
            step_result = "FAIL"

        self.log(f"[FA] 測量: {v_meas} V, {a_meas} A -> {step_result}")
        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "FA Direct Mode", "DIRECT", current,
            v_meas, a_meas, 0.0, "N/A", step_result, step_result
        ])
        return step_result

    # --- SKYFALL JIG Mode ---
    def run_skyfall_port(self, pcba_sn, jig_id, port_id):
        cfg = self.config["SKYFALL_JIG_MODE"]
        steps = cfg["STEPS"]
        step_dur = cfg["STEP_DURATION_SEC"]
        pass_min = cfg["V3_0A_PASS_MIN"]
        border_min = cfg["V3_0A_BORDERLINE_MIN"]
        ocp_start = cfg["OCP_START_CURRENT"]
        ocp_max = cfg["OCP_MAX_CURRENT"]
        ocp_step = cfg["OCP_STEP_CURRENT"]
        ocp_trip_v = cfg["OCP_TRIP_MAX_VOLT"]
        recovery_min = cfg["RECOVERY_MIN_VOLT"]

        port_final_result = "PASS"

        # Measure V_idle
        self.update_monitor(port=port_id, step_text="Measuring V_idle...", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        v_idle, _ = self.measure_stable()
        self.log(f"[{port_id}] 空載電壓 V_idle: {v_idle} V")
        self.update_monitor(volt=v_idle, curr=0.0)

        self.instr.setON()
        time.sleep(0.5)

        # Fixed current steps
        for step_a in steps:
            if not self.is_running:
                break
            self.log(f"[{port_id}] 執行電流步階: {step_a} A")
            self.update_monitor(step_text=f"Step {step_a}A", target_a=step_a)
            self.instr.setamp(step_a, rel=False)

            # Wait step_dur seconds
            for _ in range(step_dur):
                if not self.is_running:
                    break
                time.sleep(1)

            v_meas, a_meas = self.measure_stable()
            self.update_monitor(volt=v_meas, curr=a_meas)
            vdrop_mv = (v_idle - v_meas) * 1000.0 if v_idle > 0 else 0.0
            step_result = "PASS"

            if step_a == 3.0:
                if v_meas >= pass_min:
                    step_result = "PASS"
                elif v_meas >= border_min:
                    step_result = "BORDERLINE"
                else:
                    step_result = "FAIL"
                self.log(f"   -> 3.0A 判定: {v_meas} V -> {step_result}")

            if step_result == "FAIL":
                port_final_result = "FAIL"
            elif step_result == "BORDERLINE" and port_final_result == "PASS":
                port_final_result = "BORDERLINE"

            self.log(f"   -> 測量: {v_meas} V, {a_meas} A, Vdrop: {vdrop_mv:.1f} mV")
            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, step_a,
                v_meas, a_meas, round(vdrop_mv, 1), "N/A", step_result, "PENDING"
            ])

        if not self.is_running:
            return port_final_result

        # Dynamic OCP ramp
        self.log(f"[{port_id}] 開始 OCP 動態爬升測試 ({ocp_start}A -> {ocp_max}A)")
        ocp_result = "FAIL (NO_TRIP)"
        ocp_tripped_at = None
        ocp_current = ocp_start

        while ocp_current <= ocp_max + 0.001 and self.is_running:
            ocp_current = round(ocp_current, 2)
            self.log(f"[{port_id}] OCP 測試電流: {ocp_current} A")
            self.update_monitor(step_text=f"OCP {ocp_current}A", target_a=ocp_current)
            self.instr.setamp(ocp_current, rel=False)
            time.sleep(1.5)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_ocp = self.instr.cmd_getvolt()
            if v_ocp is None:
                v_ocp = 0.0
            self.update_monitor(volt=v_ocp)
            self.log(f"   -> OCP 電壓: {v_ocp} V")

            if v_ocp <= ocp_trip_v:
                ocp_result = f"TRIPPED @ {ocp_current}A"
                ocp_tripped_at = ocp_current
                self.log(f"[{port_id}] eFuse 觸發成功！@ {ocp_current} A, V={v_ocp} V")
                break
            ocp_current += ocp_step

        vdrop_ocp = (v_idle - (v_ocp if v_ocp else 0)) * 1000.0 if v_idle > 0 else 0.0
        ocp_step_result = "PASS" if ocp_tripped_at is not None else "FAIL"
        if ocp_step_result == "FAIL":
            port_final_result = "FAIL"

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id,
            ocp_current if ocp_tripped_at else ocp_max,
            v_ocp if v_ocp else 0.0, 0.0, round(vdrop_ocp, 1),
            ocp_result, ocp_step_result, "PENDING"
        ])

        # eFuse recovery verification (only if tripped)
        if ocp_tripped_at is not None and self.is_running:
            self.instr.setamp(0, rel=False)
            self.instr.setOFF()
            self.update_monitor(step_text="等待 eFuse 復歸...", target_a=0.0)
            messagebox.showinfo(
                "eFuse 復歸確認",
                f"eFuse 已成功觸發保護！\n請重新插拔 Type-C 端子以復歸 eFuse，完成後按下【確定】",
                parent=self.root
            )
            self.log(f"[{port_id}] 使用者已重新插拔，等待 1 秒後讀取復歸電壓...")
            time.sleep(1.0)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_recovery = self.instr.cmd_getvolt()
            if v_recovery is None:
                v_recovery = 0.0
            self.update_monitor(volt=v_recovery, curr=0.0)
            self.log(f"[{port_id}] 復歸電壓: {v_recovery} V")

            if v_recovery >= recovery_min:
                recovery_result = "PASS"
                self.log(f"[{port_id}] eFuse 復歸判定: PASS ({v_recovery} V >= {recovery_min} V)")
            else:
                recovery_result = "FAIL (NO_RECOVERY)"
                port_final_result = "FAIL"
                self.log(f"[{port_id}] eFuse 復歸判定: FAIL ({v_recovery} V < {recovery_min} V)")

            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
                v_recovery, 0.0, 0.0, "RECOVERY", recovery_result, "PENDING"
            ])

        # Final reset
        self.update_monitor(step_text="Finishing & Reset", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        time.sleep(0.5)

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
            0.0, 0.0, 0.0, "N/A", "DONE", port_final_result
        ])
        self.log(f"--- 連接埠 {port_id} 測試結束，結果: {port_final_result} ---")
        return port_final_result

    def save_csv_row(self, row):
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production_test_datalog.csv")
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(CSV_HEADER)
                writer.writerow(row)
        except Exception as e:
            self.log(f"CSV寫入失敗: {e}")

    def finish_test(self, final_result):
        self.is_running = False
        self.set_ui_state(False)
        self.update_monitor(step_text="TEST COMPLETE")
        if final_result == "PASS":
            self.set_big_status("PASS", "lime")
        elif final_result == "BORDERLINE":
            self.set_big_status("BORDERLINE", "yellow")
        else:
            self.set_big_status("FAIL", "red")
        self.log("\n測試序列完成。")
        if self.autofocus_var.get():
            self.pcba_sn_entry.delete(0, tk.END)
            self.pcba_sn_entry.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = DL24AutoTestApp(root)
    root.mainloop()
</file>

<file path="dl24_autotest_04_battery_cycling.py">
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import csv
import json
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from dl24_lib import Instr_Atorch, LowLevelSerPort
except ImportError:
    # Dummy fallback class for environments without physical hardware/dl24_lib installed
    class LowLevelSerPort:
        def __init__(self, port, baud):
            pass

    class Instr_Atorch:
        def __init__(self):
            self.v = 5.0
            self.a = 0.0
            self.temp = 28.5
            self.is_on = False

        def initport(self, port):
            pass

        def connect(self):
            pass

        def close(self):
            pass

        def recvdata(self):
            pass

        def cmd_resetcounters(self):
            pass

        def cmd_getvolt(self):
            return self.v if self.is_on else 5.05

        def cmd_getamp(self):
            return self.a if self.is_on else 0.0

        def cmd_gettemp(self):
            return self.temp

        def setamp(self, amp, rel=False):
            self.a = amp

        def setON(self):
            self.is_on = True

        def setOFF(self):
            self.is_on = False

MODES = ["SKYFALL JIG Mode", "FA Direct Mode", "Battery Cycling Mode"]
ALL_PORTS = ["TBTB", "TBTC", "TBTD"]
CSV_HEADER = [
    "Timestamp", "PCBA_SN", "JIG_ID", "Test_Mode", "Port_ID",
    "Step_Current_A", "Measured_Volt_V", "Measured_Curr_A", "Vdrop_mV",
    "OCP_Status", "Step_Result", "Final_Port_Result"
]
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_config.json")

DEFAULT_CONFIG = {
    "SKYFALL_JIG_MODE": {
        "STEPS": [1.5, 2.5, 3.0],
        "STEP_DURATION_SEC": 5,
        "V3_0A_PASS_MIN": 4.52,
        "V3_0A_BORDERLINE_MIN": 4.47,
        "OCP_START_CURRENT": 3.5,
        "OCP_MAX_CURRENT": 4.0,
        "OCP_STEP_CURRENT": 0.1,
        "OCP_TRIP_MAX_VOLT": 1.0,
        "RECOVERY_MIN_VOLT": 4.75
    },
    "FA_DIRECT_MODE": {
        "DEFAULT_CURRENT": 1.0,
        "DEFAULT_DURATION": 5,
        "DEFAULT_VMIN": 4.75,
        "DEFAULT_VMAX": 5.25
    },
    "BATTERY_CYCLE_MODE": {
        "DEFAULT_MODE": "CC",
        "DISCHARGE_CURRENT_A": 2.0,
        "CUTOFF_VOLTAGE_V": 3.0,
        "OVER_TEMP_LIMIT_C": 55.0,
        "REST_TIME_SEC": 900,
        "MAX_CYCLES": 5,
        "SAMPLING_INTERVAL_SEC": 1.0
    }
}


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            battery_defaults = DEFAULT_CONFIG["BATTERY_CYCLE_MODE"]
            battery_cfg = cfg.setdefault("BATTERY_CYCLE_MODE", {})
            for key, value in battery_defaults.items():
                battery_cfg.setdefault(key, value)
            return cfg
    except Exception:
        return DEFAULT_CONFIG


class DL24AutoTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DL24 生產線自動化與電池充放電熱循環測試工具 v4.0")
        self.root.geometry("1120x820")
        self.root.resizable(False, False)
        self.is_running = False
        self.instr = None
        self.load_stop_lock = threading.Lock()
        self.config = load_config()
        self.setup_ui()

    def setup_ui(self):
        ttk.Style().theme_use('clam')

        left_panel = ttk.Frame(self.root, width=510)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Notebook tabs
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill=tk.X, pady=(0, 5))

        skyfall_tab = ttk.Frame(self.notebook)
        fa_tab = ttk.Frame(self.notebook)
        bat_tab = ttk.Frame(self.notebook)

        self.notebook.add(skyfall_tab, text="SKYFALL JIG Mode")
        self.notebook.add(fa_tab, text="FA Direct Mode")
        self.notebook.add(bat_tab, text="Battery Cycling Mode")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # ---------------- SKYFALL Tab Info ----------------
        skyfall_info = ttk.LabelFrame(skyfall_tab, text="SKYFALL JIG 自動化量產參數", padding=(10, 8))
        skyfall_info.pack(fill=tk.X, padx=5, pady=8)
        ttk.Label(skyfall_info, text="抽載步階: 1.5A -> 2.5A -> 3.0A -> 動態 OCP", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(skyfall_info, text="3.0A PASS 門檻: >= 4.52V | 復歸判定: >= 4.75V", font=("Arial", 10)).pack(anchor=tk.W, pady=2)

        # ---------------- FA Direct Mode Tab Profile ----------------
        fa_cfg = self.config["FA_DIRECT_MODE"]
        fa_profile = ttk.LabelFrame(fa_tab, text="FA 單點測試參數 (Test Profile)", padding=(10, 8))
        fa_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(fa_profile, text="Current (A):", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_current_var = tk.StringVar(value=str(fa_cfg["DEFAULT_CURRENT"]))
        ttk.Entry(fa_profile, textvariable=self.fa_current_var, width=10, font=("Arial", 11)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Duration (Sec):", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_duration_var = tk.StringVar(value=str(fa_cfg["DEFAULT_DURATION"]))
        ttk.Entry(fa_profile, textvariable=self.fa_duration_var, width=10, font=("Arial", 11)).grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmin (V):", font=("Arial", 11)).grid(row=2, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmin_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMIN"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmin_var, width=10, font=("Arial", 11)).grid(row=2, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmax (V):", font=("Arial", 11)).grid(row=3, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmax_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMAX"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmax_var, width=10, font=("Arial", 11)).grid(row=3, column=1, padx=5, pady=4)

        # ---------------- Battery Cycling Mode Tab Profile ----------------
        bat_cfg = self.config["BATTERY_CYCLE_MODE"]
        bat_profile = ttk.LabelFrame(bat_tab, text="電池放電容量與熱循環參數", padding=(10, 8))
        bat_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(bat_profile, text="Discharge Current (A):", font=("Arial", 10)).grid(row=0, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_current_var = tk.StringVar(value=str(bat_cfg["DISCHARGE_CURRENT_A"]))
        ttk.Entry(bat_profile, textvariable=self.bat_current_var, width=10, font=("Arial", 10)).grid(row=0, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Cutoff Voltage (V):", font=("Arial", 10)).grid(row=1, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_cutoff_v_var = tk.StringVar(value=str(bat_cfg["CUTOFF_VOLTAGE_V"]))
        ttk.Entry(bat_profile, textvariable=self.bat_cutoff_v_var, width=10, font=("Arial", 10)).grid(row=1, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Over-Temp Limit (°C):", font=("Arial", 10)).grid(row=2, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_overtemp_var = tk.StringVar(value=str(bat_cfg["OVER_TEMP_LIMIT_C"]))
        ttk.Entry(bat_profile, textvariable=self.bat_overtemp_var, width=10, font=("Arial", 10)).grid(row=2, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Rest Duration (Sec):", font=("Arial", 10)).grid(row=3, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_rest_time_var = tk.StringVar(value=str(bat_cfg["REST_TIME_SEC"]))
        ttk.Entry(bat_profile, textvariable=self.bat_rest_time_var, width=10, font=("Arial", 10)).grid(row=3, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Total Cycles:", font=("Arial", 10)).grid(row=4, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_max_cycles_var = tk.StringVar(value=str(bat_cfg["MAX_CYCLES"]))
        ttk.Entry(bat_profile, textvariable=self.bat_max_cycles_var, width=10, font=("Arial", 10)).grid(row=4, column=1, padx=4, pady=3)

        # ---------------- Connection Settings ----------------
        conn_frame = ttk.LabelFrame(left_panel, text="連線設定 (Connection)", padding=(10, 8))
        conn_frame.pack(fill=tk.X, pady=4)

        ttk.Label(conn_frame, text="COM Port:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM3")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=12, font=("Arial", 10)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(conn_frame, text="Baud Rate:", font=("Arial", 10)).grid(row=0, column=2, padx=5, pady=4, sticky=tk.W)
        self.baud_var = tk.StringVar(value="9600")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=12, font=("Arial", 10)).grid(row=0, column=3, padx=5, pady=4)

        # ---------------- Traceability ----------------
        trace_frame = ttk.LabelFrame(left_panel, text="資料追蹤 (Traceability)", padding=(10, 8))
        trace_frame.pack(fill=tk.X, pady=4)

        ttk.Label(trace_frame, text="PCBA S/N:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.pcba_sn_var = tk.StringVar()
        self.pcba_sn_entry = ttk.Entry(trace_frame, textvariable=self.pcba_sn_var, width=25, font=("Arial", 11, "bold"))
        self.pcba_sn_entry.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(trace_frame, text="JIG ID:", font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.jig_id_var = tk.StringVar()
        self.jig_id_entry = ttk.Entry(trace_frame, textvariable=self.jig_id_var, width=25, font=("Arial", 11))
        self.jig_id_entry.grid(row=1, column=1, padx=5, pady=4)

        self.autofocus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trace_frame, text="測試完成後自動聚焦 PCBA S/N 欄位", variable=self.autofocus_var).grid(row=2, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)

        # ---------------- Port Selection ----------------
        port_frame = ttk.LabelFrame(left_panel, text="測試連接埠 (Ports)", padding=(10, 8))
        port_frame.pack(fill=tk.X, pady=4)

        self.port_mode_var = tk.StringVar(value="ALL")
        ttk.Radiobutton(port_frame, text="自動測試所有埠 (TBTB -> TBTC -> TBTD)", variable=self.port_mode_var, value="ALL").grid(row=0, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)
        ttk.Radiobutton(port_frame, text="單一埠測試:", variable=self.port_mode_var, value="SINGLE").grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)

        self.single_port_var = tk.StringVar(value="TBTB")
        self.single_port_cb = ttk.Combobox(port_frame, textvariable=self.single_port_var, values=ALL_PORTS, state="readonly", width=12, font=("Arial", 10))
        self.single_port_cb.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)

        # ---------------- Controls ----------------
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(control_frame, text="開始測試\n(START)", font=("Arial", 16, "bold"), bg="#4CAF50", fg="white", height=2, command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.stop_btn = tk.Button(control_frame, text="強制停止\n(STOP)", font=("Arial", 16, "bold"), bg="#F44336", fg="white", height=2, command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        # ---------------- Live Monitor (Right Panel) ----------------
        monitor_frame = ttk.LabelFrame(right_panel, text="即時監控 (Live Monitor)", padding=(15, 12))
        monitor_frame.pack(fill=tk.X, pady=(0, 8))

        info_frame = ttk.Frame(monitor_frame)
        info_frame.pack(fill=tk.X, pady=3)

        self.lbl_active_port = tk.Label(info_frame, text="---", font=("Arial", 18, "bold"), fg="blue")
        self.lbl_active_port.pack(side=tk.LEFT, padx=5)

        self.lbl_active_step = tk.Label(info_frame, text="準備中", font=("Arial", 16))
        self.lbl_active_step.pack(side=tk.LEFT, padx=15)

        self.lbl_target_curr = tk.Label(info_frame, text="Target: 0.0 A", font=("Arial", 14, "bold"), fg="darkorange")
        self.lbl_target_curr.pack(side=tk.RIGHT, padx=5)

        # Primary Volt / Curr Readings
        reading_frame = ttk.Frame(monitor_frame)
        reading_frame.pack(fill=tk.X, pady=6)

        v_frame = ttk.Frame(reading_frame)
        v_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(v_frame, text="Voltage (V)", font=("Arial", 12)).pack()
        self.lbl_volt = tk.Label(v_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_volt.pack()

        a_frame = ttk.Frame(reading_frame)
        a_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(a_frame, text="Current (A)", font=("Arial", 12)).pack()
        self.lbl_curr = tk.Label(a_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_curr.pack()

        # Dedicated Battery Cycling Indicators Panel
        bat_meter_frame = ttk.LabelFrame(monitor_frame, text="電池放電與熱數據 (Battery Cycling Metrics)", padding=(8, 6))
        bat_meter_frame.pack(fill=tk.X, pady=6)

        m1 = ttk.Frame(bat_meter_frame)
        m1.pack(fill=tk.X, pady=2)

        tk.Label(m1, text="Capacity (Ah):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_ah = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#1976D2")
        self.lbl_ah.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m1, text="Energy (Wh):", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_wh = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#388E3C")
        self.lbl_wh.grid(row=0, column=3, sticky=tk.W, padx=4)

        m2 = ttk.Frame(bat_meter_frame)
        m2.pack(fill=tk.X, pady=2)

        tk.Label(m2, text="Temp (°C):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_temp = tk.Label(m2, text="--.-", font=("Consolas", 12, "bold"), fg="#D32F2F")
        self.lbl_temp.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m2, text="Cycle Progress:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_cycle = tk.Label(m2, text="Cycle 0 / 0", font=("Consolas", 12, "bold"), fg="#7B1FA2")
        self.lbl_cycle.grid(row=0, column=3, sticky=tk.W, padx=4)

        # Big Result Banner
        self.result_label = tk.Label(monitor_frame, text="WAITING", font=("Arial", 28, "bold"), fg="white", bg="gray")
        self.result_label.pack(fill=tk.X, pady=8)

        # Logs Frame
        log_frame = ttk.LabelFrame(right_panel, text="測試日誌 (Logs)", padding=(5, 5))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, font=("Consolas", 10), state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def on_tab_changed(self, event):
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "FA Direct Mode":
            self.jig_id_var.set("DIRECT_NO_JIG")
            self.jig_id_entry.config(state=tk.DISABLED)
        elif mode == "Battery Cycling Mode":
            if not self.jig_id_var.get() or self.jig_id_var.get() == "DIRECT_NO_JIG":
                self.jig_id_var.set("BATTERY_TEST")
            self.jig_id_entry.config(state=tk.NORMAL)
        else:
            if self.jig_id_var.get() in ["DIRECT_NO_JIG", "BATTERY_TEST"]:
                self.jig_id_var.set("")
            self.jig_id_entry.config(state=tk.NORMAL)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_monitor(self, port=None, step_text=None, volt=None, curr=None, target_a=None, ah=None, wh=None, temp=None, cycle_str=None):
        if port is not None:
            self.lbl_active_port.config(text=f"Port: {port}")
        if step_text is not None:
            self.lbl_active_step.config(text=step_text)
        if volt is not None:
            self.lbl_volt.config(text=f"{volt:.2f}")
        if curr is not None:
            self.lbl_curr.config(text=f"{curr:.2f}")
        if target_a is not None:
            self.lbl_target_curr.config(text=f"Target: {target_a:.1f} A")
        if ah is not None:
            self.lbl_ah.config(text=f"{ah:.4f}")
        if wh is not None:
            self.lbl_wh.config(text=f"{wh:.4f}")
        if temp is not None:
            self.lbl_temp.config(text=f"{temp:.1f}")
        if cycle_str is not None:
            self.lbl_cycle.config(text=cycle_str)
        self.root.update_idletasks()

    def set_ui_state(self, running):
        state = tk.DISABLED if running else tk.NORMAL
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if running else tk.DISABLED)
        self.pcba_sn_entry.config(state=state)
        self.single_port_cb.config(state=state)
        tab_idx = self.notebook.index(self.notebook.select())
        if not running and MODES[tab_idx] == "FA Direct Mode":
            self.jig_id_entry.config(state=tk.DISABLED)
        else:
            self.jig_id_entry.config(state=state)

    def set_big_status(self, text, bg_color):
        self.result_label.config(text=text, bg=bg_color, fg="white" if bg_color not in ["yellow", "lime"] else "black")
        self.root.update_idletasks()

    def get_temp_safe(self):
        if self.instr and hasattr(self.instr, "cmd_gettemp"):
            try:
                t = self.instr.cmd_gettemp()
                if t is not None:
                    return float(t)
            except Exception:
                pass
        return 28.5  # Default ambient temperature fallback

    def start_test(self):
        pcba_sn = self.pcba_sn_var.get().strip()
        jig_id = self.jig_id_var.get().strip()
        if not pcba_sn:
            messagebox.showerror("錯誤", "請輸入 PCBA S/N")
            return
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "SKYFALL JIG Mode" and not jig_id:
            messagebox.showerror("錯誤", "請輸入 JIG ID")
            return
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "Baud Rate 格式錯誤")
            return
        self.is_running = True
        self.set_ui_state(True)
        self.set_big_status("TESTING", "blue")
        self.update_monitor("---", "Initializing...", 0.0, 0.0, 0.0, ah=0.0, wh=0.0, temp=25.0, cycle_str="Cycle 0/0")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log(f"=== 開始新測試: {mode} ===")
        threading.Thread(target=self.run_full_sequence, args=(port, baud, mode, pcba_sn, jig_id), daemon=True).start()

    def stop_test(self):
        self.log("收到停止指令，正在中斷測試並關閉負載...")
        self.is_running = False
        self.stop_load()

    def stop_load(self):
        with self.load_stop_lock:
            if not self.instr:
                return
            try:
                self.instr.setamp(0, rel=False)
            except Exception:
                pass
            try:
                self.instr.setOFF()
            except Exception:
                pass

    def run_full_sequence(self, com_port, baud, mode, pcba_sn, jig_id):
        final_result_overall = "PASS"
        self.instr = None
        try:
            self.log(f"嘗試連線至 {com_port} ({baud} bps)...")
            self.instr = Instr_Atorch()
            self.instr.initport(LowLevelSerPort(com_port, baud))
            self.instr.connect()
            self.log("串列埠已開啟，等待設備回應...")
            time.sleep(1.0)
            for _ in range(5):
                self.instr.recvdata()
                time.sleep(0.1)
            self.log("連線成功，重置計數器...")
            self.instr.cmd_resetcounters()
            time.sleep(0.5)
            test_v = self.instr.cmd_getvolt()
            if test_v is None:
                self.log("警告: 無法讀取電壓，請確認 DL24 已開機並連接正確 COM Port")
            else:
                self.log(f"通訊確認成功，目前電壓: {test_v} V")

            if mode == "FA Direct Mode":
                final_result_overall = self.run_fa_direct(pcba_sn, jig_id)
            elif mode == "Battery Cycling Mode":
                final_result_overall = self.run_battery_cycling(pcba_sn, jig_id)
            else:
                ports_to_test = ALL_PORTS if self.port_mode_var.get() == "ALL" else [self.single_port_var.get()]
                for i, p in enumerate(ports_to_test):
                    if not self.is_running:
                        break
                    if i > 0 and self.is_running:
                        self.set_big_status("WAITING", "orange")
                        self.update_monitor(p, "Waiting for cable change", 0.0, 0.0, 0.0)
                        response = messagebox.askokcancel("換線提示", f"Please move TBT5 0.8m cable to Port {p} and press [OK] to Continue...", parent=self.root)
                        if not response:
                            self.log("使用者取消後續測試。")
                            self.is_running = False
                            break
                        self.set_big_status("TESTING", "blue")
                    self.log(f"\n--- 準備測試連接埠: {p} ---")
                    port_result = self.run_skyfall_port(pcba_sn, jig_id, p)
                    if port_result == "FAIL":
                        final_result_overall = "FAIL"
                    elif port_result == "BORDERLINE" and final_result_overall == "PASS":
                        final_result_overall = "BORDERLINE"
        except Exception as e:
            self.log(f"發生錯誤: {str(e)}")
            final_result_overall = "FAIL"
        finally:
            if self.instr:
                try:
                    self.stop_load()
                    self.instr.close()
                except Exception:
                    pass
            self.root.after(0, self.finish_test, final_result_overall)

    def measure_stable(self, retries=3):
        v, a = 0.0, 0.0
        time.sleep(0.5)
        if self.instr:
            for _ in range(2):
                self.instr.recvdata()
                time.sleep(0.05)
            for _ in range(retries):
                if not self.is_running:
                    break
                v_tmp = self.instr.cmd_getvolt()
                if v_tmp is not None:
                    v = v_tmp
                a_tmp = self.instr.cmd_getamp()
                if a_tmp is not None:
                    a = a_tmp
                time.sleep(0.05)
        return v, a

    # ---------------- FA Direct Mode ----------------
    def run_fa_direct(self, pcba_sn, jig_id):
        try:
            current = float(self.fa_current_var.get())
            duration = int(self.fa_duration_var.get())
            vmin = float(self.fa_vmin_var.get())
            vmax = float(self.fa_vmax_var.get())
        except ValueError:
            self.log("FA Direct Mode 參數格式錯誤")
            return "FAIL"

        self.update_monitor(port="DIRECT", step_text=f"Load {current}A", target_a=current)
        self.log(f"[FA] 設定電流 {current} A，持續 {duration} 秒")
        self.instr.setamp(current, rel=False)
        time.sleep(0.5)
        self.instr.setON()

        for i in range(duration):
            if not self.is_running:
                self.log("[FA] 使用者中斷測試")
                break
            self.log(f"[FA] 抽載中... 剩餘 {duration - i} 秒")
            time.sleep(1)

        v_meas, a_meas = self.measure_stable()
        self.update_monitor(volt=v_meas, curr=a_meas)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()

        if vmin <= v_meas <= vmax:
            step_result = "PASS"
        else:
            step_result = "FAIL"

        self.log(f"[FA] 測量: {v_meas} V, {a_meas} A -> {step_result}")
        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "FA Direct Mode", "DIRECT", current,
            v_meas, a_meas, 0.0, "N/A", step_result, step_result
        ])
        return step_result

    # ---------------- SKYFALL JIG Mode ----------------
    def run_skyfall_port(self, pcba_sn, jig_id, port_id):
        cfg = self.config["SKYFALL_JIG_MODE"]
        steps = cfg["STEPS"]
        step_dur = cfg["STEP_DURATION_SEC"]
        pass_min = cfg["V3_0A_PASS_MIN"]
        border_min = cfg["V3_0A_BORDERLINE_MIN"]
        ocp_start = cfg["OCP_START_CURRENT"]
        ocp_max = cfg["OCP_MAX_CURRENT"]
        ocp_step = cfg["OCP_STEP_CURRENT"]
        ocp_trip_v = cfg["OCP_TRIP_MAX_VOLT"]
        recovery_min = cfg["RECOVERY_MIN_VOLT"]

        port_final_result = "PASS"

        # Measure V_idle
        self.update_monitor(port=port_id, step_text="Measuring V_idle...", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        v_idle, _ = self.measure_stable()
        self.log(f"[{port_id}] 空載電壓 V_idle: {v_idle} V")
        self.update_monitor(volt=v_idle, curr=0.0)

        self.instr.setON()
        time.sleep(0.5)

        # Fixed current steps
        for step_a in steps:
            if not self.is_running:
                break
            self.log(f"[{port_id}] 執行電流步階: {step_a} A")
            self.update_monitor(step_text=f"Step {step_a}A", target_a=step_a)
            self.instr.setamp(step_a, rel=False)

            for _ in range(step_dur):
                if not self.is_running:
                    break
                time.sleep(1)

            v_meas, a_meas = self.measure_stable()
            self.update_monitor(volt=v_meas, curr=a_meas)
            vdrop_mv = (v_idle - v_meas) * 1000.0 if v_idle > 0 else 0.0
            step_result = "PASS"

            if step_a == 3.0:
                if v_meas >= pass_min:
                    step_result = "PASS"
                elif v_meas >= border_min:
                    step_result = "BORDERLINE"
                else:
                    step_result = "FAIL"
                self.log(f"   -> 3.0A 判定: {v_meas} V -> {step_result}")

            if step_result == "FAIL":
                port_final_result = "FAIL"
            elif step_result == "BORDERLINE" and port_final_result == "PASS":
                port_final_result = "BORDERLINE"

            self.log(f"   -> 測量: {v_meas} V, {a_meas} A, Vdrop: {vdrop_mv:.1f} mV")
            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, step_a,
                v_meas, a_meas, round(vdrop_mv, 1), "N/A", step_result, "PENDING"
            ])

        if not self.is_running:
            return port_final_result

        # Dynamic OCP ramp
        self.log(f"[{port_id}] 開始 OCP 動態爬升測試 ({ocp_start}A -> {ocp_max}A)")
        ocp_result = "FAIL (NO_TRIP)"
        ocp_tripped_at = None
        ocp_current = ocp_start

        while ocp_current <= ocp_max + 0.001 and self.is_running:
            ocp_current = round(ocp_current, 2)
            self.log(f"[{port_id}] OCP 測試電流: {ocp_current} A")
            self.update_monitor(step_text=f"OCP {ocp_current}A", target_a=ocp_current)
            self.instr.setamp(ocp_current, rel=False)
            time.sleep(1.5)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_ocp = self.instr.cmd_getvolt()
            if v_ocp is None:
                v_ocp = 0.0
            self.update_monitor(volt=v_ocp)
            self.log(f"   -> OCP 電壓: {v_ocp} V")

            if v_ocp <= ocp_trip_v:
                ocp_result = f"TRIPPED @ {ocp_current}A"
                ocp_tripped_at = ocp_current
                self.log(f"[{port_id}] eFuse 觸發成功！@ {ocp_current} A, V={v_ocp} V")
                break
            ocp_current += ocp_step

        vdrop_ocp = (v_idle - (v_ocp if v_ocp else 0)) * 1000.0 if v_idle > 0 else 0.0
        ocp_step_result = "PASS" if ocp_tripped_at is not None else "FAIL"
        if ocp_step_result == "FAIL":
            port_final_result = "FAIL"

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id,
            ocp_current if ocp_tripped_at else ocp_max,
            v_ocp if v_ocp else 0.0, 0.0, round(vdrop_ocp, 1),
            ocp_result, ocp_step_result, "PENDING"
        ])

        # eFuse recovery verification
        if ocp_tripped_at is not None and self.is_running:
            self.instr.setamp(0, rel=False)
            self.instr.setOFF()
            self.update_monitor(step_text="等待 eFuse 復歸...", target_a=0.0)
            messagebox.showinfo(
                "eFuse 復歸確認",
                f"eFuse 已成功觸發保護！\n請重新插拔 Type-C 端子以復歸 eFuse，完成後按下【確定】",
                parent=self.root
            )
            self.log(f"[{port_id}] 使用者已重新插拔，等待 1 秒後讀取復歸電壓...")
            time.sleep(1.0)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_recovery = self.instr.cmd_getvolt()
            if v_recovery is None:
                v_recovery = 0.0
            self.update_monitor(volt=v_recovery, curr=0.0)
            self.log(f"[{port_id}] 復歸電壓: {v_recovery} V")

            if v_recovery >= recovery_min:
                recovery_result = "PASS"
                self.log(f"[{port_id}] eFuse 復歸判定: PASS ({v_recovery} V >= {recovery_min} V)")
            else:
                recovery_result = "FAIL (NO_RECOVERY)"
                port_final_result = "FAIL"
                self.log(f"[{port_id}] eFuse 復歸判定: FAIL ({v_recovery} V < {recovery_min} V)")

            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
                v_recovery, 0.0, 0.0, "RECOVERY", recovery_result, "PENDING"
            ])

        # Final reset
        self.update_monitor(step_text="Finishing & Reset", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        time.sleep(0.5)

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
            0.0, 0.0, 0.0, "N/A", "DONE", port_final_result
        ])
        self.log(f"--- 連接埠 {port_id} 測試結束，結果: {port_final_result} ---")
        return port_final_result

    # ---------------- Battery Cycling Mode ----------------
    def run_battery_cycling(self, pcba_sn, jig_id):
        try:
            discharge_curr = float(self.bat_current_var.get())
            cutoff_v = float(self.bat_cutoff_v_var.get())
            overtemp_limit = float(self.bat_overtemp_var.get())
            rest_sec = int(self.bat_rest_time_var.get())
            max_cycles = int(self.bat_max_cycles_var.get())
            sampling_interval = float(self.config["BATTERY_CYCLE_MODE"].get("SAMPLING_INTERVAL_SEC", 1.0))
            if sampling_interval <= 0:
                raise ValueError
        except ValueError:
            self.log("Battery Cycling Mode 參數格式錯誤")
            return "FAIL"

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        ts_log_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"battery_cycle_{pcba_sn}_{timestamp_str}.csv"
        )

        try:
            with open(ts_log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Cycle_Index", "Phase", "Voltage_V",
                    "Current_A", "Power_W", "Temp_C", "Capacity_Ah", "Energy_Wh", "Status"
                ])
        except Exception as e:
            self.log(f"無法建立電池放電時間序列日誌: {e}")

        total_ah = 0.0
        total_wh = 0.0
        overall_status = "PASS"

        self.log(f"=== 開始電池放電容量與熱循環測試 ===")
        self.log(f"目標: {max_cycles} 輪次 | 電流: {discharge_curr}A | 截止: {cutoff_v}V | 過溫: {overtemp_limit}°C | 靜置: {rest_sec}s")

        for cycle_idx in range(1, max_cycles + 1):
            if not self.is_running:
                break

            cycle_str = f"Cycle {cycle_idx} / {max_cycles}"
            self.log(f"\n>>> 開始 {cycle_str} - 放電階段 (DISCHARGE) <<<")
            self.update_monitor(
                port="BATTERY",
                step_text=f"{cycle_str} - DISCHARGING",
                target_a=discharge_curr,
                ah=total_ah,
                wh=total_wh,
                cycle_str=cycle_str
            )

            # Enable DL24 load
            self.instr.setamp(discharge_curr, rel=False)
            time.sleep(0.5)
            self.instr.setON()

            last_time = time.monotonic()
            last_v, last_a = self.measure_stable()
            last_temp = self.get_temp_safe()
            last_p = last_v * last_a

            discharge_phase_active = True

            while discharge_phase_active and self.is_running:
                sample_deadline = last_time + sampling_interval
                time.sleep(max(0.0, sample_deadline - time.monotonic()))
                curr_time = time.monotonic()
                dt = curr_time - last_time

                v_k, a_k = self.measure_stable()
                temp_k = self.get_temp_safe()
                p_k = v_k * a_k

                # Trapezoidal integration for Ah & Wh
                delta_ah = ((a_k + last_a) / 2.0) * (dt / 3600.0)
                delta_wh = ((p_k + last_p) / 2.0) * (dt / 3600.0)
                total_ah += delta_ah
                total_wh += delta_wh

                self.update_monitor(
                    volt=v_k,
                    curr=a_k,
                    ah=total_ah,
                    wh=total_wh,
                    temp=temp_k,
                    cycle_str=cycle_str
                )

                now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Safety Check: Over-Temp Alarm
                if temp_k >= overtemp_limit:
                    self.log(f"⚠️ [過溫保護觸發] 溫度 {temp_k:.1f}°C 超過上限 {overtemp_limit}°C！緊急切斷負載！")
                    self.stop_load()
                    self.update_monitor(step_text="OVER_TEMP_ALARM")
                    overall_status = "FAIL (OVER_TEMP)"
                    self.append_ts_log(ts_log_file, [
                        now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3),
                        round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "OVER_TEMP_ALARM"
                    ])
                    discharge_phase_active = False
                    self.is_running = False
                    break

                # Termination Check: Cutoff Voltage
                if v_k <= cutoff_v:
                    self.log(f"✅ [截止電壓到達] 電壓 {v_k:.2f}V <= {cutoff_v}V，完成本輪放電。")
                    self.stop_load()
                    self.append_ts_log(ts_log_file, [
                        now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3),
                        round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "CUTOFF_REACHED"
                    ])
                    discharge_phase_active = False
                    break

                # Normal running log entry
                self.append_ts_log(ts_log_file, [
                    now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3),
                    round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "RUNNING"
                ])

                last_time, last_v, last_a, last_p, last_temp = curr_time, v_k, a_k, p_k, temp_k

            if not self.is_running or overall_status.startswith("FAIL"):
                break

            # Phase B: REST PHASE
            self.instr.setamp(0, rel=False)
            self.instr.setOFF()
            self.log(f">>> 進入 {cycle_str} - 靜置冷卻階段 (REST)，時長: {rest_sec} 秒 <<<")

            for sec in range(rest_sec, 0, -1):
                if not self.is_running:
                    break
                v_rest, a_rest = self.measure_stable()
                temp_rest = self.get_temp_safe()
                self.update_monitor(
                    step_text=f"{cycle_str} - RESTING ({sec}s)",
                    target_a=0.0,
                    volt=v_rest,
                    curr=a_rest,
                    temp=temp_rest
                )
                self.append_ts_log(ts_log_file, [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    cycle_idx, "REST", round(v_rest, 3), round(a_rest, 3),
                    0.0, round(temp_rest, 1), round(total_ah, 4), round(total_wh, 4), "RESTING"
                ])
                time.sleep(1.0)

        # Final Cleanup & Logging
        self.stop_load()

        self.log(f"\n=== 電池放電熱循環測試結束 ===")
        self.log(f"總累計放電容量: {total_ah:.4f} Ah | 總能量: {total_wh:.4f} Wh | 結果: {overall_status}")

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "Battery Cycling Mode", "BATTERY", discharge_curr,
            0.0, 0.0, 0.0, f"Ah={total_ah:.4f},Wh={total_wh:.4f}", overall_status, overall_status
        ])

        return overall_status

    def append_ts_log(self, filepath, row):
        try:
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(row)
        except Exception as e:
            self.log(f"時間序列 Log 寫入失敗: {e}")

    def save_csv_row(self, row):
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production_test_datalog.csv")
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(CSV_HEADER)
                writer.writerow(row)
        except Exception as e:
            self.log(f"CSV寫入失敗: {e}")

    def finish_test(self, final_result):
        self.is_running = False
        self.set_ui_state(False)
        self.update_monitor(step_text="COMPLETE")
        if final_result in ["PASS", "COMPLETE"]:
            self.set_big_status("PASS", "lime")
        elif final_result == "BORDERLINE":
            self.set_big_status("BORDERLINE", "yellow")
        else:
            self.set_big_status("FAIL", "red")
        self.log("\n測試序列完成。")
        if self.autofocus_var.get():
            self.pcba_sn_entry.delete(0, tk.END)
            self.pcba_sn_entry.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = DL24AutoTestApp(root)
    root.mainloop()
</file>

<file path="dl24_autotest_05_battery_cycling.py">
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import csv
import json
from datetime import datetime
import os
import sys

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from dl24_lib import Instr_Atorch, LowLevelSerPort
except ImportError:
    # Dummy fallback class for environments without physical hardware/dl24_lib installed
    class LowLevelSerPort:
        def __init__(self, port, baud):
            pass

    class Instr_Atorch:
        def __init__(self):
            self.v = 5.0
            self.a = 0.0
            self.temp = 28.5
            self.is_on = False

        def initport(self, port):
            pass

        def connect(self):
            pass

        def close(self):
            pass

        def recvdata(self):
            pass

        def cmd_resetcounters(self):
            pass

        def cmd_getvolt(self):
            return self.v if self.is_on else 5.05

        def cmd_getamp(self):
            return self.a if self.is_on else 0.0

        def cmd_gettemp(self):
            return self.temp

        def setamp(self, amp, rel=False):
            self.a = amp

        def setON(self):
            self.is_on = True

        def setOFF(self):
            self.is_on = False

MODES = ["SKYFALL JIG Mode", "FA Direct Mode", "Battery Cycling Mode"]
ALL_PORTS = ["TBTB", "TBTC", "TBTD"]
CSV_HEADER = [
    "Timestamp", "PCBA_SN", "JIG_ID", "Test_Mode", "Port_ID",
    "Step_Current_A", "Measured_Volt_V", "Measured_Curr_A", "Vdrop_mV",
    "OCP_Status", "Step_Result", "Final_Port_Result"
]
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_config.json")

DEFAULT_CONFIG = {
    "SKYFALL_JIG_MODE": {
        "STEPS": [1.5, 2.5, 3.0],
        "STEP_DURATION_SEC": 5,
        "V3_0A_PASS_MIN": 4.52,
        "V3_0A_BORDERLINE_MIN": 4.47,
        "OCP_START_CURRENT": 3.5,
        "OCP_MAX_CURRENT": 4.0,
        "OCP_STEP_CURRENT": 0.1,
        "OCP_TRIP_MAX_VOLT": 1.0,
        "RECOVERY_MIN_VOLT": 4.75
    },
    "FA_DIRECT_MODE": {
        "DEFAULT_CURRENT": 1.0,
        "DEFAULT_DURATION": 5,
        "DEFAULT_VMIN": 4.75,
        "DEFAULT_VMAX": 5.25
    },
    "BATTERY_CYCLE_MODE": {
        "DEFAULT_MODE": "CC",
        "DISCHARGE_CURRENT_A": 2.0,
        "CUTOFF_VOLTAGE_V": 3.0,
        "OVER_TEMP_LIMIT_C": 55.0,
        "REST_TIME_SEC": 900,
        "SAMPLING_INTERVAL_SEC": 1.0
    }
}


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            battery_defaults = DEFAULT_CONFIG["BATTERY_CYCLE_MODE"]
            battery_cfg = cfg.setdefault("BATTERY_CYCLE_MODE", {})
            for key, value in battery_defaults.items():
                battery_cfg.setdefault(key, value)
            return cfg
    except Exception:
        return DEFAULT_CONFIG


class DL24AutoTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DL24 生產線自動化與電池放電測試工具 v5.0")
        self.root.geometry("1120x820")
        self.root.resizable(False, False)
        self.is_running = False
        self.instr = None
        self.load_stop_lock = threading.Lock()
        self.last_comm_timestamp = time.monotonic()
        self.comm_failure_since = None
        self.current_ts_log_file = None
        self.config = load_config()
        self.setup_ui()
        self.root.after(100, self.auto_detect_dl24_port)

    def setup_ui(self):
        ttk.Style().theme_use('clam')

        left_panel = ttk.Frame(self.root, width=510)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Notebook tabs
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill=tk.X, pady=(0, 5))

        skyfall_tab = ttk.Frame(self.notebook)
        fa_tab = ttk.Frame(self.notebook)
        bat_tab = ttk.Frame(self.notebook)

        self.notebook.add(skyfall_tab, text="SKYFALL JIG Mode")
        self.notebook.add(fa_tab, text="FA Direct Mode")
        self.notebook.add(bat_tab, text="Battery Cycling Mode")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # ---------------- SKYFALL Tab Info ----------------
        skyfall_info = ttk.LabelFrame(skyfall_tab, text="SKYFALL JIG 自動化量產參數", padding=(10, 8))
        skyfall_info.pack(fill=tk.X, padx=5, pady=8)
        ttk.Label(skyfall_info, text="抽載步階: 1.5A -> 2.5A -> 3.0A -> 動態 OCP", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(skyfall_info, text="3.0A PASS 門檻: >= 4.52V | 復歸判定: >= 4.75V", font=("Arial", 10)).pack(anchor=tk.W, pady=2)

        # ---------------- FA Direct Mode Tab Profile ----------------
        fa_cfg = self.config["FA_DIRECT_MODE"]
        fa_profile = ttk.LabelFrame(fa_tab, text="FA 單點測試參數 (Test Profile)", padding=(10, 8))
        fa_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(fa_profile, text="Current (A):", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_current_var = tk.StringVar(value=str(fa_cfg["DEFAULT_CURRENT"]))
        ttk.Entry(fa_profile, textvariable=self.fa_current_var, width=10, font=("Arial", 11)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Duration (Sec):", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_duration_var = tk.StringVar(value=str(fa_cfg["DEFAULT_DURATION"]))
        ttk.Entry(fa_profile, textvariable=self.fa_duration_var, width=10, font=("Arial", 11)).grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmin (V):", font=("Arial", 11)).grid(row=2, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmin_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMIN"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmin_var, width=10, font=("Arial", 11)).grid(row=2, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmax (V):", font=("Arial", 11)).grid(row=3, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmax_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMAX"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmax_var, width=10, font=("Arial", 11)).grid(row=3, column=1, padx=5, pady=4)

        # ---------------- Battery Cycling Mode Tab Profile ----------------
        bat_cfg = self.config["BATTERY_CYCLE_MODE"]
        bat_profile = ttk.LabelFrame(bat_tab, text="電池放電容量與熱循環參數", padding=(10, 8))
        bat_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(bat_profile, text="Discharge Current (A):", font=("Arial", 10)).grid(row=0, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_current_var = tk.StringVar(value=str(bat_cfg["DISCHARGE_CURRENT_A"]))
        ttk.Entry(bat_profile, textvariable=self.bat_current_var, width=10, font=("Arial", 10)).grid(row=0, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Cutoff Voltage (V):", font=("Arial", 10)).grid(row=1, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_cutoff_v_var = tk.StringVar(value=str(bat_cfg["CUTOFF_VOLTAGE_V"]))
        ttk.Entry(bat_profile, textvariable=self.bat_cutoff_v_var, width=10, font=("Arial", 10)).grid(row=1, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Over-Temp Limit (°C):", font=("Arial", 10)).grid(row=2, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_overtemp_var = tk.StringVar(value=str(bat_cfg["OVER_TEMP_LIMIT_C"]))
        ttk.Entry(bat_profile, textvariable=self.bat_overtemp_var, width=10, font=("Arial", 10)).grid(row=2, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Rest Duration (Sec):", font=("Arial", 10)).grid(row=3, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_rest_time_var = tk.StringVar(value=str(bat_cfg["REST_TIME_SEC"]))
        ttk.Entry(bat_profile, textvariable=self.bat_rest_time_var, width=10, font=("Arial", 10)).grid(row=3, column=1, padx=4, pady=3)

        # ---------------- Connection Settings ----------------
        conn_frame = ttk.LabelFrame(left_panel, text="連線設定 (Connection)", padding=(10, 8))
        conn_frame.pack(fill=tk.X, pady=4)

        ttk.Label(conn_frame, text="COM Port:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.port_var = tk.StringVar(value="COM3")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=12, font=("Arial", 10)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(conn_frame, text="Baud Rate:", font=("Arial", 10)).grid(row=0, column=2, padx=5, pady=4, sticky=tk.W)
        self.baud_var = tk.StringVar(value="9600")
        ttk.Entry(conn_frame, textvariable=self.baud_var, width=12, font=("Arial", 10)).grid(row=0, column=3, padx=5, pady=4)

        # ---------------- Traceability ----------------
        trace_frame = ttk.LabelFrame(left_panel, text="資料追蹤 (Traceability)", padding=(10, 8))
        trace_frame.pack(fill=tk.X, pady=4)

        ttk.Label(trace_frame, text="PCBA S/N:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.pcba_sn_var = tk.StringVar()
        self.pcba_sn_entry = ttk.Entry(trace_frame, textvariable=self.pcba_sn_var, width=25, font=("Arial", 11, "bold"))
        self.pcba_sn_entry.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(trace_frame, text="JIG ID:", font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.jig_id_var = tk.StringVar()
        self.jig_id_entry = ttk.Entry(trace_frame, textvariable=self.jig_id_var, width=25, font=("Arial", 11))
        self.jig_id_entry.grid(row=1, column=1, padx=5, pady=4)

        self.autofocus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trace_frame, text="測試完成後自動聚焦 PCBA S/N 欄位", variable=self.autofocus_var).grid(row=2, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)

        # ---------------- Port Selection ----------------
        self.port_frame = ttk.LabelFrame(left_panel, text="測試連接埠 (Ports)", padding=(10, 8))
        self.port_frame.pack(fill=tk.X, pady=4)

        self.port_mode_var = tk.StringVar(value="ALL")
        ttk.Radiobutton(self.port_frame, text="自動測試所有埠 (TBTB -> TBTC -> TBTD)", variable=self.port_mode_var, value="ALL").grid(row=0, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)
        ttk.Radiobutton(self.port_frame, text="單一埠測試:", variable=self.port_mode_var, value="SINGLE").grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)

        self.single_port_var = tk.StringVar(value="TBTB")
        self.single_port_cb = ttk.Combobox(self.port_frame, textvariable=self.single_port_var, values=ALL_PORTS, state="readonly", width=12, font=("Arial", 10))
        self.single_port_cb.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)

        # ---------------- Controls ----------------
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(control_frame, text="開始測試\n(START)", font=("Arial", 16, "bold"), bg="#4CAF50", fg="white", height=2, command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.stop_btn = tk.Button(control_frame, text="強制停止\n(STOP)", font=("Arial", 16, "bold"), bg="#F44336", fg="white", height=2, command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.load_chart_btn = ttk.Button(left_panel, text="載入歷史 CSV 繪圖 (Load Chart)", command=self.load_historical_chart)
        self.load_chart_btn.pack(fill=tk.X, padx=4, pady=(0, 6))

        # ---------------- Live Monitor (Right Panel) ----------------
        monitor_frame = ttk.LabelFrame(right_panel, text="即時監控 (Live Monitor)", padding=(15, 12))
        monitor_frame.pack(fill=tk.X, pady=(0, 8))

        info_frame = ttk.Frame(monitor_frame)
        info_frame.pack(fill=tk.X, pady=3)

        self.lbl_active_port = tk.Label(info_frame, text="---", font=("Arial", 18, "bold"), fg="blue")
        self.lbl_active_port.pack(side=tk.LEFT, padx=5)

        self.lbl_active_step = tk.Label(info_frame, text="準備中", font=("Arial", 16))
        self.lbl_active_step.pack(side=tk.LEFT, padx=15)

        self.lbl_target_curr = tk.Label(info_frame, text="Target: 0.0 A", font=("Arial", 14, "bold"), fg="darkorange")
        self.lbl_target_curr.pack(side=tk.RIGHT, padx=5)

        # Primary Volt / Curr Readings
        reading_frame = ttk.Frame(monitor_frame)
        reading_frame.pack(fill=tk.X, pady=6)

        v_frame = ttk.Frame(reading_frame)
        v_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(v_frame, text="Voltage (V)", font=("Arial", 12)).pack()
        self.lbl_volt = tk.Label(v_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_volt.pack()

        a_frame = ttk.Frame(reading_frame)
        a_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(a_frame, text="Current (A)", font=("Arial", 12)).pack()
        self.lbl_curr = tk.Label(a_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_curr.pack()

        # Dedicated Battery Cycling Indicators Panel
        bat_meter_frame = ttk.LabelFrame(monitor_frame, text="電池放電與熱數據 (Battery Cycling Metrics)", padding=(8, 6))
        bat_meter_frame.pack(fill=tk.X, pady=6)

        m1 = ttk.Frame(bat_meter_frame)
        m1.pack(fill=tk.X, pady=2)

        tk.Label(m1, text="Capacity (Ah):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_ah = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#1976D2")
        self.lbl_ah.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m1, text="Energy (Wh):", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_wh = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#388E3C")
        self.lbl_wh.grid(row=0, column=3, sticky=tk.W, padx=4)

        m2 = ttk.Frame(bat_meter_frame)
        m2.pack(fill=tk.X, pady=2)

        tk.Label(m2, text="Temp (°C):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_temp = tk.Label(m2, text="--.-", font=("Consolas", 12, "bold"), fg="#D32F2F")
        self.lbl_temp.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m2, text="Cycle Progress:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_cycle = tk.Label(m2, text="Single Discharge", font=("Consolas", 12, "bold"), fg="#7B1FA2")
        self.lbl_cycle.grid(row=0, column=3, sticky=tk.W, padx=4)

        # Big Result Banner
        self.result_label = tk.Label(monitor_frame, text="WAITING", font=("Arial", 28, "bold"), fg="white", bg="gray")
        self.result_label.pack(fill=tk.X, pady=8)

        # Logs Frame
        log_frame = ttk.LabelFrame(right_panel, text="測試日誌 (Logs)", padding=(5, 5))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, font=("Consolas", 10), state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def on_tab_changed(self, event):
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "FA Direct Mode":
            self.jig_id_var.set("DIRECT_NO_JIG")
            self.jig_id_entry.config(state=tk.DISABLED)
        elif mode == "Battery Cycling Mode":
            self.port_frame.pack_forget()
            if not self.jig_id_var.get() or self.jig_id_var.get() == "DIRECT_NO_JIG":
                self.jig_id_var.set("BATTERY_TEST")
            self.jig_id_entry.config(state=tk.NORMAL)
        else:
            if not self.port_frame.winfo_ismapped():
                self.port_frame.pack(fill=tk.X, pady=4, before=self.load_chart_btn)
            if self.jig_id_var.get() in ["DIRECT_NO_JIG", "BATTERY_TEST"]:
                self.jig_id_var.set("")
            self.jig_id_entry.config(state=tk.NORMAL)

    def auto_detect_dl24_port(self):
        if list_ports is None or serial is None:
            self.log("[Auto-Detect] pyserial 未安裝，請手動選擇 COM Port")
            return
        threading.Thread(target=self._auto_detect_worker, daemon=True).start()

    def _auto_detect_worker(self):
        try:
            ports = list(list_ports.comports())
            priority_words = ("CH340", "USB-SERIAL", "ATORCH")
            ports.sort(key=lambda item: 0 if any(word in (item.description or "").upper() for word in priority_words) else 1)
            ping = bytes([0xFF, 0x55, 0x11, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            for candidate in ports:
                try:
                    with serial.Serial(candidate.device, int(self.baud_var.get()), timeout=0.5) as port:
                        port.reset_input_buffer()
                        port.write(ping)
                        response = port.read(10)
                    if response.startswith(b"\xff\x55") or response.startswith(b"\xca\xcb"):
                        self.root.after(0, self.port_var.set, candidate.device)
                        self.root.after(0, self.log, f"[Auto-Detect] 發現 DL24: {candidate.device}")
                        return
                except Exception:
                    continue
        except Exception as error:
            self.root.after(0, self.log, f"[Auto-Detect] 掃描失敗: {error}")
            return
        self.root.after(0, self.log, "[Auto-Detect] 未發現 DL24，請手動選擇 COM Port")

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_monitor(self, port=None, step_text=None, volt=None, curr=None, target_a=None, ah=None, wh=None, temp=None, cycle_str=None):
        if port is not None:
            self.lbl_active_port.config(text=f"Port: {port}")
        if step_text is not None:
            self.lbl_active_step.config(text=step_text)
        if volt is not None:
            self.lbl_volt.config(text=f"{volt:.2f}")
        if curr is not None:
            self.lbl_curr.config(text=f"{curr:.2f}")
        if target_a is not None:
            self.lbl_target_curr.config(text=f"Target: {target_a:.1f} A")
        if ah is not None:
            self.lbl_ah.config(text=f"{ah:.4f}")
        if wh is not None:
            self.lbl_wh.config(text=f"{wh:.4f}")
        if temp is not None:
            self.lbl_temp.config(text=f"{temp:.1f}")
        if cycle_str is not None:
            self.lbl_cycle.config(text=cycle_str)
        self.root.update_idletasks()

    def set_ui_state(self, running):
        state = tk.DISABLED if running else tk.NORMAL
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if running else tk.DISABLED)
        self.pcba_sn_entry.config(state=state)
        self.single_port_cb.config(state=state)
        tab_idx = self.notebook.index(self.notebook.select())
        if not running and MODES[tab_idx] == "FA Direct Mode":
            self.jig_id_entry.config(state=tk.DISABLED)
        else:
            self.jig_id_entry.config(state=state)

    def set_big_status(self, text, bg_color):
        self.result_label.config(text=text, bg=bg_color, fg="white" if bg_color not in ["yellow", "lime"] else "black")
        self.root.update_idletasks()

    def get_temp_safe(self):
        if self.instr and hasattr(self.instr, "cmd_gettemp"):
            try:
                t = self.instr.cmd_gettemp()
                if t is not None:
                    self.last_comm_timestamp = time.monotonic()
                    return float(t)
            except Exception:
                pass
            self.mark_comm_failure()
        return 28.5  # Default ambient temperature fallback

    def communication_timed_out(self):
        if self.comm_failure_since is None:
            return False
        return time.monotonic() - self.comm_failure_since > 3.0

    def mark_comm_failure(self):
        if self.comm_failure_since is None:
            self.comm_failure_since = time.monotonic()

    def trigger_comm_timeout(self, filepath, cycle_idx, voltage=0.0, current=0.0, temp=0.0, capacity=0.0, energy=0.0):
        self.stop_load()
        self.is_running = False
        self.update_monitor(step_text="COMM_TIMEOUT")
        self.append_ts_log(filepath, [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cycle_idx, "DISCHARGE",
            round(voltage, 3), round(current, 3), round(voltage * current, 3),
            round(temp, 1), round(capacity, 4), round(energy, 4), "FAIL (COMM_TIMEOUT)"
        ])
        self.root.after(0, messagebox.showerror, "DL24 通訊安全警報", "⚠️ 通訊中斷！已觸發緊急安全切斷！")

    def start_test(self):
        pcba_sn = self.pcba_sn_var.get().strip()
        jig_id = self.jig_id_var.get().strip()
        if not pcba_sn:
            messagebox.showerror("錯誤", "請輸入 PCBA S/N")
            return
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "SKYFALL JIG Mode" and not jig_id:
            messagebox.showerror("錯誤", "請輸入 JIG ID")
            return
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "Baud Rate 格式錯誤")
            return
        self.is_running = True
        self.set_ui_state(True)
        self.set_big_status("TESTING", "blue")
        self.update_monitor("---", "Initializing...", 0.0, 0.0, 0.0, ah=0.0, wh=0.0, temp=25.0, cycle_str="Single Discharge")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log(f"=== 開始新測試: {mode} ===")
        threading.Thread(target=self.run_full_sequence, args=(port, baud, mode, pcba_sn, jig_id), daemon=True).start()

    def stop_test(self):
        self.log("收到停止指令，正在中斷測試並關閉負載...")
        self.is_running = False
        self.stop_load()

    def stop_load(self):
        with self.load_stop_lock:
            if not self.instr:
                return
            try:
                self.instr.setamp(0, rel=False)
            except Exception:
                pass
            try:
                self.instr.setOFF()
            except Exception:
                pass

    def run_full_sequence(self, com_port, baud, mode, pcba_sn, jig_id):
        final_result_overall = "PASS"
        self.instr = None
        try:
            self.log(f"嘗試連線至 {com_port} ({baud} bps)...")
            self.instr = Instr_Atorch()
            self.instr.initport(LowLevelSerPort(com_port, baud))
            self.instr.connect()
            self.log("串列埠已開啟，等待設備回應...")
            time.sleep(1.0)
            for _ in range(5):
                self.instr.recvdata()
                time.sleep(0.1)
            self.log("連線成功，重置計數器...")
            self.instr.cmd_resetcounters()
            time.sleep(0.5)
            test_v = self.instr.cmd_getvolt()
            if test_v is None:
                self.log("警告: 無法讀取電壓，請確認 DL24 已開機並連接正確 COM Port")
            else:
                self.log(f"通訊確認成功，目前電壓: {test_v} V")

            if mode == "FA Direct Mode":
                final_result_overall = self.run_fa_direct(pcba_sn, jig_id)
            elif mode == "Battery Cycling Mode":
                final_result_overall = self.run_battery_cycling(pcba_sn, jig_id)
            else:
                ports_to_test = ALL_PORTS if self.port_mode_var.get() == "ALL" else [self.single_port_var.get()]
                for i, p in enumerate(ports_to_test):
                    if not self.is_running:
                        break
                    if i > 0 and self.is_running:
                        self.set_big_status("WAITING", "orange")
                        self.update_monitor(p, "Waiting for cable change", 0.0, 0.0, 0.0)
                        response = messagebox.askokcancel("換線提示", f"Please move TBT5 0.8m cable to Port {p} and press [OK] to Continue...", parent=self.root)
                        if not response:
                            self.log("使用者取消後續測試。")
                            self.is_running = False
                            break
                        self.set_big_status("TESTING", "blue")
                    self.log(f"\n--- 準備測試連接埠: {p} ---")
                    port_result = self.run_skyfall_port(pcba_sn, jig_id, p)
                    if port_result == "FAIL":
                        final_result_overall = "FAIL"
                    elif port_result == "BORDERLINE" and final_result_overall == "PASS":
                        final_result_overall = "BORDERLINE"
        except Exception as e:
            self.log(f"發生錯誤: {str(e)}")
            final_result_overall = "FAIL"
        finally:
            if self.instr:
                try:
                    self.stop_load()
                    self.instr.close()
                except Exception:
                    pass
            self.root.after(0, self.finish_test, final_result_overall)

    def measure_stable(self, retries=3):
        v, a = 0.0, 0.0
        time.sleep(0.5)
        if self.instr:
            for _ in range(2):
                self.instr.recvdata()
                time.sleep(0.05)
            for _ in range(retries):
                if not self.is_running:
                    break
                v_tmp = self.instr.cmd_getvolt()
                if v_tmp is not None:
                    v = v_tmp
                a_tmp = self.instr.cmd_getamp()
                if a_tmp is not None:
                    a = a_tmp
                if v_tmp is None or a_tmp is None:
                    self.mark_comm_failure()
                else:
                    self.last_comm_timestamp = time.monotonic()
                    self.comm_failure_since = None
                time.sleep(0.05)
        return v, a

    # ---------------- FA Direct Mode ----------------
    def run_fa_direct(self, pcba_sn, jig_id):
        try:
            current = float(self.fa_current_var.get())
            duration = int(self.fa_duration_var.get())
            vmin = float(self.fa_vmin_var.get())
            vmax = float(self.fa_vmax_var.get())
        except ValueError:
            self.log("FA Direct Mode 參數格式錯誤")
            return "FAIL"

        self.update_monitor(port="DIRECT", step_text=f"Load {current}A", target_a=current)
        self.log(f"[FA] 設定電流 {current} A，持續 {duration} 秒")
        self.instr.setamp(current, rel=False)
        time.sleep(0.5)
        self.instr.setON()

        for i in range(duration):
            if not self.is_running:
                self.log("[FA] 使用者中斷測試")
                break
            self.log(f"[FA] 抽載中... 剩餘 {duration - i} 秒")
            time.sleep(1)

        v_meas, a_meas = self.measure_stable()
        self.update_monitor(volt=v_meas, curr=a_meas)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()

        if vmin <= v_meas <= vmax:
            step_result = "PASS"
        else:
            step_result = "FAIL"

        self.log(f"[FA] 測量: {v_meas} V, {a_meas} A -> {step_result}")
        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "FA Direct Mode", "DIRECT", current,
            v_meas, a_meas, 0.0, "N/A", step_result, step_result
        ])
        return step_result

    # ---------------- SKYFALL JIG Mode ----------------
    def run_skyfall_port(self, pcba_sn, jig_id, port_id):
        cfg = self.config["SKYFALL_JIG_MODE"]
        steps = cfg["STEPS"]
        step_dur = cfg["STEP_DURATION_SEC"]
        pass_min = cfg["V3_0A_PASS_MIN"]
        border_min = cfg["V3_0A_BORDERLINE_MIN"]
        ocp_start = cfg["OCP_START_CURRENT"]
        ocp_max = cfg["OCP_MAX_CURRENT"]
        ocp_step = cfg["OCP_STEP_CURRENT"]
        ocp_trip_v = cfg["OCP_TRIP_MAX_VOLT"]
        recovery_min = cfg["RECOVERY_MIN_VOLT"]

        port_final_result = "PASS"

        # Measure V_idle
        self.update_monitor(port=port_id, step_text="Measuring V_idle...", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        v_idle, _ = self.measure_stable()
        self.log(f"[{port_id}] 空載電壓 V_idle: {v_idle} V")
        self.update_monitor(volt=v_idle, curr=0.0)

        self.instr.setON()
        time.sleep(0.5)

        # Fixed current steps
        for step_a in steps:
            if not self.is_running:
                break
            self.log(f"[{port_id}] 執行電流步階: {step_a} A")
            self.update_monitor(step_text=f"Step {step_a}A", target_a=step_a)
            self.instr.setamp(step_a, rel=False)

            for _ in range(step_dur):
                if not self.is_running:
                    break
                time.sleep(1)

            v_meas, a_meas = self.measure_stable()
            self.update_monitor(volt=v_meas, curr=a_meas)
            vdrop_mv = (v_idle - v_meas) * 1000.0 if v_idle > 0 else 0.0
            step_result = "PASS"

            if step_a == 3.0:
                if v_meas >= pass_min:
                    step_result = "PASS"
                elif v_meas >= border_min:
                    step_result = "BORDERLINE"
                else:
                    step_result = "FAIL"
                self.log(f"   -> 3.0A 判定: {v_meas} V -> {step_result}")

            if step_result == "FAIL":
                port_final_result = "FAIL"
            elif step_result == "BORDERLINE" and port_final_result == "PASS":
                port_final_result = "BORDERLINE"

            self.log(f"   -> 測量: {v_meas} V, {a_meas} A, Vdrop: {vdrop_mv:.1f} mV")
            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, step_a,
                v_meas, a_meas, round(vdrop_mv, 1), "N/A", step_result, "PENDING"
            ])

        if not self.is_running:
            return port_final_result

        # Dynamic OCP ramp
        self.log(f"[{port_id}] 開始 OCP 動態爬升測試 ({ocp_start}A -> {ocp_max}A)")
        ocp_result = "FAIL (NO_TRIP)"
        ocp_tripped_at = None
        ocp_current = ocp_start

        while ocp_current <= ocp_max + 0.001 and self.is_running:
            ocp_current = round(ocp_current, 2)
            self.log(f"[{port_id}] OCP 測試電流: {ocp_current} A")
            self.update_monitor(step_text=f"OCP {ocp_current}A", target_a=ocp_current)
            self.instr.setamp(ocp_current, rel=False)
            time.sleep(1.5)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_ocp = self.instr.cmd_getvolt()
            if v_ocp is None:
                v_ocp = 0.0
            self.update_monitor(volt=v_ocp)
            self.log(f"   -> OCP 電壓: {v_ocp} V")

            if v_ocp <= ocp_trip_v:
                ocp_result = f"TRIPPED @ {ocp_current}A"
                ocp_tripped_at = ocp_current
                self.log(f"[{port_id}] eFuse 觸發成功！@ {ocp_current} A, V={v_ocp} V")
                break
            ocp_current += ocp_step

        vdrop_ocp = (v_idle - (v_ocp if v_ocp else 0)) * 1000.0 if v_idle > 0 else 0.0
        ocp_step_result = "PASS" if ocp_tripped_at is not None else "FAIL"
        if ocp_step_result == "FAIL":
            port_final_result = "FAIL"

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id,
            ocp_current if ocp_tripped_at else ocp_max,
            v_ocp if v_ocp else 0.0, 0.0, round(vdrop_ocp, 1),
            ocp_result, ocp_step_result, "PENDING"
        ])

        # eFuse recovery verification
        if ocp_tripped_at is not None and self.is_running:
            self.instr.setamp(0, rel=False)
            self.instr.setOFF()
            self.update_monitor(step_text="等待 eFuse 復歸...", target_a=0.0)
            messagebox.showinfo(
                "eFuse 復歸確認",
                f"eFuse 已成功觸發保護！\n請重新插拔 Type-C 端子以復歸 eFuse，完成後按下【確定】",
                parent=self.root
            )
            self.log(f"[{port_id}] 使用者已重新插拔，等待 1 秒後讀取復歸電壓...")
            time.sleep(1.0)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_recovery = self.instr.cmd_getvolt()
            if v_recovery is None:
                v_recovery = 0.0
            self.update_monitor(volt=v_recovery, curr=0.0)
            self.log(f"[{port_id}] 復歸電壓: {v_recovery} V")

            if v_recovery >= recovery_min:
                recovery_result = "PASS"
                self.log(f"[{port_id}] eFuse 復歸判定: PASS ({v_recovery} V >= {recovery_min} V)")
            else:
                recovery_result = "FAIL (NO_RECOVERY)"
                port_final_result = "FAIL"
                self.log(f"[{port_id}] eFuse 復歸判定: FAIL ({v_recovery} V < {recovery_min} V)")

            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
                v_recovery, 0.0, 0.0, "RECOVERY", recovery_result, "PENDING"
            ])

        # Final reset
        self.update_monitor(step_text="Finishing & Reset", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        time.sleep(0.5)

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
            0.0, 0.0, 0.0, "N/A", "DONE", port_final_result
        ])
        self.log(f"--- 連接埠 {port_id} 測試結束，結果: {port_final_result} ---")
        return port_final_result

    def load_historical_chart(self):
        csv_file = filedialog.askopenfilename(
            title="選擇電池循環 CSV",
            filetypes=[("CSV Files", "*.csv")]
        )
        if csv_file:
            threading.Thread(target=self.generate_discharge_chart, args=(csv_file,), daemon=True).start()

    def generate_discharge_chart(self, csv_file_path):
        if plt is None:
            self.root.after(0, self.log, "[Chart] matplotlib 未安裝，無法產生圖表")
            return None
        try:
            with open(csv_file_path, newline='', encoding='utf-8') as csv_file:
                rows = list(csv.DictReader(csv_file))
            if not rows:
                raise ValueError("CSV 沒有資料")

            timestamps = [datetime.strptime(row["Timestamp"], '%Y-%m-%d %H:%M:%S') for row in rows]
            elapsed = [(stamp - timestamps[0]).total_seconds() / 60.0 for stamp in timestamps]
            voltage = [float(row["Voltage_V"]) for row in rows]
            current = [float(row["Current_A"]) for row in rows]
            capacity = [float(row["Capacity_Ah"]) for row in rows]
            energy = [float(row["Energy_Wh"]) for row in rows]
            temperature = [float(row["Temp_C"]) for row in rows]
            phase_values = [1 if row["Phase"] == "DISCHARGE" else 0 for row in rows]

            figure, top_axis = plt.subplots(2, 1, figsize=(11, 8), dpi=150, sharex=True)
            current_axis = top_axis[0].twinx()
            top_axis[0].plot(elapsed, voltage, color="blue", label="Voltage (V)")
            current_axis.plot(elapsed, current, color="orangered", linestyle="--", label="Current (A)")
            current_axis.plot(elapsed, capacity, color="green", label="Capacity (Ah)")
            top_axis[0].set_ylabel("Voltage (V)", color="blue")
            current_axis.set_ylabel("Current / Capacity")
            top_axis[0].set_title("DL24 Battery Discharge Curve")
            top_axis[0].grid(True, alpha=0.25)

            bottom_axis = top_axis[1]
            phase_axis = bottom_axis.twinx()
            bottom_axis.plot(elapsed, temperature, color="red", label="Temperature (C)")
            phase_axis.step(elapsed, phase_values, color="gray", alpha=0.6, where="post", label="Phase")
            bottom_axis.set_ylabel("Temperature (C)")
            phase_axis.set_ylabel("DISCHARGE / REST")
            phase_axis.set_yticks([0, 1], ["REST", "DISCHARGE"])
            bottom_axis.set_xlabel("Elapsed Time (minutes)")
            bottom_axis.grid(True, alpha=0.25)

            top_axis[0].annotate(f"Initial {voltage[0]:.2f} V", (elapsed[0], voltage[0]))
            cutoff_index = next((index for index, row in enumerate(rows) if "CUTOFF" in row["Status"]), None)
            if cutoff_index is not None:
                top_axis[0].annotate("Cutoff", (elapsed[cutoff_index], voltage[cutoff_index]))
            bottom_axis.annotate(f"Peak {max(temperature):.1f} C", (elapsed[temperature.index(max(temperature))], max(temperature)))
            top_axis[0].text(0.99, 0.95, f"Final: {capacity[-1]:.4f} Ah / {energy[-1]:.4f} Wh", transform=top_axis[0].transAxes, ha="right", va="top")
            figure.tight_layout()
            output_path = os.path.splitext(csv_file_path)[0] + ".png"
            figure.savefig(output_path)
            plt.close("all")
            self.root.after(0, self.log, f"[Chart] 圖表已儲存: {output_path}")
            return output_path
        except Exception as error:
            plt.close("all")
            self.root.after(0, self.log, f"[Chart] 繪圖失敗: {error}")
            return None

    # ---------------- Battery Cycling Mode ----------------
    def run_battery_cycling(self, pcba_sn, jig_id):
        try:
            discharge_curr = float(self.bat_current_var.get())
            cutoff_v = float(self.bat_cutoff_v_var.get())
            overtemp_limit = float(self.bat_overtemp_var.get())
            rest_sec = int(self.bat_rest_time_var.get())
            sampling_interval = float(self.config["BATTERY_CYCLE_MODE"].get("SAMPLING_INTERVAL_SEC", 1.0))
            if sampling_interval <= 0 or rest_sec < 0:
                raise ValueError
        except ValueError:
            self.log("Battery Cycling Mode 參數格式錯誤")
            return "FAIL"

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        ts_log_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"battery_cycle_{pcba_sn}_{timestamp_str}.csv"
        )
        self.current_ts_log_file = ts_log_file

        try:
            with open(ts_log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Cycle_Index", "Phase", "Voltage_V",
                    "Current_A", "Power_W", "Temp_C", "Capacity_Ah", "Energy_Wh", "Status"
                ])
        except Exception as e:
            self.log(f"無法建立電池放電時間序列日誌: {e}")

        total_ah = 0.0
        total_wh = 0.0
        overall_status = "PASS"
        cycle_idx = 1
        self.last_comm_timestamp = time.monotonic()
        self.comm_failure_since = None

        self.log(f"=== 開始電池放電容量與熱循環測試 ===")
        self.log(f"單次放電 | 電流: {discharge_curr}A | 截止: {cutoff_v}V | 過溫: {overtemp_limit}°C | 靜置: {rest_sec}s")
        self.update_monitor(port="BATTERY", step_text="DISCHARGING", target_a=discharge_curr, ah=0.0, wh=0.0, cycle_str="Single Discharge")

        try:
            self.instr.setamp(discharge_curr, rel=False)
            time.sleep(0.5)
            self.instr.setON()
            last_time = time.monotonic()
            last_v, last_a = self.measure_stable()
            last_p = last_v * last_a

            while self.is_running:
                sample_deadline = last_time + sampling_interval
                time.sleep(max(0.0, sample_deadline - time.monotonic()))
                curr_time = time.monotonic()
                v_k, a_k = self.measure_stable()
                temp_k = self.get_temp_safe()
                if self.communication_timed_out():
                    overall_status = "FAIL (COMM_TIMEOUT)"
                    self.trigger_comm_timeout(ts_log_file, cycle_idx, v_k, a_k, temp_k, total_ah, total_wh)
                    break

                dt = curr_time - last_time
                p_k = v_k * a_k
                total_ah += ((a_k + last_a) / 2.0) * (dt / 3600.0)
                total_wh += ((p_k + last_p) / 2.0) * (dt / 3600.0)
                self.update_monitor(volt=v_k, curr=a_k, ah=total_ah, wh=total_wh, temp=temp_k, cycle_str="Single Discharge")
                now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if temp_k >= overtemp_limit:
                    self.log(f"⚠️ [過溫保護觸發] 溫度 {temp_k:.1f}°C 超過上限 {overtemp_limit}°C！")
                    self.stop_load()
                    self.update_monitor(step_text="OVER_TEMP_ALARM")
                    overall_status = "FAIL (OVER_TEMP)"
                    self.append_ts_log(ts_log_file, [now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3), round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "OVER_TEMP_ALARM"])
                    self.is_running = False
                    break

                if v_k <= cutoff_v:
                    self.log(f"✅ [截止電壓到達] 電壓 {v_k:.2f}V <= {cutoff_v}V")
                    self.stop_load()
                    self.append_ts_log(ts_log_file, [now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3), round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "CUTOFF_REACHED"])
                    break

                self.append_ts_log(ts_log_file, [now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3), round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), "RUNNING"])
                last_time, last_a, last_p = curr_time, a_k, p_k

            if overall_status == "PASS" and self.is_running:
                self.stop_load()
                self.log(f">>> 進入靜置 OCV recovery 階段，時長: {rest_sec} 秒 <<<")
                for second in range(rest_sec):
                    if not self.is_running:
                        break
                    rest_deadline = time.monotonic() + sampling_interval
                    v_rest, a_rest = self.measure_stable()
                    temp_rest = self.get_temp_safe()
                    if self.communication_timed_out():
                        overall_status = "FAIL (COMM_TIMEOUT)"
                        self.trigger_comm_timeout(ts_log_file, cycle_idx, v_rest, a_rest, temp_rest, total_ah, total_wh)
                        break
                    self.update_monitor(step_text=f"RESTING OCV ({rest_sec - second}s)", target_a=0.0, volt=v_rest, curr=a_rest, temp=temp_rest)
                    self.append_ts_log(ts_log_file, [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cycle_idx, "REST", round(v_rest, 3), round(a_rest, 3), 0.0, round(temp_rest, 1), round(total_ah, 4), round(total_wh, 4), "REST_OCV_RECOVERY"])
                    time.sleep(max(0.0, rest_deadline - time.monotonic()))
        except Exception as error:
            overall_status = "FAIL"
            self.log(f"Battery Cycling 執行錯誤: {error}")
        finally:
            self.stop_load()

        # Final Cleanup & Logging
        self.stop_load()

        self.log(f"\n=== 電池放電熱循環測試結束 ===")
        self.log(f"總累計放電容量: {total_ah:.4f} Ah | 總能量: {total_wh:.4f} Wh | 結果: {overall_status}")

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "Battery Cycling Mode", "BATTERY", discharge_curr,
            0.0, 0.0, 0.0, f"Ah={total_ah:.4f},Wh={total_wh:.4f}", overall_status, overall_status
        ])

        self.generate_discharge_chart(ts_log_file)

        return overall_status

    def append_ts_log(self, filepath, row):
        try:
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(row)
        except Exception as e:
            self.log(f"時間序列 Log 寫入失敗: {e}")

    def save_csv_row(self, row):
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production_test_datalog.csv")
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(CSV_HEADER)
                writer.writerow(row)
        except Exception as e:
            self.log(f"CSV寫入失敗: {e}")

    def finish_test(self, final_result):
        self.is_running = False
        self.set_ui_state(False)
        self.update_monitor(step_text="COMPLETE")
        if final_result in ["PASS", "COMPLETE"]:
            self.set_big_status("PASS", "lime")
        elif final_result == "BORDERLINE":
            self.set_big_status("BORDERLINE", "yellow")
        else:
            self.set_big_status("FAIL", "red")
        self.log("\n測試序列完成。")
        if self.autofocus_var.get():
            self.pcba_sn_entry.delete(0, tk.END)
            self.pcba_sn_entry.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = DL24AutoTestApp(root)
    root.mainloop()
</file>

<file path="dl24_autotest_06_battery_cycling.py">
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import csv
import json
from datetime import datetime
import os
import sys
import platform
import subprocess
import atexit

if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from dl24_lib import Instr_Atorch, LowLevelSerPort
except ImportError:
    # Dummy fallback class for environments without physical hardware/dl24_lib installed
    class LowLevelSerPort:
        def __init__(self, port, baud):
            pass

    class Instr_Atorch:
        def __init__(self):
            self.v = 5.0
            self.a = 0.0
            self.temp = 28.5
            self.is_on = False

        def initport(self, port):
            pass

        def connect(self):
            pass

        def close(self):
            pass

        def recvdata(self):
            pass

        def cmd_resetcounters(self):
            pass

        def cmd_getvolt(self):
            return self.v if self.is_on else 5.05

        def cmd_getamp(self):
            return self.a if self.is_on else 0.0

        def cmd_gettemp(self):
            return self.temp

        def setamp(self, amp, rel=False):
            self.a = amp

        def setON(self):
            self.is_on = True

        def setOFF(self):
            self.is_on = False

def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()
CONFIG_FILE = os.path.join(APP_DIR, "test_config.json")
LOG_FILE = os.path.join(APP_DIR, "production_test_datalog.csv")
LOCK_FILE = os.path.join(APP_DIR, ".dl24_v6_instance.lock")
MODES = ["SKYFALL JIG Mode", "FA Direct Mode", "Battery Cycling Mode"]
ALL_PORTS = ["TBTB", "TBTC", "TBTD"]
CSV_HEADER = [
    "Timestamp", "PCBA_SN", "JIG_ID", "Test_Mode", "Port_ID",
    "Step_Current_A", "Measured_Volt_V", "Measured_Curr_A", "Vdrop_mV",
    "OCP_Status", "Step_Result", "Final_Port_Result", "DCIR_mOhm"
]
DEFAULT_CONFIG = {
    "SKYFALL_JIG_MODE": {
        "STEPS": [1.5, 2.5, 3.0],
        "STEP_DURATION_SEC": 5,
        "V3_0A_PASS_MIN": 4.52,
        "V3_0A_BORDERLINE_MIN": 4.47,
        "OCP_START_CURRENT": 3.5,
        "OCP_MAX_CURRENT": 4.0,
        "OCP_STEP_CURRENT": 0.1,
        "OCP_TRIP_MAX_VOLT": 1.0,
        "RECOVERY_MIN_VOLT": 4.75
    },
    "FA_DIRECT_MODE": {
        "DEFAULT_CURRENT": 1.0,
        "DEFAULT_DURATION": 5,
        "DEFAULT_VMIN": 4.75,
        "DEFAULT_VMAX": 5.25
    },
    "BATTERY_CYCLE_MODE": {
        "DEFAULT_MODE": "CC",
        "DISCHARGE_CURRENT_A": 2.0,
        "CUTOFF_VOLTAGE_V": 3.0,
        "OVER_TEMP_LIMIT_C": 55.0,
        "REST_TIME_SEC": 900,
        "SAMPLING_INTERVAL_SEC": 1.0,
        "DCIR_CALC_ENABLE": True
    }
}


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            battery_defaults = DEFAULT_CONFIG["BATTERY_CYCLE_MODE"]
            battery_cfg = cfg.setdefault("BATTERY_CYCLE_MODE", {})
            for key, value in battery_defaults.items():
                battery_cfg.setdefault(key, value)
                with open(CONFIG_FILE, 'w', encoding='utf-8') as config_file:
                    json.dump(cfg, config_file, indent=2)
            return cfg
    except Exception:
        return DEFAULT_CONFIG


def prevent_sleep():
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
        except Exception:
            pass


def allow_sleep():
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:
            pass


def acquire_instance_lock():
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "r", encoding="utf-8") as lock_file:
                pid = lock_file.read().strip()
            if pid:
                try:
                    os.kill(int(pid), 0)
                    return False
                except OSError:
                    pass
        with open(LOCK_FILE, "w", encoding="utf-8") as lock_file:
            lock_file.write(str(os.getpid()))
        atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))
        return True
    except Exception:
        return True


README_CONTENT = """# DL24 Production ATE v6.0

## Hardware
- Use 4-pin Kelvin sensing for DL24 load wiring.
- Place the NTC probe firmly on the battery cell or hottest expected surface.
- Install the CH340 USB serial driver when Windows does not enumerate the adapter.

## Configuration
`test_config.json` contains current, cutoff voltage, temperature, rest duration, sampling interval, and DCIR settings.

## Distribution
The application stores configuration and CSV/PNG logs beside the executable. PyInstaller `--onefile` and `--onedir` deployments are supported.
"""
RELEASE_NOTES_CONTENT = """# Release Notes

- v1.0: Race Lee's seven questions and JIG IR-drop production checks.
- v5.0: Single-pass battery discharge, OCV recovery, watchdog, and charts.
- v6.0: Battery DCIR, high-DPI responsive UI, connection menu, anti-sleep, single-instance lock, and deployment path anchoring.
"""


def ensure_documentation():
    for filename, content in (("README.md", README_CONTENT), ("RELEASE_NOTES.md", RELEASE_NOTES_CONTENT)):
        path = os.path.join(APP_DIR, filename)
        if not os.path.exists(path):
            try:
                with open(path, "w", encoding="utf-8") as doc_file:
                    doc_file.write(content)
            except OSError:
                pass


class DL24AutoTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DL24 Production Test & Battery Health ATE System v6.0")
        dpi = self.root.winfo_fpixels('1i')
        self.root.tk.call('tk', 'scaling', dpi / 96.0)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = int(screen_w * 0.65)
        win_h = int(screen_h * 0.80)
        self.root.geometry(f"{win_w}x{win_h}+{(screen_w - win_w) // 2}+{(screen_h - win_h) // 2}")
        self.root.minsize(1024, 700)
        self.root.resizable(True, True)
        self.is_running = False
        self.instr = None
        self.load_stop_lock = threading.Lock()
        self.last_comm_timestamp = time.monotonic()
        self.comm_failure_since = None
        self.current_ts_log_file = None
        self.port_var = tk.StringVar(value="COM3")
        self.baud_var = tk.StringVar(value="9600")
        self.dcir_var = tk.StringVar(value="0.000")
        self.config = load_config()
        prevent_sleep()
        ensure_documentation()
        self.create_menu()
        self.setup_ui()
        self.root.after(0, lambda: self.on_tab_changed(None))
        self.root.after(100, self.auto_detect_dl24_port)

    def setup_ui(self):
        ttk.Style().theme_use('clam')

        self.root.columnconfigure(0, weight=4)
        self.root.columnconfigure(1, weight=6)
        self.root.rowconfigure(0, weight=1)
        left_panel = ttk.Frame(self.root)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        right_panel = ttk.Frame(self.root)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Notebook tabs
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill=tk.X, pady=(0, 5))

        skyfall_tab = ttk.Frame(self.notebook)
        fa_tab = ttk.Frame(self.notebook)
        bat_tab = ttk.Frame(self.notebook)

        self.notebook.add(skyfall_tab, text="SKYFALL JIG Mode")
        self.notebook.add(fa_tab, text="FA Direct Mode")
        self.notebook.add(bat_tab, text="Battery Cycling Mode")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # ---------------- SKYFALL Tab Info ----------------
        skyfall_info = ttk.LabelFrame(skyfall_tab, text="SKYFALL JIG 自動化量產參數", padding=(10, 8))
        skyfall_info.pack(fill=tk.X, padx=5, pady=8)
        ttk.Label(skyfall_info, text="抽載步階: 1.5A -> 2.5A -> 3.0A -> 動態 OCP", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(skyfall_info, text="3.0A PASS 門檻: >= 4.52V | 復歸判定: >= 4.75V", font=("Arial", 10)).pack(anchor=tk.W, pady=2)

        # ---------------- FA Direct Mode Tab Profile ----------------
        fa_cfg = self.config["FA_DIRECT_MODE"]
        fa_profile = ttk.LabelFrame(fa_tab, text="FA 單點測試參數 (Test Profile)", padding=(10, 8))
        fa_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(fa_profile, text="Current (A):", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_current_var = tk.StringVar(value=str(fa_cfg["DEFAULT_CURRENT"]))
        ttk.Entry(fa_profile, textvariable=self.fa_current_var, width=10, font=("Arial", 11)).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Duration (Sec):", font=("Arial", 11)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_duration_var = tk.StringVar(value=str(fa_cfg["DEFAULT_DURATION"]))
        ttk.Entry(fa_profile, textvariable=self.fa_duration_var, width=10, font=("Arial", 11)).grid(row=1, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmin (V):", font=("Arial", 11)).grid(row=2, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmin_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMIN"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmin_var, width=10, font=("Arial", 11)).grid(row=2, column=1, padx=5, pady=4)

        ttk.Label(fa_profile, text="Vmax (V):", font=("Arial", 11)).grid(row=3, column=0, padx=5, pady=4, sticky=tk.W)
        self.fa_vmax_var = tk.StringVar(value=str(fa_cfg["DEFAULT_VMAX"]))
        ttk.Entry(fa_profile, textvariable=self.fa_vmax_var, width=10, font=("Arial", 11)).grid(row=3, column=1, padx=5, pady=4)

        # ---------------- Battery Cycling Mode Tab Profile ----------------
        bat_cfg = self.config["BATTERY_CYCLE_MODE"]
        bat_profile = ttk.LabelFrame(bat_tab, text="電池放電容量與熱循環參數", padding=(10, 8))
        bat_profile.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(bat_profile, text="Discharge Current (A):", font=("Arial", 10)).grid(row=0, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_current_var = tk.StringVar(value=str(bat_cfg["DISCHARGE_CURRENT_A"]))
        ttk.Entry(bat_profile, textvariable=self.bat_current_var, width=10, font=("Arial", 10)).grid(row=0, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Cutoff Voltage (V):", font=("Arial", 10)).grid(row=1, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_cutoff_v_var = tk.StringVar(value=str(bat_cfg["CUTOFF_VOLTAGE_V"]))
        ttk.Entry(bat_profile, textvariable=self.bat_cutoff_v_var, width=10, font=("Arial", 10)).grid(row=1, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Over-Temp Limit (°C):", font=("Arial", 10)).grid(row=2, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_overtemp_var = tk.StringVar(value=str(bat_cfg["OVER_TEMP_LIMIT_C"]))
        ttk.Entry(bat_profile, textvariable=self.bat_overtemp_var, width=10, font=("Arial", 10)).grid(row=2, column=1, padx=4, pady=3)

        ttk.Label(bat_profile, text="Rest Duration (Sec):", font=("Arial", 10)).grid(row=3, column=0, padx=4, pady=3, sticky=tk.W)
        self.bat_rest_time_var = tk.StringVar(value=str(bat_cfg["REST_TIME_SEC"]))
        ttk.Entry(bat_profile, textvariable=self.bat_rest_time_var, width=10, font=("Arial", 10)).grid(row=3, column=1, padx=4, pady=3)

        # ---------------- Traceability ----------------
        trace_frame = ttk.LabelFrame(left_panel, text="資料追蹤 (Traceability)", padding=(10, 8))
        trace_frame.pack(fill=tk.X, pady=4)

        ttk.Label(trace_frame, text="PCBA S/N:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        self.pcba_sn_var = tk.StringVar()
        self.pcba_sn_entry = ttk.Entry(trace_frame, textvariable=self.pcba_sn_var, width=25, font=("Arial", 11, "bold"))
        self.pcba_sn_entry.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(trace_frame, text="JIG ID:", font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        self.jig_id_var = tk.StringVar()
        self.jig_id_entry = ttk.Entry(trace_frame, textvariable=self.jig_id_var, width=25, font=("Arial", 11))
        self.jig_id_entry.grid(row=1, column=1, padx=5, pady=4)

        self.autofocus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trace_frame, text="測試完成後自動聚焦 PCBA S/N 欄位", variable=self.autofocus_var).grid(row=2, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)

        # ---------------- Port Selection ----------------
        self.port_frame = ttk.LabelFrame(left_panel, text="測試連接埠 (Ports)", padding=(10, 8))
        self.port_frame.pack(fill=tk.X, pady=4)

        self.port_mode_var = tk.StringVar(value="ALL")
        ttk.Radiobutton(self.port_frame, text="自動測試所有埠 (TBTB -> TBTC -> TBTD)", variable=self.port_mode_var, value="ALL").grid(row=0, column=0, columnspan=2, padx=5, pady=3, sticky=tk.W)
        ttk.Radiobutton(self.port_frame, text="單一埠測試:", variable=self.port_mode_var, value="SINGLE").grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)

        self.single_port_var = tk.StringVar(value="TBTB")
        self.single_port_cb = ttk.Combobox(self.port_frame, textvariable=self.single_port_var, values=ALL_PORTS, state="readonly", width=12, font=("Arial", 10))
        self.single_port_cb.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)

        # ---------------- Controls ----------------
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(control_frame, text="開始測試\n(START)", font=("Arial", 16, "bold"), bg="#4CAF50", fg="white", height=2, command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.stop_btn = tk.Button(control_frame, text="強制停止\n(STOP)", font=("Arial", 16, "bold"), bg="#F44336", fg="white", height=2, command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.load_chart_btn = ttk.Button(left_panel, text="載入歷史 CSV 繪圖 (Load Chart)", command=self.load_historical_chart)
        self.load_chart_btn.pack(fill=tk.X, padx=4, pady=(0, 6))

        # ---------------- Live Monitor (Right Panel) ----------------
        monitor_frame = ttk.LabelFrame(right_panel, text="即時監控 (Live Monitor)", padding=(15, 12))
        monitor_frame.pack(fill=tk.X, pady=(0, 8))

        info_frame = ttk.Frame(monitor_frame)
        info_frame.pack(fill=tk.X, pady=3)

        self.lbl_active_port = tk.Label(info_frame, text="---", font=("Arial", 18, "bold"), fg="blue")
        self.lbl_active_port.pack(side=tk.LEFT, padx=5)

        self.lbl_active_step = tk.Label(info_frame, text="準備中", font=("Arial", 16))
        self.lbl_active_step.pack(side=tk.LEFT, padx=15)

        self.lbl_target_curr = tk.Label(info_frame, text="Target: 0.0 A", font=("Arial", 14, "bold"), fg="darkorange")
        self.lbl_target_curr.pack(side=tk.RIGHT, padx=5)

        # Primary Volt / Curr Readings
        reading_frame = ttk.Frame(monitor_frame)
        reading_frame.pack(fill=tk.X, pady=6)

        v_frame = ttk.Frame(reading_frame)
        v_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(v_frame, text="Voltage (V)", font=("Arial", 12)).pack()
        self.lbl_volt = tk.Label(v_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_volt.pack()

        a_frame = ttk.Frame(reading_frame)
        a_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(a_frame, text="Current (A)", font=("Arial", 12)).pack()
        self.lbl_curr = tk.Label(a_frame, text="0.00", font=("Consolas", 36, "bold"), fg="black")
        self.lbl_curr.pack()

        # Dedicated Battery Cycling Indicators Panel
        bat_meter_frame = ttk.LabelFrame(monitor_frame, text="電池放電與熱數據 (Battery Cycling Metrics)", padding=(8, 6))
        bat_meter_frame.pack(fill=tk.X, pady=6)

        m1 = ttk.Frame(bat_meter_frame)
        m1.pack(fill=tk.X, pady=2)

        tk.Label(m1, text="Capacity (Ah):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_ah = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#1976D2")
        self.lbl_ah.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m1, text="Energy (Wh):", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_wh = tk.Label(m1, text="0.0000", font=("Consolas", 12, "bold"), fg="#388E3C")
        self.lbl_wh.grid(row=0, column=3, sticky=tk.W, padx=4)

        tk.Label(m1, text="DCIR (mΩ):", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, padx=4)
        self.lbl_dcir = tk.Label(m1, text="0.000", font=("Consolas", 12, "bold"), fg="#7B1FA2")
        self.lbl_dcir.grid(row=1, column=1, sticky=tk.W, padx=4)

        m2 = ttk.Frame(bat_meter_frame)
        m2.pack(fill=tk.X, pady=2)

        tk.Label(m2, text="Temp (°C):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.lbl_temp = tk.Label(m2, text="--.-", font=("Consolas", 12, "bold"), fg="#D32F2F")
        self.lbl_temp.grid(row=0, column=1, sticky=tk.W, padx=4)

        tk.Label(m2, text="Cycle Progress:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=12)
        self.lbl_cycle = tk.Label(m2, text="Single Discharge", font=("Consolas", 12, "bold"), fg="#7B1FA2")
        self.lbl_cycle.grid(row=0, column=3, sticky=tk.W, padx=4)

        # Big Result Banner
        self.result_label = tk.Label(monitor_frame, text="WAITING", font=("Arial", 28, "bold"), fg="white", bg="gray")
        self.result_label.pack(fill=tk.X, pady=8)

        # Logs Frame
        log_frame = ttk.LabelFrame(right_panel, text="測試日誌 (Logs)", padding=(5, 5))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, font=("Consolas", 10), state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        settings_menu = tk.Menu(menu_bar, tearoff=False)
        settings_menu.add_command(label="通訊設定 (Serial Connection)", command=self.open_connection_dialog)
        menu_bar.add_cascade(label="設定 (Settings)", menu=settings_menu)
        view_menu = tk.Menu(menu_bar, tearoff=False)
        view_menu.add_command(label="開啟 Log 資料夾 (Open Log Folder)", command=lambda: self.open_path(APP_DIR))
        view_menu.add_command(label="開啟 Data Log CSV (Open Data Log CSV)", command=lambda: self.open_path(LOG_FILE))
        menu_bar.add_cascade(label="檢視 (View)", menu=view_menu)
        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="關於 (About)", command=self.show_about)
        menu_bar.add_cascade(label="說明 (Help)", menu=help_menu)
        self.root.config(menu=menu_bar)

    def open_path(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as error:
            self.log(f"無法開啟路徑: {error}")

    def open_connection_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("通訊設定")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="COM Port:").grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)
        ttk.Entry(dialog, textvariable=self.port_var, width=16).grid(row=0, column=1, padx=10, pady=8)
        ttk.Label(dialog, text="Baud Rate:").grid(row=1, column=0, padx=10, pady=8, sticky=tk.W)
        ttk.Entry(dialog, textvariable=self.baud_var, width=16).grid(row=1, column=1, padx=10, pady=8)
        ttk.Button(dialog, text="重新自動掃描 DL24", command=self.auto_detect_dl24_port).grid(row=2, column=0, columnspan=2, padx=10, pady=8)
        ttk.Button(dialog, text="關閉", command=dialog.destroy).grid(row=3, column=0, columnspan=2, padx=10, pady=8)

    def show_about(self):
        messagebox.showinfo(
            "關於 DL24 ATE",
            "DL24 Production Test & Battery Health ATE System\n\n"
            "Version: v6.0\n"
            "Developer: Automated ATE Engineering Team\n\n"
            "Open-Source Reference: tshaddack/dl24\n"
            "Atorch DL24 Python Control, GitHub."
        )

    def on_tab_changed(self, event):
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "FA Direct Mode":
            self.jig_id_var.set("DIRECT_NO_JIG")
            self.jig_id_entry.config(state=tk.DISABLED)
        elif mode == "Battery Cycling Mode":
            self.port_frame.pack_forget()
            self.load_chart_btn.pack(fill=tk.X, padx=4, pady=(0, 6), before=self.notebook)
            if not self.jig_id_var.get() or self.jig_id_var.get() == "DIRECT_NO_JIG":
                self.jig_id_var.set("BATTERY_TEST")
            self.jig_id_entry.config(state=tk.NORMAL)
        else:
            if not self.port_frame.winfo_ismapped():
                self.port_frame.pack(fill=tk.X, pady=4, before=self.load_chart_btn)
            self.load_chart_btn.pack_forget()
            if self.jig_id_var.get() in ["DIRECT_NO_JIG", "BATTERY_TEST"]:
                self.jig_id_var.set("")
            self.jig_id_entry.config(state=tk.NORMAL)

    def auto_detect_dl24_port(self):
        if list_ports is None or serial is None:
            self.log("[Auto-Detect] pyserial 未安裝，請手動選擇 COM Port")
            return
        threading.Thread(target=self._auto_detect_worker, daemon=True).start()

    def _auto_detect_worker(self):
        try:
            ports = list(list_ports.comports())
            priority_words = ("CH340", "USB-SERIAL", "ATORCH")
            ports.sort(key=lambda item: 0 if any(word in (item.description or "").upper() for word in priority_words) else 1)
            ping = bytes([0xFF, 0x55, 0x11, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            for candidate in ports:
                try:
                    with serial.Serial(candidate.device, int(self.baud_var.get()), timeout=0.5) as port:
                        port.reset_input_buffer()
                        port.write(ping)
                        response = port.read(10)
                    if response.startswith(b"\xff\x55") or response.startswith(b"\xca\xcb"):
                        self.root.after(0, self.port_var.set, candidate.device)
                        self.root.after(0, self.log, f"[Auto-Detect] 發現 DL24: {candidate.device}")
                        return
                except Exception:
                    continue
        except Exception as error:
            self.root.after(0, self.log, f"[Auto-Detect] 掃描失敗: {error}")
            return
        self.root.after(0, self.log, "[Auto-Detect] 未發現 DL24，請手動選擇 COM Port")

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_monitor(self, port=None, step_text=None, volt=None, curr=None, target_a=None, ah=None, wh=None, temp=None, cycle_str=None, dcir=None):
        if port is not None:
            self.lbl_active_port.config(text=f"Port: {port}")
        if step_text is not None:
            self.lbl_active_step.config(text=step_text)
        if volt is not None:
            self.lbl_volt.config(text=f"{volt:.2f}")
        if curr is not None:
            self.lbl_curr.config(text=f"{curr:.2f}")
        if target_a is not None:
            self.lbl_target_curr.config(text=f"Target: {target_a:.1f} A")
        if ah is not None:
            self.lbl_ah.config(text=f"{ah:.4f}")
        if wh is not None:
            self.lbl_wh.config(text=f"{wh:.4f}")
        if temp is not None:
            self.lbl_temp.config(text=f"{temp:.1f}")
        if cycle_str is not None:
            self.lbl_cycle.config(text=cycle_str)
        if dcir is not None:
            self.lbl_dcir.config(text=f"{dcir:.3f}")
        self.root.update_idletasks()

    def set_ui_state(self, running):
        state = tk.DISABLED if running else tk.NORMAL
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if running else tk.DISABLED)
        self.pcba_sn_entry.config(state=state)
        self.single_port_cb.config(state=state)
        self.load_chart_btn.config(state=tk.DISABLED if running else tk.NORMAL)
        tab_idx = self.notebook.index(self.notebook.select())
        if not running and MODES[tab_idx] == "FA Direct Mode":
            self.jig_id_entry.config(state=tk.DISABLED)
        else:
            self.jig_id_entry.config(state=state)

    def set_big_status(self, text, bg_color):
        self.result_label.config(text=text, bg=bg_color, fg="white" if bg_color not in ["yellow", "lime"] else "black")
        self.root.update_idletasks()

    def get_temp_safe(self):
        if self.instr and hasattr(self.instr, "cmd_gettemp"):
            try:
                t = self.instr.cmd_gettemp()
                if t is not None:
                    self.last_comm_timestamp = time.monotonic()
                    return float(t)
            except Exception:
                pass
            self.mark_comm_failure()
        return 28.5  # Default ambient temperature fallback

    def communication_timed_out(self):
        if self.comm_failure_since is None:
            return False
        return time.monotonic() - self.comm_failure_since > 3.0

    def mark_comm_failure(self):
        if self.comm_failure_since is None:
            self.comm_failure_since = time.monotonic()

    def trigger_comm_timeout(self, filepath, cycle_idx, voltage=0.0, current=0.0, temp=0.0, capacity=0.0, energy=0.0):
        self.stop_load()
        self.is_running = False
        self.update_monitor(step_text="COMM_TIMEOUT")
        self.append_ts_log(filepath, [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cycle_idx, "DISCHARGE",
            round(voltage, 3), round(current, 3), round(voltage * current, 3),
            round(temp, 1), round(capacity, 4), round(energy, 4), "FAIL (COMM_TIMEOUT)"
        ])
        self.root.after(0, messagebox.showerror, "DL24 通訊安全警報", "⚠️ 通訊中斷！已觸發緊急安全切斷！")

    def start_test(self):
        pcba_sn = self.pcba_sn_var.get().strip()
        jig_id = self.jig_id_var.get().strip()
        if not pcba_sn:
            messagebox.showerror("錯誤", "請輸入 PCBA S/N")
            return
        tab_idx = self.notebook.index(self.notebook.select())
        mode = MODES[tab_idx]
        if mode == "SKYFALL JIG Mode" and not jig_id:
            messagebox.showerror("錯誤", "請輸入 JIG ID")
            return
        try:
            port = self.port_var.get()
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "Baud Rate 格式錯誤")
            return
        self.is_running = True
        self.set_ui_state(True)
        self.set_big_status("TESTING", "blue")
        self.update_monitor("---", "Initializing...", 0.0, 0.0, 0.0, ah=0.0, wh=0.0, temp=25.0, cycle_str="Single Discharge")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log(f"=== 開始新測試: {mode} ===")
        threading.Thread(target=self.run_full_sequence, args=(port, baud, mode, pcba_sn, jig_id), daemon=True).start()

    def stop_test(self):
        self.log("收到停止指令，正在中斷測試並關閉負載...")
        self.is_running = False
        self.stop_load()

    def stop_load(self):
        with self.load_stop_lock:
            if not self.instr:
                return
            try:
                self.instr.setamp(0, rel=False)
            except Exception:
                pass
            try:
                self.instr.setOFF()
            except Exception:
                pass

    def run_full_sequence(self, com_port, baud, mode, pcba_sn, jig_id):
        final_result_overall = "PASS"
        self.instr = None
        try:
            self.log(f"嘗試連線至 {com_port} ({baud} bps)...")
            self.instr = Instr_Atorch()
            self.instr.initport(LowLevelSerPort(com_port, baud))
            self.instr.connect()
            self.log("串列埠已開啟，等待設備回應...")
            time.sleep(1.0)
            for _ in range(5):
                self.instr.recvdata()
                time.sleep(0.1)
            self.log("連線成功，重置計數器...")
            self.instr.cmd_resetcounters()
            time.sleep(0.5)
            test_v = self.instr.cmd_getvolt()
            if test_v is None:
                self.log("警告: 無法讀取電壓，請確認 DL24 已開機並連接正確 COM Port")
            else:
                self.log(f"通訊確認成功，目前電壓: {test_v} V")

            if mode == "FA Direct Mode":
                final_result_overall = self.run_fa_direct(pcba_sn, jig_id)
            elif mode == "Battery Cycling Mode":
                final_result_overall = self.run_battery_cycling(pcba_sn, jig_id)
            else:
                ports_to_test = ALL_PORTS if self.port_mode_var.get() == "ALL" else [self.single_port_var.get()]
                for i, p in enumerate(ports_to_test):
                    if not self.is_running:
                        break
                    if i > 0 and self.is_running:
                        self.set_big_status("WAITING", "orange")
                        self.update_monitor(p, "Waiting for cable change", 0.0, 0.0, 0.0)
                        response = messagebox.askokcancel("換線提示", f"Please move TBT5 0.8m cable to Port {p} and press [OK] to Continue...", parent=self.root)
                        if not response:
                            self.log("使用者取消後續測試。")
                            self.is_running = False
                            break
                        self.set_big_status("TESTING", "blue")
                    self.log(f"\n--- 準備測試連接埠: {p} ---")
                    port_result = self.run_skyfall_port(pcba_sn, jig_id, p)
                    if port_result == "FAIL":
                        final_result_overall = "FAIL"
                    elif port_result == "BORDERLINE" and final_result_overall == "PASS":
                        final_result_overall = "BORDERLINE"
        except Exception as e:
            self.log(f"發生錯誤: {str(e)}")
            final_result_overall = "FAIL"
        finally:
            if self.instr:
                try:
                    self.stop_load()
                    self.instr.close()
                except Exception:
                    pass
            self.root.after(0, self.finish_test, final_result_overall)

    def measure_stable(self, retries=3):
        v, a = 0.0, 0.0
        time.sleep(0.5)
        if self.instr:
            for _ in range(2):
                self.instr.recvdata()
                time.sleep(0.05)
            for _ in range(retries):
                if not self.is_running:
                    break
                v_tmp = self.instr.cmd_getvolt()
                if v_tmp is not None:
                    v = v_tmp
                a_tmp = self.instr.cmd_getamp()
                if a_tmp is not None:
                    a = a_tmp
                if v_tmp is None or a_tmp is None:
                    self.mark_comm_failure()
                else:
                    self.last_comm_timestamp = time.monotonic()
                    self.comm_failure_since = None
                time.sleep(0.05)
        return v, a

    # ---------------- FA Direct Mode ----------------
    def run_fa_direct(self, pcba_sn, jig_id):
        try:
            current = float(self.fa_current_var.get())
            duration = int(self.fa_duration_var.get())
            vmin = float(self.fa_vmin_var.get())
            vmax = float(self.fa_vmax_var.get())
        except ValueError:
            self.log("FA Direct Mode 參數格式錯誤")
            return "FAIL"

        self.update_monitor(port="DIRECT", step_text=f"Load {current}A", target_a=current)
        self.log(f"[FA] 設定電流 {current} A，持續 {duration} 秒")
        self.instr.setamp(current, rel=False)
        time.sleep(0.5)
        self.instr.setON()

        for i in range(duration):
            if not self.is_running:
                self.log("[FA] 使用者中斷測試")
                break
            self.log(f"[FA] 抽載中... 剩餘 {duration - i} 秒")
            time.sleep(1)

        v_meas, a_meas = self.measure_stable()
        self.update_monitor(volt=v_meas, curr=a_meas)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()

        if vmin <= v_meas <= vmax:
            step_result = "PASS"
        else:
            step_result = "FAIL"

        self.log(f"[FA] 測量: {v_meas} V, {a_meas} A -> {step_result}")
        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "FA Direct Mode", "DIRECT", current,
            v_meas, a_meas, 0.0, "N/A", step_result, step_result, ""
        ])
        return step_result

    # ---------------- SKYFALL JIG Mode ----------------
    def run_skyfall_port(self, pcba_sn, jig_id, port_id):
        cfg = self.config["SKYFALL_JIG_MODE"]
        steps = cfg["STEPS"]
        step_dur = cfg["STEP_DURATION_SEC"]
        pass_min = cfg["V3_0A_PASS_MIN"]
        border_min = cfg["V3_0A_BORDERLINE_MIN"]
        ocp_start = cfg["OCP_START_CURRENT"]
        ocp_max = cfg["OCP_MAX_CURRENT"]
        ocp_step = cfg["OCP_STEP_CURRENT"]
        ocp_trip_v = cfg["OCP_TRIP_MAX_VOLT"]
        recovery_min = cfg["RECOVERY_MIN_VOLT"]

        port_final_result = "PASS"

        # Measure V_idle
        self.update_monitor(port=port_id, step_text="Measuring V_idle...", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        v_idle, _ = self.measure_stable()
        self.log(f"[{port_id}] 空載電壓 V_idle: {v_idle} V")
        self.update_monitor(volt=v_idle, curr=0.0)

        self.instr.setON()
        time.sleep(0.5)

        # Fixed current steps
        for step_a in steps:
            if not self.is_running:
                break
            self.log(f"[{port_id}] 執行電流步階: {step_a} A")
            self.update_monitor(step_text=f"Step {step_a}A", target_a=step_a)
            self.instr.setamp(step_a, rel=False)

            for _ in range(step_dur):
                if not self.is_running:
                    break
                time.sleep(1)

            v_meas, a_meas = self.measure_stable()
            self.update_monitor(volt=v_meas, curr=a_meas)
            vdrop_mv = (v_idle - v_meas) * 1000.0 if v_idle > 0 else 0.0
            step_result = "PASS"

            if step_a == 3.0:
                if v_meas >= pass_min:
                    step_result = "PASS"
                elif v_meas >= border_min:
                    step_result = "BORDERLINE"
                else:
                    step_result = "FAIL"
                self.log(f"   -> 3.0A 判定: {v_meas} V -> {step_result}")

            if step_result == "FAIL":
                port_final_result = "FAIL"
            elif step_result == "BORDERLINE" and port_final_result == "PASS":
                port_final_result = "BORDERLINE"

            self.log(f"   -> 測量: {v_meas} V, {a_meas} A, Vdrop: {vdrop_mv:.1f} mV")
            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, step_a,
                v_meas, a_meas, round(vdrop_mv, 1), "N/A", step_result, "PENDING", ""
            ])

        if not self.is_running:
            return port_final_result

        # Dynamic OCP ramp
        self.log(f"[{port_id}] 開始 OCP 動態爬升測試 ({ocp_start}A -> {ocp_max}A)")
        ocp_result = "FAIL (NO_TRIP)"
        ocp_tripped_at = None
        ocp_current = ocp_start

        while ocp_current <= ocp_max + 0.001 and self.is_running:
            ocp_current = round(ocp_current, 2)
            self.log(f"[{port_id}] OCP 測試電流: {ocp_current} A")
            self.update_monitor(step_text=f"OCP {ocp_current}A", target_a=ocp_current)
            self.instr.setamp(ocp_current, rel=False)
            time.sleep(1.5)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_ocp = self.instr.cmd_getvolt()
            if v_ocp is None:
                v_ocp = 0.0
            self.update_monitor(volt=v_ocp)
            self.log(f"   -> OCP 電壓: {v_ocp} V")

            if v_ocp <= ocp_trip_v:
                ocp_result = f"TRIPPED @ {ocp_current}A"
                ocp_tripped_at = ocp_current
                self.log(f"[{port_id}] eFuse 觸發成功！@ {ocp_current} A, V={v_ocp} V")
                break
            ocp_current += ocp_step

        vdrop_ocp = (v_idle - (v_ocp if v_ocp else 0)) * 1000.0 if v_idle > 0 else 0.0
        ocp_step_result = "PASS" if ocp_tripped_at is not None else "FAIL"
        if ocp_step_result == "FAIL":
            port_final_result = "FAIL"

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id,
            ocp_current if ocp_tripped_at else ocp_max,
            v_ocp if v_ocp else 0.0, 0.0, round(vdrop_ocp, 1),
            ocp_result, ocp_step_result, "PENDING", ""
        ])

        # eFuse recovery verification
        if ocp_tripped_at is not None and self.is_running:
            self.instr.setamp(0, rel=False)
            self.instr.setOFF()
            self.update_monitor(step_text="等待 eFuse 復歸...", target_a=0.0)
            messagebox.showinfo(
                "eFuse 復歸確認",
                f"eFuse 已成功觸發保護！\n請重新插拔 Type-C 端子以復歸 eFuse，完成後按下【確定】",
                parent=self.root
            )
            self.log(f"[{port_id}] 使用者已重新插拔，等待 1 秒後讀取復歸電壓...")
            time.sleep(1.0)
            for _ in range(3):
                self.instr.recvdata()
                time.sleep(0.1)
            v_recovery = self.instr.cmd_getvolt()
            if v_recovery is None:
                v_recovery = 0.0
            self.update_monitor(volt=v_recovery, curr=0.0)
            self.log(f"[{port_id}] 復歸電壓: {v_recovery} V")

            if v_recovery >= recovery_min:
                recovery_result = "PASS"
                self.log(f"[{port_id}] eFuse 復歸判定: PASS ({v_recovery} V >= {recovery_min} V)")
            else:
                recovery_result = "FAIL (NO_RECOVERY)"
                port_final_result = "FAIL"
                self.log(f"[{port_id}] eFuse 復歸判定: FAIL ({v_recovery} V < {recovery_min} V)")

            self.save_csv_row([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
                v_recovery, 0.0, 0.0, "RECOVERY", recovery_result, "PENDING", ""
            ])

        # Final reset
        self.update_monitor(step_text="Finishing & Reset", target_a=0.0)
        self.instr.setamp(0, rel=False)
        self.instr.setOFF()
        time.sleep(0.5)

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "SKYFALL JIG Mode", port_id, 0.0,
            0.0, 0.0, 0.0, "N/A", "DONE", port_final_result, ""
        ])
        self.log(f"--- 連接埠 {port_id} 測試結束，結果: {port_final_result} ---")
        return port_final_result

    def load_historical_chart(self):
        csv_file = filedialog.askopenfilename(
            title="選擇電池循環 CSV",
            filetypes=[("CSV Files", "*.csv")]
        )
        if csv_file:
            threading.Thread(target=self.generate_discharge_chart, args=(csv_file,), daemon=True).start()

    def generate_discharge_chart(self, csv_file_path):
        if plt is None:
            self.root.after(0, self.log, "[Chart] matplotlib 未安裝，無法產生圖表")
            return None
        try:
            with open(csv_file_path, newline='', encoding='utf-8') as csv_file:
                rows = list(csv.DictReader(csv_file))
            if not rows:
                raise ValueError("CSV 沒有資料")

            timestamps = [datetime.strptime(row["Timestamp"], '%Y-%m-%d %H:%M:%S') for row in rows]
            elapsed = [(stamp - timestamps[0]).total_seconds() / 60.0 for stamp in timestamps]
            voltage = [float(row["Voltage_V"]) for row in rows]
            current = [float(row["Current_A"]) for row in rows]
            capacity = [float(row["Capacity_Ah"]) for row in rows]
            energy = [float(row["Energy_Wh"]) for row in rows]
            temperature = [float(row["Temp_C"]) for row in rows]
            phase_values = [1 if row["Phase"] == "DISCHARGE" else 0 for row in rows]

            figure, top_axis = plt.subplots(2, 1, figsize=(11, 8), dpi=150, sharex=True)
            current_axis = top_axis[0].twinx()
            top_axis[0].plot(elapsed, voltage, color="blue", label="Voltage (V)")
            current_axis.plot(elapsed, current, color="orangered", linestyle="--", label="Current (A)")
            current_axis.plot(elapsed, capacity, color="green", label="Capacity (Ah)")
            top_axis[0].set_ylabel("Voltage (V)", color="blue")
            current_axis.set_ylabel("Current / Capacity")
            top_axis[0].set_title("DL24 Battery Discharge Curve")
            top_axis[0].grid(True, alpha=0.25)

            bottom_axis = top_axis[1]
            phase_axis = bottom_axis.twinx()
            bottom_axis.plot(elapsed, temperature, color="red", label="Temperature (C)")
            phase_axis.step(elapsed, phase_values, color="gray", alpha=0.6, where="post", label="Phase")
            bottom_axis.set_ylabel("Temperature (C)")
            phase_axis.set_ylabel("DISCHARGE / REST")
            phase_axis.set_yticks([0, 1], ["REST", "DISCHARGE"])
            bottom_axis.set_xlabel("Elapsed Time (minutes)")
            bottom_axis.grid(True, alpha=0.25)

            top_axis[0].annotate(f"Initial {voltage[0]:.2f} V", (elapsed[0], voltage[0]))
            cutoff_index = next((index for index, row in enumerate(rows) if "CUTOFF" in row["Status"]), None)
            if cutoff_index is not None:
                top_axis[0].annotate("Cutoff", (elapsed[cutoff_index], voltage[cutoff_index]))
            bottom_axis.annotate(f"Peak {max(temperature):.1f} C", (elapsed[temperature.index(max(temperature))], max(temperature)))
            top_axis[0].text(0.99, 0.95, f"Final: {capacity[-1]:.4f} Ah / {energy[-1]:.4f} Wh", transform=top_axis[0].transAxes, ha="right", va="top")
            figure.tight_layout()
            output_path = os.path.splitext(csv_file_path)[0] + ".png"
            figure.savefig(output_path)
            plt.close("all")
            self.root.after(0, self.log, f"[Chart] 圖表已儲存: {output_path}")
            return output_path
        except Exception as error:
            plt.close("all")
            self.root.after(0, self.log, f"[Chart] 繪圖失敗: {error}")
            return None

    # ---------------- Battery Cycling Mode ----------------
    def run_battery_cycling(self, pcba_sn, jig_id):
        try:
            discharge_curr = float(self.bat_current_var.get())
            cutoff_v = float(self.bat_cutoff_v_var.get())
            overtemp_limit = float(self.bat_overtemp_var.get())
            rest_sec = int(self.bat_rest_time_var.get())
            sampling_interval = float(self.config["BATTERY_CYCLE_MODE"].get("SAMPLING_INTERVAL_SEC", 1.0))
            if sampling_interval <= 0 or rest_sec < 0:
                raise ValueError
        except ValueError:
            self.log("Battery Cycling Mode 參數格式錯誤")
            return "FAIL"

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        ts_log_file = os.path.join(
            APP_DIR,
            f"battery_cycle_{pcba_sn}_{timestamp_str}.csv"
        )
        self.current_ts_log_file = ts_log_file

        try:
            with open(ts_log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Cycle_Index", "Phase", "Voltage_V",
                    "Current_A", "Power_W", "Temp_C", "Capacity_Ah", "Energy_Wh", "DCIR_mOhm", "Status"
                ])
        except Exception as e:
            self.log(f"無法建立電池放電時間序列日誌: {e}")

        total_ah = 0.0
        total_wh = 0.0
        overall_status = "PASS"
        cycle_idx = 1
        dcir_mohm = 0.0
        self.last_comm_timestamp = time.monotonic()
        self.comm_failure_since = None

        self.log(f"=== 開始電池放電容量與熱循環測試 ===")
        self.log(f"單次放電 | 電流: {discharge_curr}A | 截止: {cutoff_v}V | 過溫: {overtemp_limit}°C | 靜置: {rest_sec}s")
        self.update_monitor(port="BATTERY", step_text="DISCHARGING", target_a=discharge_curr, ah=0.0, wh=0.0, cycle_str="Single Discharge")

        try:
            ocv_voltage, _ = self.measure_stable()
            self.instr.setamp(discharge_curr, rel=False)
            time.sleep(0.5)
            self.instr.setON()
            time.sleep(0.5)
            last_time = time.monotonic()
            last_v, last_a = self.measure_stable()
            if self.config["BATTERY_CYCLE_MODE"].get("DCIR_CALC_ENABLE", True) and last_a > 0:
                dcir_mohm = max(0.0, (ocv_voltage - last_v) / last_a * 1000.0)
                self.dcir_var.set(f"{dcir_mohm:.3f}")
                self.update_monitor(dcir=dcir_mohm)
            last_p = last_v * last_a

            while self.is_running:
                sample_deadline = last_time + sampling_interval
                time.sleep(max(0.0, sample_deadline - time.monotonic()))
                curr_time = time.monotonic()
                v_k, a_k = self.measure_stable()
                temp_k = self.get_temp_safe()
                if self.communication_timed_out():
                    overall_status = "FAIL (COMM_TIMEOUT)"
                    self.trigger_comm_timeout(ts_log_file, cycle_idx, v_k, a_k, temp_k, total_ah, total_wh)
                    break

                dt = curr_time - last_time
                p_k = v_k * a_k
                total_ah += ((a_k + last_a) / 2.0) * (dt / 3600.0)
                total_wh += ((p_k + last_p) / 2.0) * (dt / 3600.0)
                self.update_monitor(volt=v_k, curr=a_k, ah=total_ah, wh=total_wh, temp=temp_k, cycle_str="Single Discharge")
                now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if temp_k >= overtemp_limit:
                    self.log(f"⚠️ [過溫保護觸發] 溫度 {temp_k:.1f}°C 超過上限 {overtemp_limit}°C！")
                    self.stop_load()
                    self.update_monitor(step_text="OVER_TEMP_ALARM")
                    overall_status = "FAIL (OVER_TEMP)"
                    self.append_ts_log(ts_log_file, [now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3), round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), round(dcir_mohm, 3), "OVER_TEMP_ALARM"])
                    self.is_running = False
                    break

                if v_k <= cutoff_v:
                    self.log(f"✅ [截止電壓到達] 電壓 {v_k:.2f}V <= {cutoff_v}V")
                    self.stop_load()
                    self.append_ts_log(ts_log_file, [now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3), round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), round(dcir_mohm, 3), "CUTOFF_REACHED"])
                    break

                self.append_ts_log(ts_log_file, [now_ts, cycle_idx, "DISCHARGE", round(v_k, 3), round(a_k, 3), round(p_k, 3), round(temp_k, 1), round(total_ah, 4), round(total_wh, 4), round(dcir_mohm, 3), "RUNNING"])
                last_time, last_a, last_p = curr_time, a_k, p_k

            if overall_status == "PASS" and self.is_running:
                self.stop_load()
                self.log(f">>> 進入靜置 OCV recovery 階段，時長: {rest_sec} 秒 <<<")
                for second in range(rest_sec):
                    if not self.is_running:
                        break
                    rest_deadline = time.monotonic() + sampling_interval
                    v_rest, a_rest = self.measure_stable()
                    temp_rest = self.get_temp_safe()
                    if self.communication_timed_out():
                        overall_status = "FAIL (COMM_TIMEOUT)"
                        self.trigger_comm_timeout(ts_log_file, cycle_idx, v_rest, a_rest, temp_rest, total_ah, total_wh)
                        break
                    self.update_monitor(step_text=f"RESTING OCV ({rest_sec - second}s)", target_a=0.0, volt=v_rest, curr=a_rest, temp=temp_rest)
                    self.append_ts_log(ts_log_file, [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cycle_idx, "REST", round(v_rest, 3), round(a_rest, 3), 0.0, round(temp_rest, 1), round(total_ah, 4), round(total_wh, 4), round(dcir_mohm, 3), "REST_OCV_RECOVERY"])
                    time.sleep(max(0.0, rest_deadline - time.monotonic()))
        except Exception as error:
            overall_status = "FAIL"
            self.log(f"Battery Cycling 執行錯誤: {error}")
        finally:
            self.stop_load()

        # Final Cleanup & Logging
        self.stop_load()

        self.log(f"\n=== 電池放電熱循環測試結束 ===")
        self.log(f"總累計放電容量: {total_ah:.4f} Ah | 總能量: {total_wh:.4f} Wh | 結果: {overall_status}")

        self.save_csv_row([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            pcba_sn, jig_id, "Battery Cycling Mode", "BATTERY", discharge_curr,
            0.0, 0.0, 0.0, f"Ah={total_ah:.4f},Wh={total_wh:.4f}", overall_status, overall_status, round(dcir_mohm, 3)
        ])

        self.generate_discharge_chart(ts_log_file)

        return overall_status

    def append_ts_log(self, filepath, row):
        try:
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(row)
        except Exception as e:
            self.log(f"時間序列 Log 寫入失敗: {e}")

    def save_csv_row(self, row):
        filename = LOG_FILE
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(CSV_HEADER)
                writer.writerow(row)
        except Exception as e:
            self.log(f"CSV寫入失敗: {e}")

    def finish_test(self, final_result):
        self.is_running = False
        self.set_ui_state(False)
        self.update_monitor(step_text="COMPLETE")
        if final_result in ["PASS", "COMPLETE"]:
            self.set_big_status("PASS", "lime")
        elif final_result == "BORDERLINE":
            self.set_big_status("BORDERLINE", "yellow")
        else:
            self.set_big_status("FAIL", "red")
        self.log("\n測試序列完成。")
        if self.autofocus_var.get():
            self.pcba_sn_entry.delete(0, tk.END)
            self.pcba_sn_entry.focus_set()


if __name__ == "__main__":
    if not acquire_instance_lock():
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("DL24 v6", "已有另一個 DL24 v6 實例正在執行。")
        root.destroy()
        sys.exit(1)
    root = tk.Tk()
    try:
        app = DL24AutoTestApp(root)
        root.protocol("WM_DELETE_WINDOW", lambda: (allow_sleep(), root.destroy()))
        root.mainloop()
    finally:
        allow_sleep()
</file>

<file path="production_test_datalog.csv">
Timestamp,PCBA_SN,JIG_ID,Test_Mode,Port_ID,Step_Current_A,Measured_Volt_V,Measured_Curr_A,Vdrop_mV,OCP_Status,Step_Result,Final_Port_Result
2026-09-16 10:21:22,1,1,SKYFALL JIG Mode,TBTB,1.5,4.853,1.501,266.0,N/A,PASS,PENDING
2026-09-16 10:21:30,1,1,SKYFALL JIG Mode,TBTB,2.5,4.674,2.498,445.0,N/A,PASS,PENDING
2026-09-16 10:21:37,1,1,SKYFALL JIG Mode,TBTB,3.0,4.578,3.001,541.0,N/A,PASS,PENDING
2026-09-16 10:21:42,1,1,SKYFALL JIG Mode,TBTB,3.6,0.005,0.0,5114.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:21:56,1,1,SKYFALL JIG Mode,TBTB,0.0,5.117,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:21:57,1,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:22:20,1,1,SKYFALL JIG Mode,TBTC,1.5,4.838,1.501,271.0,N/A,PASS,PENDING
2026-09-16 10:22:27,1,1,SKYFALL JIG Mode,TBTC,2.5,4.655,2.502,454.0,N/A,PASS,PENDING
2026-09-16 10:22:35,1,1,SKYFALL JIG Mode,TBTC,3.0,4.563,3.001,546.0,N/A,PASS,PENDING
2026-09-16 10:22:39,1,1,SKYFALL JIG Mode,TBTC,3.6,0.002,0.0,5107.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:22:54,1,1,SKYFALL JIG Mode,TBTC,0.0,5.11,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:22:55,1,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:23:15,1,1,SKYFALL JIG Mode,TBTD,1.5,4.846,1.502,261.0,N/A,PASS,PENDING
2026-09-16 10:23:23,1,1,SKYFALL JIG Mode,TBTD,2.5,4.672,2.499,435.0,N/A,PASS,PENDING
2026-09-16 10:23:30,1,1,SKYFALL JIG Mode,TBTD,3.0,4.582,3.001,525.0,N/A,PASS,PENDING
2026-09-16 10:23:35,1,1,SKYFALL JIG Mode,TBTD,3.6,0.004,0.0,5103.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:23:45,1,1,SKYFALL JIG Mode,TBTD,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:23:46,1,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:24:36,1,2,SKYFALL JIG Mode,TBTB,1.5,4.853,1.501,267.0,N/A,PASS,PENDING
2026-09-16 10:24:44,1,2,SKYFALL JIG Mode,TBTB,2.5,4.669,2.502,451.0,N/A,PASS,PENDING
2026-09-16 10:24:51,1,2,SKYFALL JIG Mode,TBTB,3.0,4.574,3.0,546.0,N/A,PASS,PENDING
2026-09-16 10:24:55,1,2,SKYFALL JIG Mode,TBTB,3.6,0.006,0.0,5114.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:25:10,1,2,SKYFALL JIG Mode,TBTB,0.0,5.122,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:25:11,1,2,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:25:29,1,2,SKYFALL JIG Mode,TBTC,1.5,4.841,1.495,268.0,N/A,PASS,PENDING
2026-09-16 10:25:37,1,2,SKYFALL JIG Mode,TBTC,2.5,4.661,2.498,448.0,N/A,PASS,PENDING
2026-09-16 10:25:44,1,2,SKYFALL JIG Mode,TBTC,3.0,4.567,3.001,542.0,N/A,PASS,PENDING
2026-09-16 10:25:49,1,2,SKYFALL JIG Mode,TBTC,3.6,0.006,0.0,5103.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:26:00,1,2,SKYFALL JIG Mode,TBTC,0.0,5.111,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:26:01,1,2,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:26:20,1,2,SKYFALL JIG Mode,TBTD,1.5,4.848,1.496,261.0,N/A,PASS,PENDING
2026-09-16 10:26:28,1,2,SKYFALL JIG Mode,TBTD,2.5,4.672,2.499,437.0,N/A,PASS,PENDING
2026-09-16 10:26:35,1,2,SKYFALL JIG Mode,TBTD,3.0,4.582,3.001,527.0,N/A,PASS,PENDING
2026-09-16 10:26:39,1,2,SKYFALL JIG Mode,TBTD,3.6,0.004,0.0,5105.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:26:52,1,2,SKYFALL JIG Mode,TBTD,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:26:53,1,2,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:27:49,1,3,SKYFALL JIG Mode,TBTB,1.5,4.851,1.382,267.0,N/A,PASS,PENDING
2026-09-16 10:27:56,1,3,SKYFALL JIG Mode,TBTB,2.5,4.671,2.502,447.0,N/A,PASS,PENDING
2026-09-16 10:28:04,1,3,SKYFALL JIG Mode,TBTB,3.0,4.573,3.0,545.0,N/A,PASS,PENDING
2026-09-16 10:28:08,1,3,SKYFALL JIG Mode,TBTB,3.6,0.005,0.0,5113.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:28:32,1,3,SKYFALL JIG Mode,TBTB,0.0,5.118,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:28:33,1,3,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:28:52,1,3,SKYFALL JIG Mode,TBTC,1.5,4.837,1.502,271.0,N/A,PASS,PENDING
2026-09-16 10:29:00,1,3,SKYFALL JIG Mode,TBTC,2.5,4.657,2.502,451.0,N/A,PASS,PENDING
2026-09-16 10:29:07,1,3,SKYFALL JIG Mode,TBTC,3.0,4.564,2.995,544.0,N/A,PASS,PENDING
2026-09-16 10:29:12,1,3,SKYFALL JIG Mode,TBTC,3.6,0.002,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:29:34,1,3,SKYFALL JIG Mode,TBTC,0.0,5.107,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:29:35,1,3,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:30:02,1,3,SKYFALL JIG Mode,TBTD,1.5,4.847,1.501,259.0,N/A,PASS,PENDING
2026-09-16 10:30:09,1,3,SKYFALL JIG Mode,TBTD,2.5,4.67,2.503,436.0,N/A,PASS,PENDING
2026-09-16 10:30:17,1,3,SKYFALL JIG Mode,TBTD,3.0,4.578,2.998,528.0,N/A,PASS,PENDING
2026-09-16 10:30:21,1,3,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:30:33,1,3,SKYFALL JIG Mode,TBTD,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:30:34,1,3,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:31:37,1,4,SKYFALL JIG Mode,TBTB,1.5,4.85,1.499,270.0,N/A,PASS,PENDING
2026-09-16 10:31:45,1,4,SKYFALL JIG Mode,TBTB,2.5,4.667,2.497,453.0,N/A,PASS,PENDING
2026-09-16 10:31:52,1,4,SKYFALL JIG Mode,TBTB,3.0,4.572,3.001,548.0,N/A,PASS,PENDING
2026-09-16 10:31:56,1,4,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5118.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:32:45,1,4,SKYFALL JIG Mode,TBTB,0.0,5.119,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:32:46,1,4,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:33:21,1,4,SKYFALL JIG Mode,TBTC,1.5,4.839,1.502,270.0,N/A,PASS,PENDING
2026-09-16 10:33:28,1,4,SKYFALL JIG Mode,TBTC,2.5,4.66,2.502,449.0,N/A,PASS,PENDING
2026-09-16 10:33:36,1,4,SKYFALL JIG Mode,TBTC,3.0,4.566,3.002,543.0,N/A,PASS,PENDING
2026-09-16 10:33:40,1,4,SKYFALL JIG Mode,TBTC,3.6,0.003,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:35:00,1,4,SKYFALL JIG Mode,TBTC,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:35:01,1,4,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:35:28,1,4,SKYFALL JIG Mode,TBTD,1.5,4.846,1.499,257.0,N/A,PASS,PENDING
2026-09-16 10:35:35,1,4,SKYFALL JIG Mode,TBTD,2.5,4.67,2.498,433.0,N/A,PASS,PENDING
2026-09-16 10:35:43,1,4,SKYFALL JIG Mode,TBTD,3.0,4.579,3.0,524.0,N/A,PASS,PENDING
2026-09-16 10:35:47,1,4,SKYFALL JIG Mode,TBTD,3.6,0.003,0.0,5100.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:36:15,1,4,SKYFALL JIG Mode,TBTD,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:36:16,1,4,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:38:10,1,5,SKYFALL JIG Mode,TBTB,1.5,4.853,1.499,266.0,N/A,PASS,PENDING
2026-09-16 10:38:17,1,5,SKYFALL JIG Mode,TBTB,2.5,4.671,2.502,448.0,N/A,PASS,PENDING
2026-09-16 10:38:25,1,5,SKYFALL JIG Mode,TBTB,3.0,4.577,3.001,542.0,N/A,PASS,PENDING
2026-09-16 10:38:27,1,5,SKYFALL JIG Mode,TBTB,3.5,0.144,0.0,4975.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 10:39:02,1,5,SKYFALL JIG Mode,TBTB,0.0,5.119,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:39:03,1,5,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:39:33,1,5,SKYFALL JIG Mode,TBTC,1.5,4.837,1.501,271.0,N/A,PASS,PENDING
2026-09-16 10:39:40,1,5,SKYFALL JIG Mode,TBTC,2.5,4.655,2.503,453.0,N/A,PASS,PENDING
2026-09-16 10:39:48,1,5,SKYFALL JIG Mode,TBTC,3.0,4.563,3.0,545.0,N/A,PASS,PENDING
2026-09-16 10:39:52,1,5,SKYFALL JIG Mode,TBTC,3.6,0.002,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:40:04,1,5,SKYFALL JIG Mode,TBTC,0.0,0.002,0.0,0.0,RECOVERY,FAIL (NO_RECOVERY),PENDING
2026-09-16 10:40:05,1,5,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,FAIL
2026-09-16 10:40:35,1,5,SKYFALL JIG Mode,TBTD,1.5,4.847,1.499,259.0,N/A,PASS,PENDING
2026-09-16 10:40:42,1,5,SKYFALL JIG Mode,TBTD,2.5,4.671,2.503,435.0,N/A,PASS,PENDING
2026-09-16 10:40:50,1,5,SKYFALL JIG Mode,TBTD,3.0,4.579,3.001,527.0,N/A,PASS,PENDING
2026-09-16 10:40:54,1,5,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:41:05,1,5,SKYFALL JIG Mode,TBTD,0.0,5.103,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:41:05,1,5,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:47:26,1,6,SKYFALL JIG Mode,TBTB,1.5,4.852,1.497,266.0,N/A,PASS,PENDING
2026-09-16 10:47:34,1,6,SKYFALL JIG Mode,TBTB,2.5,4.673,2.497,445.0,N/A,PASS,PENDING
2026-09-16 10:47:41,1,6,SKYFALL JIG Mode,TBTB,3.0,4.576,3.0,542.0,N/A,PASS,PENDING
2026-09-16 10:47:46,1,6,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5116.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:47:57,1,6,SKYFALL JIG Mode,TBTB,0.0,5.117,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:47:58,1,6,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:48:15,1,6,SKYFALL JIG Mode,TBTC,1.5,4.841,1.498,269.0,N/A,PASS,PENDING
2026-09-16 10:48:23,1,6,SKYFALL JIG Mode,TBTC,2.5,4.665,2.498,445.0,N/A,PASS,PENDING
2026-09-16 10:48:30,1,6,SKYFALL JIG Mode,TBTC,3.0,4.57,3.001,540.0,N/A,PASS,PENDING
2026-09-16 10:48:35,1,6,SKYFALL JIG Mode,TBTC,3.6,0.001,0.0,5109.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:48:46,1,6,SKYFALL JIG Mode,TBTC,0.0,5.108,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:48:47,1,6,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:49:08,1,6,SKYFALL JIG Mode,TBTD,1.5,4.849,1.502,257.0,N/A,PASS,PENDING
2026-09-16 10:49:15,1,6,SKYFALL JIG Mode,TBTD,2.5,4.675,2.497,431.0,N/A,PASS,PENDING
2026-09-16 10:49:23,1,6,SKYFALL JIG Mode,TBTD,3.0,4.585,3.002,521.0,N/A,PASS,PENDING
2026-09-16 10:49:27,1,6,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:49:44,1,6,SKYFALL JIG Mode,TBTD,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:49:44,1,6,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:50:44,1,7,SKYFALL JIG Mode,TBTB,1.5,4.851,1.496,268.0,N/A,PASS,PENDING
2026-09-16 10:50:51,1,7,SKYFALL JIG Mode,TBTB,2.5,4.669,2.502,450.0,N/A,PASS,PENDING
2026-09-16 10:50:59,1,7,SKYFALL JIG Mode,TBTB,3.0,4.575,3.001,544.0,N/A,PASS,PENDING
2026-09-16 10:51:03,1,7,SKYFALL JIG Mode,TBTB,3.6,0.0,0.0,5119.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:51:14,1,7,SKYFALL JIG Mode,TBTB,0.0,5.116,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:51:15,1,7,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:51:35,1,7,SKYFALL JIG Mode,TBTC,1.5,4.838,1.495,268.0,N/A,PASS,PENDING
2026-09-16 10:51:42,1,7,SKYFALL JIG Mode,TBTC,2.5,4.657,2.503,449.0,N/A,PASS,PENDING
2026-09-16 10:51:50,1,7,SKYFALL JIG Mode,TBTC,3.0,4.567,3.002,539.0,N/A,PASS,PENDING
2026-09-16 10:51:54,1,7,SKYFALL JIG Mode,TBTC,3.6,0.002,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:53:12,1,7,SKYFALL JIG Mode,TBTC,0.0,5.108,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:53:13,1,7,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:53:52,1,7,SKYFALL JIG Mode,TBTD,1.5,4.85,1.502,257.0,N/A,PASS,PENDING
2026-09-16 10:53:59,1,7,SKYFALL JIG Mode,TBTD,2.5,4.675,2.497,432.0,N/A,PASS,PENDING
2026-09-16 10:54:07,1,7,SKYFALL JIG Mode,TBTD,3.0,4.583,3.002,524.0,N/A,PASS,PENDING
2026-09-16 10:54:11,1,7,SKYFALL JIG Mode,TBTD,3.6,0.003,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:54:42,1,7,SKYFALL JIG Mode,TBTD,0.0,5.102,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:54:43,1,7,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:55:31,1,8,SKYFALL JIG Mode,TBTB,1.5,4.85,1.496,266.0,N/A,PASS,PENDING
2026-09-16 10:55:38,1,8,SKYFALL JIG Mode,TBTB,2.5,4.67,2.497,446.0,N/A,PASS,PENDING
2026-09-16 10:55:46,1,8,SKYFALL JIG Mode,TBTB,3.0,4.575,3.001,541.0,N/A,PASS,PENDING
2026-09-16 10:55:50,1,8,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5114.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:56:11,1,8,SKYFALL JIG Mode,TBTB,0.0,5.115,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:56:11,1,8,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:56:32,1,8,SKYFALL JIG Mode,TBTC,1.5,4.838,1.497,272.0,N/A,PASS,PENDING
2026-09-16 10:56:39,1,8,SKYFALL JIG Mode,TBTC,2.5,4.653,2.499,457.0,N/A,PASS,PENDING
2026-09-16 10:56:47,1,8,SKYFALL JIG Mode,TBTC,3.0,4.562,3.002,548.0,N/A,PASS,PENDING
2026-09-16 10:56:51,1,8,SKYFALL JIG Mode,TBTC,3.6,0.002,0.0,5108.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:56:59,1,8,SKYFALL JIG Mode,TBTC,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:57:00,1,8,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:57:23,1,8,SKYFALL JIG Mode,TBTD,1.5,4.846,1.503,256.0,N/A,PASS,PENDING
2026-09-16 10:57:30,1,8,SKYFALL JIG Mode,TBTD,2.5,4.668,2.503,434.0,N/A,PASS,PENDING
2026-09-16 10:57:38,1,8,SKYFALL JIG Mode,TBTD,3.0,4.577,3.002,525.0,N/A,PASS,PENDING
2026-09-16 10:57:42,1,8,SKYFALL JIG Mode,TBTD,3.6,0.001,0.0,5101.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:58:01,1,8,SKYFALL JIG Mode,TBTD,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:58:02,1,8,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:58:48,1,9,SKYFALL JIG Mode,TBTB,1.5,4.849,1.502,268.0,N/A,PASS,PENDING
2026-09-16 10:58:55,1,9,SKYFALL JIG Mode,TBTB,2.5,4.67,2.497,447.0,N/A,PASS,PENDING
2026-09-16 10:59:02,1,9,SKYFALL JIG Mode,TBTB,3.0,4.574,3.002,543.0,N/A,PASS,PENDING
2026-09-16 10:59:07,1,9,SKYFALL JIG Mode,TBTB,3.6,0.001,0.0,5116.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 10:59:23,1,9,SKYFALL JIG Mode,TBTB,0.0,5.118,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 10:59:24,1,9,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 10:59:46,1,9,SKYFALL JIG Mode,TBTC,1.5,4.838,1.503,267.0,N/A,PASS,PENDING
2026-09-16 10:59:53,1,9,SKYFALL JIG Mode,TBTC,2.5,4.657,2.503,448.0,N/A,PASS,PENDING
2026-09-16 11:00:01,1,9,SKYFALL JIG Mode,TBTC,3.0,4.563,3.002,542.0,N/A,PASS,PENDING
2026-09-16 11:00:05,1,9,SKYFALL JIG Mode,TBTC,3.6,0.0,0.0,5105.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:00:17,1,9,SKYFALL JIG Mode,TBTC,0.0,5.108,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:00:18,1,9,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:01:05,1,9,SKYFALL JIG Mode,TBTD,1.5,4.85,1.502,256.0,N/A,PASS,PENDING
2026-09-16 11:01:12,1,9,SKYFALL JIG Mode,TBTD,2.5,4.675,2.498,431.0,N/A,PASS,PENDING
2026-09-16 11:01:19,1,9,SKYFALL JIG Mode,TBTD,3.0,4.584,2.999,522.0,N/A,PASS,PENDING
2026-09-16 11:01:24,1,9,SKYFALL JIG Mode,TBTD,3.6,0.001,0.0,5105.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:01:35,1,9,SKYFALL JIG Mode,TBTD,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:01:36,1,9,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:02:53,1,10,SKYFALL JIG Mode,TBTB,1.5,4.854,1.495,264.0,N/A,PASS,PENDING
2026-09-16 11:03:00,1,10,SKYFALL JIG Mode,TBTB,2.5,4.672,2.503,446.0,N/A,PASS,PENDING
2026-09-16 11:03:08,1,10,SKYFALL JIG Mode,TBTB,3.0,4.578,2.998,540.0,N/A,PASS,PENDING
2026-09-16 11:03:12,1,10,SKYFALL JIG Mode,TBTB,3.6,0.001,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:03:24,1,10,SKYFALL JIG Mode,TBTB,0.0,5.118,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:03:25,1,10,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:03:46,1,10,SKYFALL JIG Mode,TBTC,1.5,4.842,1.5,265.0,N/A,PASS,PENDING
2026-09-16 11:03:54,1,10,SKYFALL JIG Mode,TBTC,2.5,4.664,2.497,443.0,N/A,PASS,PENDING
2026-09-16 11:04:01,1,10,SKYFALL JIG Mode,TBTC,3.0,4.568,2.996,539.0,N/A,PASS,PENDING
2026-09-16 11:04:05,1,10,SKYFALL JIG Mode,TBTC,3.6,0.004,0.0,5103.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:04:44,1,10,SKYFALL JIG Mode,TBTC,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:04:45,1,10,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:05:07,1,10,SKYFALL JIG Mode,TBTD,1.5,4.846,1.502,256.0,N/A,PASS,PENDING
2026-09-16 11:05:15,1,10,SKYFALL JIG Mode,TBTD,2.5,4.671,2.499,431.0,N/A,PASS,PENDING
2026-09-16 11:05:22,1,10,SKYFALL JIG Mode,TBTD,3.0,4.579,3.002,523.0,N/A,PASS,PENDING
2026-09-16 11:05:26,1,10,SKYFALL JIG Mode,TBTD,3.6,0.0,0.0,5102.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:05:38,1,10,SKYFALL JIG Mode,TBTD,0.0,5.103,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:05:39,1,10,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:06:35,2,1,SKYFALL JIG Mode,TBTB,1.5,4.854,1.497,264.0,N/A,PASS,PENDING
2026-09-16 11:06:42,2,1,SKYFALL JIG Mode,TBTB,2.5,4.671,2.498,447.0,N/A,PASS,PENDING
2026-09-16 11:06:50,2,1,SKYFALL JIG Mode,TBTB,3.0,4.579,3.002,539.0,N/A,PASS,PENDING
2026-09-16 11:06:54,2,1,SKYFALL JIG Mode,TBTB,3.6,0.001,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:07:05,2,1,SKYFALL JIG Mode,TBTB,0.0,5.117,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:07:06,2,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:07:26,2,1,SKYFALL JIG Mode,TBTC,1.5,4.836,1.503,268.0,N/A,PASS,PENDING
2026-09-16 11:07:34,2,1,SKYFALL JIG Mode,TBTC,2.5,4.66,2.498,444.0,N/A,PASS,PENDING
2026-09-16 11:07:41,2,1,SKYFALL JIG Mode,TBTC,3.0,4.563,3.0,541.0,N/A,PASS,PENDING
2026-09-16 11:07:43,2,1,SKYFALL JIG Mode,TBTC,3.5,0.007,0.0,5097.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:07:53,2,1,SKYFALL JIG Mode,TBTC,0.0,5.103,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:07:53,2,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:08:14,2,1,SKYFALL JIG Mode,TBTD,1.5,4.846,1.496,262.0,N/A,PASS,PENDING
2026-09-16 11:08:22,2,1,SKYFALL JIG Mode,TBTD,2.5,4.668,2.504,440.0,N/A,PASS,PENDING
2026-09-16 11:08:29,2,1,SKYFALL JIG Mode,TBTD,3.0,4.576,3.002,532.0,N/A,PASS,PENDING
2026-09-16 11:08:34,2,1,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:08:45,2,1,SKYFALL JIG Mode,TBTD,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:08:46,2,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:09:34,2,2,SKYFALL JIG Mode,TBTB,1.5,4.856,1.5,261.0,N/A,PASS,PENDING
2026-09-16 11:09:41,2,2,SKYFALL JIG Mode,TBTB,2.5,4.674,2.504,443.0,N/A,PASS,PENDING
2026-09-16 11:09:48,2,2,SKYFALL JIG Mode,TBTB,3.0,4.577,3.001,540.0,N/A,PASS,PENDING
2026-09-16 11:09:53,2,2,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5115.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:10:04,2,2,SKYFALL JIG Mode,TBTB,0.0,5.119,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:10:05,2,2,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:10:27,2,2,SKYFALL JIG Mode,TBTC,1.5,4.84,1.502,267.0,N/A,PASS,PENDING
2026-09-16 11:10:34,2,2,SKYFALL JIG Mode,TBTC,2.5,4.659,2.503,448.0,N/A,PASS,PENDING
2026-09-16 11:10:42,2,2,SKYFALL JIG Mode,TBTC,3.0,4.566,3.001,541.0,N/A,PASS,PENDING
2026-09-16 11:10:46,2,2,SKYFALL JIG Mode,TBTC,3.6,0.003,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:10:56,2,2,SKYFALL JIG Mode,TBTC,0.0,5.105,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:10:57,2,2,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:11:27,2,2,SKYFALL JIG Mode,TBTD,1.5,4.85,1.497,260.0,N/A,PASS,PENDING
2026-09-16 11:11:34,2,2,SKYFALL JIG Mode,TBTD,2.5,4.673,2.503,437.0,N/A,PASS,PENDING
2026-09-16 11:11:41,2,2,SKYFALL JIG Mode,TBTD,3.0,4.581,2.997,529.0,N/A,PASS,PENDING
2026-09-16 11:11:46,2,2,SKYFALL JIG Mode,TBTD,3.6,0.003,0.0,5107.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:11:57,2,2,SKYFALL JIG Mode,TBTD,0.0,5.107,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:11:58,2,2,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:12:50,2,3,SKYFALL JIG Mode,TBTB,1.5,4.853,1.499,267.0,N/A,PASS,PENDING
2026-09-16 11:12:57,2,3,SKYFALL JIG Mode,TBTB,2.5,4.67,2.504,450.0,N/A,PASS,PENDING
2026-09-16 11:13:05,2,3,SKYFALL JIG Mode,TBTB,3.0,4.578,3.0,542.0,N/A,PASS,PENDING
2026-09-16 11:13:07,2,3,SKYFALL JIG Mode,TBTB,3.5,0.567,0.0,4553.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:13:20,2,3,SKYFALL JIG Mode,TBTB,0.0,5.114,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:13:21,2,3,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:13:43,2,3,SKYFALL JIG Mode,TBTC,1.5,4.836,1.496,266.0,N/A,PASS,PENDING
2026-09-16 11:13:50,2,3,SKYFALL JIG Mode,TBTC,2.5,4.653,2.498,449.0,N/A,PASS,PENDING
2026-09-16 11:13:57,2,3,SKYFALL JIG Mode,TBTC,3.0,4.561,2.999,541.0,N/A,PASS,PENDING
2026-09-16 11:14:00,2,3,SKYFALL JIG Mode,TBTC,3.5,0.005,0.0,5097.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:14:12,2,3,SKYFALL JIG Mode,TBTC,0.0,5.103,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:14:13,2,3,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:14:39,2,3,SKYFALL JIG Mode,TBTD,1.5,4.847,1.503,258.0,N/A,PASS,PENDING
2026-09-16 11:14:47,2,3,SKYFALL JIG Mode,TBTD,2.5,4.669,2.503,436.0,N/A,PASS,PENDING
2026-09-16 11:14:54,2,3,SKYFALL JIG Mode,TBTD,3.0,4.577,3.0,528.0,N/A,PASS,PENDING
2026-09-16 11:14:59,2,3,SKYFALL JIG Mode,TBTD,3.6,0.001,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:15:08,2,3,SKYFALL JIG Mode,TBTD,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:15:09,2,3,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:16:11,2,4,SKYFALL JIG Mode,TBTB,1.5,4.85,1.502,266.0,N/A,PASS,PENDING
2026-09-16 11:16:19,2,4,SKYFALL JIG Mode,TBTB,2.5,4.672,2.497,444.0,N/A,PASS,PENDING
2026-09-16 11:16:26,2,4,SKYFALL JIG Mode,TBTB,3.0,4.576,2.999,540.0,N/A,PASS,PENDING
2026-09-16 11:16:30,2,4,SKYFALL JIG Mode,TBTB,3.6,0.003,0.0,5113.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:16:45,2,4,SKYFALL JIG Mode,TBTB,0.0,5.118,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:16:46,2,4,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:17:08,2,4,SKYFALL JIG Mode,TBTC,1.5,4.84,1.502,266.0,N/A,PASS,PENDING
2026-09-16 11:17:15,2,4,SKYFALL JIG Mode,TBTC,2.5,4.66,2.497,446.0,N/A,PASS,PENDING
2026-09-16 11:17:23,2,4,SKYFALL JIG Mode,TBTC,3.0,4.567,2.998,539.0,N/A,PASS,PENDING
2026-09-16 11:17:25,2,4,SKYFALL JIG Mode,TBTC,3.5,0.598,0.0,4508.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:17:45,2,4,SKYFALL JIG Mode,TBTC,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:17:46,2,4,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:18:14,2,4,SKYFALL JIG Mode,TBTD,1.5,4.847,1.496,261.0,N/A,PASS,PENDING
2026-09-16 11:18:22,2,4,SKYFALL JIG Mode,TBTD,2.5,4.671,2.498,437.0,N/A,PASS,PENDING
2026-09-16 11:18:29,2,4,SKYFALL JIG Mode,TBTD,3.0,4.579,2.999,529.0,N/A,PASS,PENDING
2026-09-16 11:18:33,2,4,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:19:01,2,4,SKYFALL JIG Mode,TBTD,0.0,5.109,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:19:01,2,4,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:19:44,2,5,SKYFALL JIG Mode,TBTB,1.5,4.851,1.499,270.0,N/A,PASS,PENDING
2026-09-16 11:19:51,2,5,SKYFALL JIG Mode,TBTB,2.5,4.669,2.498,452.0,N/A,PASS,PENDING
2026-09-16 11:19:59,2,5,SKYFALL JIG Mode,TBTB,3.0,4.576,3.001,545.0,N/A,PASS,PENDING
2026-09-16 11:20:03,2,5,SKYFALL JIG Mode,TBTB,3.6,0.003,0.0,5118.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:20:13,2,5,SKYFALL JIG Mode,TBTB,0.0,5.117,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:20:14,2,5,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:20:39,2,5,SKYFALL JIG Mode,TBTC,1.5,4.839,1.503,267.0,N/A,PASS,PENDING
2026-09-16 11:20:47,2,5,SKYFALL JIG Mode,TBTC,2.5,4.659,2.503,447.0,N/A,PASS,PENDING
2026-09-16 11:20:54,2,5,SKYFALL JIG Mode,TBTC,3.0,4.565,2.997,541.0,N/A,PASS,PENDING
2026-09-16 11:20:58,2,5,SKYFALL JIG Mode,TBTC,3.6,0.003,0.0,5103.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:21:10,2,5,SKYFALL JIG Mode,TBTC,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:21:11,2,5,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:21:35,2,5,SKYFALL JIG Mode,TBTD,1.5,4.847,1.499,261.0,N/A,PASS,PENDING
2026-09-16 11:21:42,2,5,SKYFALL JIG Mode,TBTD,2.5,4.669,2.501,439.0,N/A,PASS,PENDING
2026-09-16 11:21:50,2,5,SKYFALL JIG Mode,TBTD,3.0,4.578,2.998,530.0,N/A,PASS,PENDING
2026-09-16 11:21:54,2,5,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:22:06,2,5,SKYFALL JIG Mode,TBTD,0.0,5.109,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:22:07,2,5,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:23:01,2,6,SKYFALL JIG Mode,TBTB,1.5,4.851,1.499,266.0,N/A,PASS,PENDING
2026-09-16 11:23:09,2,6,SKYFALL JIG Mode,TBTB,2.5,4.668,2.498,449.0,N/A,PASS,PENDING
2026-09-16 11:23:16,2,6,SKYFALL JIG Mode,TBTB,3.0,4.576,3.002,541.0,N/A,PASS,PENDING
2026-09-16 11:23:20,2,6,SKYFALL JIG Mode,TBTB,3.6,0.003,0.0,5114.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:24:31,2,6,SKYFALL JIG Mode,TBTB,0.0,5.117,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:24:31,2,6,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:24:54,2,6,SKYFALL JIG Mode,TBTC,1.5,4.837,1.496,268.0,N/A,PASS,PENDING
2026-09-16 11:25:02,2,6,SKYFALL JIG Mode,TBTC,2.5,4.659,2.497,446.0,N/A,PASS,PENDING
2026-09-16 11:25:09,2,6,SKYFALL JIG Mode,TBTC,3.0,4.563,2.996,542.0,N/A,PASS,PENDING
2026-09-16 11:25:11,2,6,SKYFALL JIG Mode,TBTC,3.5,0.008,0.0,5097.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:25:31,2,6,SKYFALL JIG Mode,TBTC,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:25:31,2,6,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:25:54,2,6,SKYFALL JIG Mode,TBTD,1.5,4.846,1.503,261.0,N/A,PASS,PENDING
2026-09-16 11:26:02,2,6,SKYFALL JIG Mode,TBTD,2.5,4.67,2.501,437.0,N/A,PASS,PENDING
2026-09-16 11:26:09,2,6,SKYFALL JIG Mode,TBTD,3.0,4.577,3.003,530.0,N/A,PASS,PENDING
2026-09-16 11:26:14,2,6,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5105.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:26:48,2,6,SKYFALL JIG Mode,TBTD,0.0,5.108,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:26:48,2,6,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:28:57,2,7,SKYFALL JIG Mode,TBTB,1.5,4.852,1.497,266.0,N/A,PASS,PENDING
2026-09-16 11:29:04,2,7,SKYFALL JIG Mode,TBTB,2.5,4.671,2.497,447.0,N/A,PASS,PENDING
2026-09-16 11:29:11,2,7,SKYFALL JIG Mode,TBTB,3.0,4.576,3.001,542.0,N/A,PASS,PENDING
2026-09-16 11:29:16,2,7,SKYFALL JIG Mode,TBTB,3.6,0.001,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:29:42,2,7,SKYFALL JIG Mode,TBTB,0.0,5.115,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:29:43,2,7,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:30:02,2,7,SKYFALL JIG Mode,TBTC,1.5,4.835,1.503,270.0,N/A,PASS,PENDING
2026-09-16 11:30:09,2,7,SKYFALL JIG Mode,TBTC,2.5,4.658,2.497,447.0,N/A,PASS,PENDING
2026-09-16 11:30:17,2,7,SKYFALL JIG Mode,TBTC,3.0,4.564,3.002,541.0,N/A,PASS,PENDING
2026-09-16 11:30:19,2,7,SKYFALL JIG Mode,TBTC,3.5,0.018,0.0,5087.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:31:19,2,7,SKYFALL JIG Mode,TBTC,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:31:20,2,7,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:31:46,2,7,SKYFALL JIG Mode,TBTD,1.5,4.849,1.498,258.0,N/A,PASS,PENDING
2026-09-16 11:31:53,2,7,SKYFALL JIG Mode,TBTD,2.5,4.671,2.503,436.0,N/A,PASS,PENDING
2026-09-16 11:32:01,2,7,SKYFALL JIG Mode,TBTD,3.0,4.58,2.996,527.0,N/A,PASS,PENDING
2026-09-16 11:32:05,2,7,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5105.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:32:32,2,7,SKYFALL JIG Mode,TBTD,0.0,5.108,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:32:33,2,7,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:35:02,2,8,SKYFALL JIG Mode,TBTB,1.5,4.852,1.502,265.0,N/A,PASS,PENDING
2026-09-16 11:35:09,2,8,SKYFALL JIG Mode,TBTB,2.5,4.674,2.504,443.0,N/A,PASS,PENDING
2026-09-16 11:35:17,2,8,SKYFALL JIG Mode,TBTB,3.0,4.58,2.996,537.0,N/A,PASS,PENDING
2026-09-16 11:35:21,2,8,SKYFALL JIG Mode,TBTB,3.6,0.004,0.0,5113.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:35:33,2,8,SKYFALL JIG Mode,TBTB,0.0,5.117,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:35:34,2,8,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:37:09,2,8,SKYFALL JIG Mode,TBTC,1.5,4.837,1.502,268.0,N/A,PASS,PENDING
2026-09-16 11:37:16,2,8,SKYFALL JIG Mode,TBTC,2.5,4.66,2.497,445.0,N/A,PASS,PENDING
2026-09-16 11:37:24,2,8,SKYFALL JIG Mode,TBTC,3.0,4.566,3.001,539.0,N/A,PASS,PENDING
2026-09-16 11:37:28,2,8,SKYFALL JIG Mode,TBTC,3.6,0.004,0.0,5101.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:37:39,2,8,SKYFALL JIG Mode,TBTC,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:37:40,2,8,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:37:59,2,8,SKYFALL JIG Mode,TBTD,1.5,4.85,1.499,259.0,N/A,PASS,PENDING
2026-09-16 11:38:06,2,8,SKYFALL JIG Mode,TBTD,2.5,4.674,2.5,435.0,N/A,PASS,PENDING
2026-09-16 11:38:14,2,8,SKYFALL JIG Mode,TBTD,3.0,4.581,3.002,528.0,N/A,PASS,PENDING
2026-09-16 11:38:16,2,8,SKYFALL JIG Mode,TBTD,3.5,0.01,0.0,5099.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:38:29,2,8,SKYFALL JIG Mode,TBTD,0.0,5.107,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:38:30,2,8,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:39:21,2,9,SKYFALL JIG Mode,TBTB,1.5,4.851,1.499,268.0,N/A,PASS,PENDING
2026-09-16 11:39:29,2,9,SKYFALL JIG Mode,TBTB,2.5,4.668,2.501,451.0,N/A,PASS,PENDING
2026-09-16 11:39:36,2,9,SKYFALL JIG Mode,TBTB,3.0,4.577,2.999,542.0,N/A,PASS,PENDING
2026-09-16 11:39:38,2,9,SKYFALL JIG Mode,TBTB,3.5,0.139,0.0,4980.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:40:18,2,9,SKYFALL JIG Mode,TBTB,0.0,5.116,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:40:19,2,9,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:40:39,2,9,SKYFALL JIG Mode,TBTC,1.5,4.837,1.502,271.0,N/A,PASS,PENDING
2026-09-16 11:40:47,2,9,SKYFALL JIG Mode,TBTC,2.5,4.66,2.498,448.0,N/A,PASS,PENDING
2026-09-16 11:40:54,2,9,SKYFALL JIG Mode,TBTC,3.0,4.565,3.0,543.0,N/A,PASS,PENDING
2026-09-16 11:40:56,2,9,SKYFALL JIG Mode,TBTC,3.5,0.078,0.0,5030.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-16 11:41:09,2,9,SKYFALL JIG Mode,TBTC,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:41:10,2,9,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:41:33,2,9,SKYFALL JIG Mode,TBTD,1.5,4.851,1.503,257.0,N/A,PASS,PENDING
2026-09-16 11:41:40,2,9,SKYFALL JIG Mode,TBTD,2.5,4.674,2.498,434.0,N/A,PASS,PENDING
2026-09-16 11:41:48,2,9,SKYFALL JIG Mode,TBTD,3.0,4.583,3.003,525.0,N/A,PASS,PENDING
2026-09-16 11:41:52,2,9,SKYFALL JIG Mode,TBTD,3.6,0.005,0.0,5103.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:42:05,2,9,SKYFALL JIG Mode,TBTD,0.0,5.11,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:42:06,2,9,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:43:01,2,10,SKYFALL JIG Mode,TBTB,1.5,4.855,1.495,265.0,N/A,PASS,PENDING
2026-09-16 11:43:08,2,10,SKYFALL JIG Mode,TBTB,2.5,4.676,2.497,444.0,N/A,PASS,PENDING
2026-09-16 11:43:16,2,10,SKYFALL JIG Mode,TBTB,3.0,4.58,3.002,540.0,N/A,PASS,PENDING
2026-09-16 11:43:20,2,10,SKYFALL JIG Mode,TBTB,3.6,0.004,0.0,5116.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:44:14,2,10,SKYFALL JIG Mode,TBTB,0.0,5.117,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:44:15,2,10,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:44:36,2,10,SKYFALL JIG Mode,TBTC,1.5,4.84,1.502,265.0,N/A,PASS,PENDING
2026-09-16 11:44:43,2,10,SKYFALL JIG Mode,TBTC,2.5,4.662,2.503,443.0,N/A,PASS,PENDING
2026-09-16 11:44:51,2,10,SKYFALL JIG Mode,TBTC,3.0,4.568,3.0,537.0,N/A,PASS,PENDING
2026-09-16 11:44:55,2,10,SKYFALL JIG Mode,TBTC,3.6,0.004,0.0,5101.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:45:04,2,10,SKYFALL JIG Mode,TBTC,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:45:05,2,10,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 11:45:25,2,10,SKYFALL JIG Mode,TBTD,1.5,4.851,1.496,260.0,N/A,PASS,PENDING
2026-09-16 11:45:33,2,10,SKYFALL JIG Mode,TBTD,2.5,4.672,2.5,439.0,N/A,PASS,PENDING
2026-09-16 11:45:40,2,10,SKYFALL JIG Mode,TBTD,3.0,4.581,2.866,530.0,N/A,PASS,PENDING
2026-09-16 11:45:45,2,10,SKYFALL JIG Mode,TBTD,3.6,0.002,0.0,5109.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 11:45:55,2,10,SKYFALL JIG Mode,TBTD,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 11:45:56,2,10,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 15:42:15,1,1,SKYFALL JIG Mode,TBTB,1.5,4.856,1.502,266.0,N/A,PASS,PENDING
2026-09-16 15:42:22,1,1,SKYFALL JIG Mode,TBTB,2.5,4.678,2.5,444.0,N/A,PASS,PENDING
2026-09-16 15:42:30,1,1,SKYFALL JIG Mode,TBTB,3.0,4.587,2.998,535.0,N/A,PASS,PENDING
2026-09-16 15:42:34,1,1,SKYFALL JIG Mode,TBTB,3.6,0.005,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 15:42:46,1,1,SKYFALL JIG Mode,TBTB,0.0,5.121,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 15:42:47,1,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 17:09:46,1,1,SKYFALL JIG Mode,TBTB,1.5,4.858,1.498,265.0,N/A,PASS,PENDING
2026-09-16 17:09:53,1,1,SKYFALL JIG Mode,TBTB,2.5,4.678,2.5,445.0,N/A,PASS,PENDING
2026-09-16 17:10:01,1,1,SKYFALL JIG Mode,TBTB,3.0,4.583,3.002,540.0,N/A,PASS,PENDING
2026-09-16 17:10:05,1,1,SKYFALL JIG Mode,TBTB,3.6,0.006,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 17:10:55,1,1,SKYFALL JIG Mode,TBTB,0.0,5.124,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-16 17:10:56,1,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-16 17:11:27,1,1,SKYFALL JIG Mode,TBTC,1.5,4.846,1.498,267.0,N/A,PASS,PENDING
2026-09-16 17:11:34,1,1,SKYFALL JIG Mode,TBTC,2.5,4.663,2.501,450.0,N/A,PASS,PENDING
2026-09-16 17:11:42,1,1,SKYFALL JIG Mode,TBTC,3.0,4.571,2.998,542.0,N/A,PASS,PENDING
2026-09-16 17:11:46,1,1,SKYFALL JIG Mode,TBTC,3.6,0.004,0.0,5109.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-16 17:16:36,1,1,SKYFALL JIG Mode,TBTC,0.0,0.007,0.0,0.0,RECOVERY,FAIL (NO_RECOVERY),PENDING
2026-09-17 15:05:35,44,1,SKYFALL JIG Mode,TBTB,1.5,4.846,1.499,265.0,N/A,PASS,PENDING
2026-09-17 15:05:42,44,1,SKYFALL JIG Mode,TBTB,2.5,4.664,2.5,447.0,N/A,PASS,PENDING
2026-09-17 15:05:50,44,1,SKYFALL JIG Mode,TBTB,3.0,4.57,3.001,541.0,N/A,PASS,PENDING
2026-09-17 15:05:54,44,1,SKYFALL JIG Mode,TBTB,3.6,0.003,0.0,5108.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:06:04,44,1,SKYFALL JIG Mode,TBTB,0.0,5.111,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:06:05,44,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:06:24,44,1,SKYFALL JIG Mode,TBTC,1.5,4.808,1.501,273.0,N/A,PASS,PENDING
2026-09-17 15:06:32,44,1,SKYFALL JIG Mode,TBTC,2.5,4.628,2.503,453.0,N/A,PASS,PENDING
2026-09-17 15:06:39,44,1,SKYFALL JIG Mode,TBTC,3.0,4.534,2.998,547.0,N/A,PASS,PENDING
2026-09-17 15:06:43,44,1,SKYFALL JIG Mode,TBTC,3.6,0.005,0.0,5076.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:06:54,44,1,SKYFALL JIG Mode,TBTC,0.0,5.078,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:06:55,44,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:07:13,44,1,SKYFALL JIG Mode,TBTD,1.5,4.867,1.501,254.0,N/A,PASS,PENDING
2026-09-17 15:07:20,44,1,SKYFALL JIG Mode,TBTD,2.5,4.691,2.499,430.0,N/A,PASS,PENDING
2026-09-17 15:07:28,44,1,SKYFALL JIG Mode,TBTD,3.0,4.6,3.001,521.0,N/A,PASS,PENDING
2026-09-17 15:07:32,44,1,SKYFALL JIG Mode,TBTD,3.6,0.004,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:07:44,44,1,SKYFALL JIG Mode,TBTD,0.0,5.122,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:07:44,44,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:10:26,431,1,SKYFALL JIG Mode,TBTB,1.5,4.849,1.503,258.0,N/A,PASS,PENDING
2026-09-17 15:10:33,431,1,SKYFALL JIG Mode,TBTB,2.5,4.672,2.498,435.0,N/A,PASS,PENDING
2026-09-17 15:10:41,431,1,SKYFALL JIG Mode,TBTB,3.0,4.578,2.999,529.0,N/A,PASS,PENDING
2026-09-17 15:10:45,431,1,SKYFALL JIG Mode,TBTB,3.6,0.001,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:11:02,431,1,SKYFALL JIG Mode,TBTB,0.0,0.003,0.0,0.0,RECOVERY,FAIL (NO_RECOVERY),PENDING
2026-09-17 15:11:03,431,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,FAIL
2026-09-17 15:18:55,4311,1,SKYFALL JIG Mode,TBTB,1.5,4.853,1.499,267.0,N/A,PASS,PENDING
2026-09-17 15:19:03,4311,1,SKYFALL JIG Mode,TBTB,2.5,4.67,2.499,450.0,N/A,PASS,PENDING
2026-09-17 15:19:10,4311,1,SKYFALL JIG Mode,TBTB,3.0,4.575,3.001,545.0,N/A,PASS,PENDING
2026-09-17 15:19:17,4311,1,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5118.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:19:28,4311,1,SKYFALL JIG Mode,TBTB,0.0,5.119,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:19:29,4311,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:19:47,4311,1,SKYFALL JIG Mode,TBTC,1.5,4.837,1.498,271.0,N/A,PASS,PENDING
2026-09-17 15:19:54,4311,1,SKYFALL JIG Mode,TBTC,2.5,4.654,2.499,454.0,N/A,PASS,PENDING
2026-09-17 15:20:02,4311,1,SKYFALL JIG Mode,TBTC,3.0,4.559,2.998,549.0,N/A,PASS,PENDING
2026-09-17 15:20:06,4311,1,SKYFALL JIG Mode,TBTC,3.6,0.002,0.0,5106.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:20:20,4311,1,SKYFALL JIG Mode,TBTC,0.0,5.107,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:20:21,4311,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:20:39,4311,1,SKYFALL JIG Mode,TBTD,1.5,4.843,1.497,263.0,N/A,PASS,PENDING
2026-09-17 15:20:47,4311,1,SKYFALL JIG Mode,TBTD,2.5,4.668,2.499,438.0,N/A,PASS,PENDING
2026-09-17 15:20:54,4311,1,SKYFALL JIG Mode,TBTD,3.0,4.574,2.996,532.0,N/A,PASS,PENDING
2026-09-17 15:20:59,4311,1,SKYFALL JIG Mode,TBTD,3.6,0.004,0.0,5102.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:21:10,4311,1,SKYFALL JIG Mode,TBTD,0.0,5.108,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:21:11,4311,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:22:10,4312,1,SKYFALL JIG Mode,TBTB,1.5,4.853,1.504,265.0,N/A,PASS,PENDING
2026-09-17 15:22:17,4312,1,SKYFALL JIG Mode,TBTB,2.5,4.674,2.504,444.0,N/A,PASS,PENDING
2026-09-17 15:22:25,4312,1,SKYFALL JIG Mode,TBTB,3.0,4.581,2.997,537.0,N/A,PASS,PENDING
2026-09-17 15:22:29,4312,1,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5116.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:22:38,4312,1,SKYFALL JIG Mode,TBTB,0.0,5.119,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:22:39,4312,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:22:57,4312,1,SKYFALL JIG Mode,TBTC,1.5,4.837,1.498,269.0,N/A,PASS,PENDING
2026-09-17 15:23:04,4312,1,SKYFALL JIG Mode,TBTC,2.5,4.66,2.499,446.0,N/A,PASS,PENDING
2026-09-17 15:23:12,4312,1,SKYFALL JIG Mode,TBTC,3.0,4.562,3.002,544.0,N/A,PASS,PENDING
2026-09-17 15:23:14,4312,1,SKYFALL JIG Mode,TBTC,3.5,0.333,0.0,4773.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-17 15:23:26,4312,1,SKYFALL JIG Mode,TBTC,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:23:27,4312,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:23:49,4312,1,SKYFALL JIG Mode,TBTD,1.5,4.85,1.496,261.0,N/A,PASS,PENDING
2026-09-17 15:23:57,4312,1,SKYFALL JIG Mode,TBTD,2.5,4.671,2.503,440.0,N/A,PASS,PENDING
2026-09-17 15:24:04,4312,1,SKYFALL JIG Mode,TBTD,3.0,4.579,3.0,532.0,N/A,PASS,PENDING
2026-09-17 15:24:08,4312,1,SKYFALL JIG Mode,TBTD,3.6,0.004,0.0,5107.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:24:18,4312,1,SKYFALL JIG Mode,TBTD,0.0,5.11,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:24:19,4312,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:25:11,4321,1,SKYFALL JIG Mode,TBTB,1.5,4.853,1.498,265.0,N/A,PASS,PENDING
2026-09-17 15:25:18,4321,1,SKYFALL JIG Mode,TBTB,2.5,4.671,2.497,447.0,N/A,PASS,PENDING
2026-09-17 15:25:26,4321,1,SKYFALL JIG Mode,TBTB,3.0,4.574,3.002,544.0,N/A,PASS,PENDING
2026-09-17 15:25:30,4321,1,SKYFALL JIG Mode,TBTB,3.6,0.001,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:25:39,4321,1,SKYFALL JIG Mode,TBTB,0.0,5.119,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:25:40,4321,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:25:57,4321,1,SKYFALL JIG Mode,TBTC,1.5,4.834,1.497,273.0,N/A,PASS,PENDING
2026-09-17 15:26:05,4321,1,SKYFALL JIG Mode,TBTC,2.5,4.655,2.5,452.0,N/A,PASS,PENDING
2026-09-17 15:26:12,4321,1,SKYFALL JIG Mode,TBTC,3.0,4.561,3.003,546.0,N/A,PASS,PENDING
2026-09-17 15:26:17,4321,1,SKYFALL JIG Mode,TBTC,3.6,0.003,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:26:27,4321,1,SKYFALL JIG Mode,TBTC,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:26:28,4321,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:26:47,4321,1,SKYFALL JIG Mode,TBTD,1.5,4.846,1.5,258.0,N/A,PASS,PENDING
2026-09-17 15:26:54,4321,1,SKYFALL JIG Mode,TBTD,2.5,4.67,2.498,434.0,N/A,PASS,PENDING
2026-09-17 15:27:02,4321,1,SKYFALL JIG Mode,TBTD,3.0,4.576,2.997,528.0,N/A,PASS,PENDING
2026-09-17 15:27:06,4321,1,SKYFALL JIG Mode,TBTD,3.6,0.003,0.0,5101.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:27:16,4321,1,SKYFALL JIG Mode,TBTD,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:27:17,4321,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:28:02,4322,1,SKYFALL JIG Mode,TBTB,1.5,4.854,1.501,267.0,N/A,PASS,PENDING
2026-09-17 15:28:10,4322,1,SKYFALL JIG Mode,TBTB,2.5,4.672,2.504,449.0,N/A,PASS,PENDING
2026-09-17 15:28:17,4322,1,SKYFALL JIG Mode,TBTB,3.0,4.575,3.003,546.0,N/A,PASS,PENDING
2026-09-17 15:28:22,4322,1,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5119.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:28:31,4322,1,SKYFALL JIG Mode,TBTB,0.0,5.12,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:28:31,4322,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:28:51,4322,1,SKYFALL JIG Mode,TBTC,1.5,4.837,1.5,272.0,N/A,PASS,PENDING
2026-09-17 15:28:59,4322,1,SKYFALL JIG Mode,TBTC,2.5,4.659,2.497,450.0,N/A,PASS,PENDING
2026-09-17 15:29:06,4322,1,SKYFALL JIG Mode,TBTC,3.0,4.563,2.999,546.0,N/A,PASS,PENDING
2026-09-17 15:29:11,4322,1,SKYFALL JIG Mode,TBTC,3.6,0.004,0.0,5105.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:29:18,4322,1,SKYFALL JIG Mode,TBTC,0.0,5.107,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:29:19,4322,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:29:40,4322,1,SKYFALL JIG Mode,TBTD,1.5,4.845,1.499,262.0,N/A,PASS,PENDING
2026-09-17 15:29:48,4322,1,SKYFALL JIG Mode,TBTD,2.5,4.667,2.501,440.0,N/A,PASS,PENDING
2026-09-17 15:29:55,4322,1,SKYFALL JIG Mode,TBTD,3.0,4.576,3.001,531.0,N/A,PASS,PENDING
2026-09-17 15:29:59,4322,1,SKYFALL JIG Mode,TBTD,3.6,0.003,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:30:09,4322,1,SKYFALL JIG Mode,TBTD,0.0,5.108,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:30:10,4322,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:31:12,4411,1,SKYFALL JIG Mode,TBTB,1.5,4.842,1.497,267.0,N/A,PASS,PENDING
2026-09-17 15:31:19,4411,1,SKYFALL JIG Mode,TBTB,2.5,4.662,2.501,447.0,N/A,PASS,PENDING
2026-09-17 15:31:27,4411,1,SKYFALL JIG Mode,TBTB,3.0,4.569,2.999,540.0,N/A,PASS,PENDING
2026-09-17 15:31:31,4411,1,SKYFALL JIG Mode,TBTB,3.6,0.002,0.0,5107.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:31:41,4411,1,SKYFALL JIG Mode,TBTB,0.0,5.109,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:31:42,4411,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:32:00,4411,1,SKYFALL JIG Mode,TBTC,1.5,4.813,1.497,264.0,N/A,PASS,PENDING
2026-09-17 15:32:08,4411,1,SKYFALL JIG Mode,TBTC,2.5,4.63,2.502,447.0,N/A,PASS,PENDING
2026-09-17 15:32:15,4411,1,SKYFALL JIG Mode,TBTC,3.0,4.539,3.0,538.0,N/A,PASS,PENDING
2026-09-17 15:32:20,4411,1,SKYFALL JIG Mode,TBTC,3.6,0.003,0.0,5074.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:32:31,4411,1,SKYFALL JIG Mode,TBTC,0.0,5.081,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:32:31,4411,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:32:51,4411,1,SKYFALL JIG Mode,TBTD,1.5,4.867,1.501,254.0,N/A,PASS,PENDING
2026-09-17 15:32:59,4411,1,SKYFALL JIG Mode,TBTD,2.5,4.694,2.505,427.0,N/A,PASS,PENDING
2026-09-17 15:33:06,4411,1,SKYFALL JIG Mode,TBTD,3.0,4.606,2.997,515.0,N/A,PASS,PENDING
2026-09-17 15:33:08,4411,1,SKYFALL JIG Mode,TBTD,3.5,0.111,0.0,5010.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-17 15:33:17,4411,1,SKYFALL JIG Mode,TBTD,0.0,5.119,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:33:18,4411,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:34:01,4412,1,SKYFALL JIG Mode,TBTB,1.5,4.84,1.497,270.0,N/A,PASS,PENDING
2026-09-17 15:34:09,4412,1,SKYFALL JIG Mode,TBTB,2.5,4.66,2.501,450.0,N/A,PASS,PENDING
2026-09-17 15:34:16,4412,1,SKYFALL JIG Mode,TBTB,3.0,4.564,2.999,546.0,N/A,PASS,PENDING
2026-09-17 15:34:20,4412,1,SKYFALL JIG Mode,TBTB,3.6,0.003,0.0,5107.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:34:30,4412,1,SKYFALL JIG Mode,TBTB,0.0,5.106,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:34:31,4412,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:34:49,4412,1,SKYFALL JIG Mode,TBTC,1.5,4.806,1.498,271.0,N/A,PASS,PENDING
2026-09-17 15:34:57,4412,1,SKYFALL JIG Mode,TBTC,2.5,4.624,2.505,453.0,N/A,PASS,PENDING
2026-09-17 15:35:04,4412,1,SKYFALL JIG Mode,TBTC,3.0,4.53,3.003,547.0,N/A,PASS,PENDING
2026-09-17 15:35:09,4412,1,SKYFALL JIG Mode,TBTC,3.6,0.002,0.0,5075.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:35:18,4412,1,SKYFALL JIG Mode,TBTC,0.0,5.076,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:35:19,4412,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:35:38,4412,1,SKYFALL JIG Mode,TBTD,1.5,4.863,1.497,259.0,N/A,PASS,PENDING
2026-09-17 15:35:46,4412,1,SKYFALL JIG Mode,TBTD,2.5,4.686,2.499,436.0,N/A,PASS,PENDING
2026-09-17 15:35:53,4412,1,SKYFALL JIG Mode,TBTD,3.0,4.594,3.003,528.0,N/A,PASS,PENDING
2026-09-17 15:35:57,4412,1,SKYFALL JIG Mode,TBTD,3.6,0.003,0.0,5119.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:36:07,4412,1,SKYFALL JIG Mode,TBTD,0.0,5.122,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:36:08,4412,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:36:57,4421,1,SKYFALL JIG Mode,TBTB,1.5,4.838,1.382,267.0,N/A,PASS,PENDING
2026-09-17 15:37:04,4421,1,SKYFALL JIG Mode,TBTB,2.5,4.661,2.498,444.0,N/A,PASS,PENDING
2026-09-17 15:37:12,4421,1,SKYFALL JIG Mode,TBTB,3.0,4.566,3.0,539.0,N/A,PASS,PENDING
2026-09-17 15:37:16,4421,1,SKYFALL JIG Mode,TBTB,3.6,0.001,0.0,5104.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:37:25,4421,1,SKYFALL JIG Mode,TBTB,0.0,5.104,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:37:26,4421,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:37:44,4421,1,SKYFALL JIG Mode,TBTC,1.5,4.811,1.496,265.0,N/A,PASS,PENDING
2026-09-17 15:37:52,4421,1,SKYFALL JIG Mode,TBTC,2.5,4.631,2.502,445.0,N/A,PASS,PENDING
2026-09-17 15:37:59,4421,1,SKYFALL JIG Mode,TBTC,3.0,4.538,3.0,538.0,N/A,PASS,PENDING
2026-09-17 15:38:04,4421,1,SKYFALL JIG Mode,TBTC,3.6,0.001,0.0,5075.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:38:14,4421,1,SKYFALL JIG Mode,TBTC,0.0,5.077,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:38:15,4421,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:38:34,4421,1,SKYFALL JIG Mode,TBTD,1.5,4.866,1.502,255.0,N/A,PASS,PENDING
2026-09-17 15:38:42,4421,1,SKYFALL JIG Mode,TBTD,2.5,4.69,2.501,431.0,N/A,PASS,PENDING
2026-09-17 15:38:49,4421,1,SKYFALL JIG Mode,TBTD,3.0,4.601,2.998,520.0,N/A,PASS,PENDING
2026-09-17 15:38:54,4421,1,SKYFALL JIG Mode,TBTD,3.6,0.004,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:39:03,4421,1,SKYFALL JIG Mode,TBTD,0.0,5.12,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:39:04,4421,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:39:44,4422,1,SKYFALL JIG Mode,TBTB,1.5,4.838,1.5,267.0,N/A,PASS,PENDING
2026-09-17 15:39:52,4422,1,SKYFALL JIG Mode,TBTB,2.5,4.657,2.5,448.0,N/A,PASS,PENDING
2026-09-17 15:39:59,4422,1,SKYFALL JIG Mode,TBTB,3.0,4.563,3.004,542.0,N/A,PASS,PENDING
2026-09-17 15:40:04,4422,1,SKYFALL JIG Mode,TBTB,3.6,0.003,0.0,5102.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:40:13,4422,1,SKYFALL JIG Mode,TBTB,0.0,5.109,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:40:14,4422,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:40:33,4422,1,SKYFALL JIG Mode,TBTC,1.5,4.808,1.5,270.0,N/A,PASS,PENDING
2026-09-17 15:40:40,4422,1,SKYFALL JIG Mode,TBTC,2.5,4.629,2.499,449.0,N/A,PASS,PENDING
2026-09-17 15:40:48,4422,1,SKYFALL JIG Mode,TBTC,3.0,4.536,2.997,542.0,N/A,PASS,PENDING
2026-09-17 15:40:52,4422,1,SKYFALL JIG Mode,TBTC,3.6,0.001,0.0,5077.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-17 15:41:04,4422,1,SKYFALL JIG Mode,TBTC,0.0,5.075,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:41:05,4422,1,SKYFALL JIG Mode,TBTC,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-17 15:41:25,4422,1,SKYFALL JIG Mode,TBTD,1.5,4.864,1.5,259.0,N/A,PASS,PENDING
2026-09-17 15:41:32,4422,1,SKYFALL JIG Mode,TBTD,2.5,4.688,2.503,435.0,N/A,PASS,PENDING
2026-09-17 15:41:40,4422,1,SKYFALL JIG Mode,TBTD,3.0,4.6,3.003,523.0,N/A,PASS,PENDING
2026-09-17 15:41:42,4422,1,SKYFALL JIG Mode,TBTD,3.5,0.112,0.0,5011.0,TRIPPED @ 3.5A,PASS,PENDING
2026-09-17 15:42:19,4422,1,SKYFALL JIG Mode,TBTD,0.0,5.125,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-17 15:42:20,4422,1,SKYFALL JIG Mode,TBTD,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-18 15:32:49,1,BATTERY_TEST,Battery Cycling Mode,BATTERY,2.0,0.0,0.0,0.0,"Ah=0.0000,Wh=0.0000",PASS,PASS
2026-09-18 15:41:33,1,BATTERY_TEST,Battery Cycling Mode,BATTERY,2.0,0.0,0.0,0.0,"Ah=0.0000,Wh=0.0000",PASS,PASS
2026-09-18 15:50:40,DC_source1,BATTERY_TEST,Battery Cycling Mode,BATTERY,0.5,0.0,0.0,0.0,"Ah=0.0126,Wh=0.0501",PASS,PASS
2026-09-18 16:26:29,demo,BATTERY_TEST,Battery Cycling Mode,BATTERY,2.0,0.0,0.0,0.0,"Ah=0.0383,Wh=0.1287",PASS,PASS
2026-09-18 17:12:25,1,BATTERY_TEST,Battery Cycling Mode,BATTERY,2.0,0.0,0.0,0.0,"Ah=0.0106,Wh=0.0444",PASS,PASS,313.598
2026-09-21 14:35:31,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,1.5,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:36:36,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,3.0,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:38:32,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,3.0,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:39:04,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,1.5,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:39:49,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,1.5,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:40:21,3,DIRECT_NO_JIG,FA Direct Mode,DIRECT,3.0,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:42:33,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,3.0,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:43:08,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,1.5,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:43:36,2,DIRECT_NO_JIG,FA Direct Mode,DIRECT,1.5,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:44:03,3,DIRECT_NO_JIG,FA Direct Mode,DIRECT,3.0,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:44:29,3,DIRECT_NO_JIG,FA Direct Mode,DIRECT,3.0,0.0,0.0,0.0,N/A,FAIL,FAIL,
2026-09-21 14:46:26,1,DIRECT_NO_JIG,FA Direct Mode,DIRECT,1.5,0.002,0.0,0.0,N/A,FAIL,FAIL,
2026-09-22 09:07:20,1,1,SKYFALL JIG Mode,TBTB,1.5,4.852,1.5,270.0,N/A,PASS,PENDING
2026-09-22 09:07:27,1,1,SKYFALL JIG Mode,TBTB,2.5,4.671,2.5,451.0,N/A,PASS,PENDING
2026-09-22 09:07:34,1,1,SKYFALL JIG Mode,TBTB,3.0,4.578,3.002,544.0,N/A,PASS,PENDING
2026-09-22 09:07:39,1,1,SKYFALL JIG Mode,TBTB,3.6,0.005,0.0,5117.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-22 09:08:01,1,1,SKYFALL JIG Mode,TBTB,0.0,5.121,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-22 09:08:02,1,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
2026-09-22 09:09:06,123,1,SKYFALL JIG Mode,TBTB,1.5,4.854,1.503,267.0,N/A,PASS,PENDING
2026-09-22 09:09:14,123,1,SKYFALL JIG Mode,TBTB,2.5,4.675,2.5,446.0,N/A,PASS,PENDING
2026-09-22 09:09:21,123,1,SKYFALL JIG Mode,TBTB,3.0,4.582,2.997,539.0,N/A,PASS,PENDING
2026-09-22 09:09:25,123,1,SKYFALL JIG Mode,TBTB,3.6,0.003,0.0,5118.0,TRIPPED @ 3.6A,PASS,PENDING
2026-09-22 09:09:49,123,1,SKYFALL JIG Mode,TBTB,0.0,5.12,0.0,0.0,RECOVERY,PASS,PENDING
2026-09-22 09:09:50,123,1,SKYFALL JIG Mode,TBTB,0.0,0.0,0.0,0.0,N/A,DONE,PASS
</file>

<file path="README_CHT.md">
# DL24 生產線自動化測試工具

## 1. 專案目的

本工具以 Python Tkinter 建立 DL24 電子負載測試介面，透過串列埠控制 Atorch DL24，執行 PCBA 電源輸出與保護功能測試。

主要目標如下：

- 連線並控制 DL24 電子負載。
- 支援 PCBA S/N、JIG ID 與測試模式等資料追蹤。
- 以圖形介面即時顯示測試中的電壓、電流、測試步驟與結果。
- 將每個測試步驟及最終結果寫入 CSV，供生產追溯與後續分析。
- 將測試條件放在 `test_config.json`，讓測試規格可以獨立調整。

## 2. 主要檔案

| 檔案 | 說明 |
| --- | --- |
| `dl24_autotest_02.py` | 主程式，提供 GUI、測試流程、DL24 控制與結果判定。 |
| `test_config.json` | 測試參數與判定門檻設定檔。 |
| `dl24_lib/` | DL24 通訊控制模組，至少需要包含 `__init__.py`。 |
| `production_test_datalog.csv` | 測試結果紀錄檔，程式會以附加方式寫入。 |

備份或移植專案時，應保留主程式、`test_config.json`、`dl24_lib/` 以及既有的 CSV 紀錄。只複製主程式可能造成通訊模組或測試條件遺失。

## 3. 測試模式

### 3.1 FA Direct Mode

此模式適合單一負載條件的直接測試。使用者可以在介面中輸入：

- `Current (A)`：目標負載電流。
- `Duration (Sec)`：負載持續時間。
- `Vmin (V)`：允許的最低輸出電壓。
- `Vmax (V)`：允許的最高輸出電壓。

執行流程：

1. 設定 DL24 負載電流並開啟輸出。
2. 維持設定時間。
3. 讀取測試結束時的電壓與電流。
4. 當 `Vmin <= 測量電壓 <= Vmax` 時判定為 `PASS`，否則為 `FAIL`。
5. 關閉 DL24 並寫入測試紀錄。

FA 模式會將 JIG ID 自動設為 `DIRECT_NO_JIG`，不需要輸入治具編號。

### 3.2 SKYFALL JIG Mode

此模式用於搭配治具逐一測試連接埠 `TBTB`、`TBTC`、`TBTD`。

每個連接埠的測試流程如下：

1. 在 0 A 狀態讀取空載電壓 `V_idle`。
2. 依設定執行固定電流步階，預設為 `1.5 A`、`2.5 A`、`3.0 A`。
3. 在 3.0 A 時依照設定的電壓門檻判定 `PASS`、`BORDERLINE` 或 `FAIL`。
4. 執行動態 OCP 電流爬升，預設從 `3.5 A` 開始，逐步增加至 `4.0 A`。
5. 當輸出電壓降至 OCP 觸發門檻以下時，判定 eFuse 已觸發。
6. 關閉負載，提示使用者重新插拔 Type-C 端子，使 eFuse 復歸。
7. 讀取復歸電壓；達到 `RECOVERY_MIN_VOLT` 時判定復歸成功。
8. 將該連接埠的測試結果寫入 CSV。

選擇所有連接埠時，每測試完一個連接埠，程式會提示使用者將測試線移至下一個連接埠。

## 4. `test_config.json` 的用途

`test_config.json` 是外部測試設定檔，用來保存測試電流、等待時間、電壓門檻與 OCP 條件。程式啟動時會從主程式所在資料夾讀取這個檔案。

使用設定檔的原因：

- 不必為了調整產品規格而修改 Python 程式碼。
- 不同產品或治具可以使用不同的測試門檻。
- 測試條件集中管理，方便審查、備份與版本追蹤。
- 可降低直接修改測試流程程式碼而造成其他功能異常的風險。
- 備份設定檔即可保留當時實際使用的測試規格，避免日後只剩程式卻無法重現測試條件。

若 `test_config.json` 不存在，程式會依照內建的 `DEFAULT_CONFIG` 自動建立一份預設設定檔。若 JSON 格式無法讀取，程式會暫時使用內建預設值；正式測試前仍應修正設定檔格式，並確認實際門檻符合產品規格。

### 4.1 設定欄位說明

#### `SKYFALL_JIG_MODE`

| 欄位 | 說明 |
| --- | --- |
| `STEPS` | 固定電流測試步階，單位為 A。 |
| `STEP_DURATION_SEC` | 每個固定電流步階的持續秒數。 |
| `V3_0A_PASS_MIN` | 3.0 A 測試判定為 PASS 的最低電壓。 |
| `V3_0A_BORDERLINE_MIN` | 3.0 A 測試判定為 BORDERLINE 的最低電壓。低於此值為 FAIL。 |
| `OCP_START_CURRENT` | OCP 測試的起始電流，單位為 A。 |
| `OCP_MAX_CURRENT` | OCP 測試允許爬升到的最大電流，單位為 A。 |
| `OCP_STEP_CURRENT` | OCP 每次增加的電流，單位為 A。 |
| `OCP_TRIP_MAX_VOLT` | 判定 eFuse 觸發的最高電壓，單位為 V。 |
| `RECOVERY_MIN_VOLT` | eFuse 復歸成功所需的最低電壓，單位為 V。 |

#### `FA_DIRECT_MODE`

| 欄位 | 說明 |
| --- | --- |
| `DEFAULT_CURRENT` | FA 模式介面預設電流，單位為 A。 |
| `DEFAULT_DURATION` | FA 模式介面預設測試時間，單位為秒。 |
| `DEFAULT_VMIN` | FA 模式介面預設最低允許電壓，單位為 V。 |
| `DEFAULT_VMAX` | FA 模式介面預設最高允許電壓，單位為 V。 |

### 4.2 修改設定檔注意事項

- 檔案必須是合法 JSON，字串使用雙引號。
- 欄位名稱必須與程式預期名稱完全一致。
- 電流、電壓與時間應使用數值，不要加入單位文字，例如使用 `4.75`，不要使用 `"4.75V"`。
- 修改後重新啟動程式才會載入新設定。
- 變更判定門檻前，應確認產品規格與測試安全條件。

## 5. 安裝環境

建議使用 Python 3.9 以上版本。此工具使用 Python 標準函式庫中的 Tkinter、threading、csv、json 與 os，另外需要安裝 `pyserial` 以進行串列埠通訊。

在 Windows PowerShell 執行：

```powershell
python -m pip install pyserial
```

確認 DL24 使用的 COM Port，例如 `COM3`，以及正確的 Baud Rate。程式目前預設使用 `COM3` 與 `9600`，但仍應依實際設備設定確認。

## 6. 啟動方式

請在專案資料夾中執行：

```powershell
python .\dl24_autotest_02.py
```

啟動後的基本操作：

1. 確認 DL24 已連接電腦並開機。
2. 輸入正確的 COM Port 與 Baud Rate。
3. 選擇 `FA Direct Mode` 或 `SKYFALL JIG Mode`。
4. 輸入 PCBA S/N；SKYFALL 模式另需輸入 JIG ID。
5. SKYFALL 模式選擇測試所有連接埠或單一連接埠。
6. 按下 `START` 開始測試。
7. 測試完成後，在程式所在資料夾查看 `production_test_datalog.csv`。

## 7. 測試紀錄

`production_test_datalog.csv` 會以 UTF-8 編碼保存以下欄位：

```text
Timestamp, PCBA_SN, JIG_ID, Test_Mode, Port_ID,
Step_Current_A, Measured_Volt_V, Measured_Curr_A, Vdrop_mV,
OCP_Status, Step_Result, Final_Port_Result
```

每次測試會追加資料，不會覆蓋既有紀錄。若需要開始新的批次，建議先備份或重新命名既有 CSV，再啟動程式。

## 8. 注意事項

- 測試前確認負載線、Type-C 線材、治具與被測 PCBA 已正確連接。
- OCP 測試可能觸發 eFuse 保護，請依畫面提示完成重新插拔與復歸操作。
- 測試中若需要停止，請按下 `STOP`；程式會嘗試將電流設為 0 A 並關閉 DL24。
- 不要在測試進行中拔除通訊線或任意修改 `test_config.json`。
- 請保留與程式版本相對應的 `test_config.json`，以確保歷史測試結果可重現。
</file>

<file path="README.md">
# DL24 Production ATE v6.0

## Hardware
- Use 4-pin Kelvin sensing for DL24 load wiring.
- Place the NTC probe firmly on the battery cell or hottest expected surface.
- Install the CH340 USB serial driver when Windows does not enumerate the adapter.

## Configuration
`test_config.json` contains current, cutoff voltage, temperature, rest duration, sampling interval, and DCIR settings.

## Distribution
The application stores configuration and CSV/PNG logs beside the executable. PyInstaller `--onefile` and `--onedir` deployments are supported.
</file>

<file path="RELEASE_NOTES.md">
# Release Notes

- v1.0: Race Lee's seven questions and JIG IR-drop production checks.
- v5.0: Single-pass battery discharge, OCV recovery, watchdog, and charts.
- v6.0: Battery DCIR, high-DPI responsive UI, connection menu, anti-sleep, single-instance lock, and deployment path anchoring.
</file>

<file path="test_config.json">
{
  "SKYFALL_JIG_MODE": {
    "STEPS": [
      1.5,
      2.5,
      3.0
    ],
    "STEP_DURATION_SEC": 5,
    "V3_0A_PASS_MIN": 4.52,
    "V3_0A_BORDERLINE_MIN": 4.47,
    "OCP_START_CURRENT": 3.5,
    "OCP_MAX_CURRENT": 4.0,
    "OCP_STEP_CURRENT": 0.1,
    "OCP_TRIP_MAX_VOLT": 1.0,
    "RECOVERY_MIN_VOLT": 4.75
  },
  "FA_DIRECT_MODE": {
    "DEFAULT_CURRENT": 1.0,
    "DEFAULT_DURATION": 5,
    "DEFAULT_VMIN": 4.75,
    "DEFAULT_VMAX": 5.25
  },
  "BATTERY_CYCLE_MODE": {
    "DEFAULT_MODE": "CC",
    "DISCHARGE_CURRENT_A": 2.0,
    "CUTOFF_VOLTAGE_V": 3.0,
    "OVER_TEMP_LIMIT_C": 55.0,
    "REST_TIME_SEC": 900,
    "SAMPLING_INTERVAL_SEC": 1.0,
    "DCIR_CALC_ENABLE": true
  }
}
</file>

</files>
