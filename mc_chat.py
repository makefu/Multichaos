#!/usr/bin/env python
from socket import * #@UnusedWildImport
import select
import struct
from threading import Thread
GROUP = '224.110.42.23'
PORT  = 42023
CLIENTNAME = "Bob Ross"
MCMESSAGE="%s Says Hello!" % CLIENTNAME
class myThread(Thread):
    def __init__(self,sock):
        Thread.__init__(self)
        self.s = sock

    def run(self):
        print "Start reading:"
        while 1:
            ready,output,exception = select.select([self.s],[],[],2) # try every 2 seconds 
            for r in ready:
                if r == self.s:
                    (data,addr) = self.s.recvfrom(1024)
                    print data
            
        

def hack():
    host = ''
    s = socket(AF_INET,SOCK_DGRAM,  IPPROTO_UDP)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    #s.setsockopt(SOL_SOCKET,socket.SO_REUSEPORT,1)
    
    s.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, 32)
    s.setsockopt(IPPROTO_IP,IP_MULTICAST_LOOP,1)
    s.bind((host,PORT))
    mreq = struct.pack("4sl", inet_aton(GROUP), INADDR_ANY)
    s.setsockopt(IPPROTO_IP,IP_ADD_MEMBERSHIP,mreq)
    s.sendto(MCMESSAGE ,0,(GROUP,PORT))
    th = myThread(s)
    th.start()
    while 1:
        print "Start writing:"
        msg = raw_input()
        s.sendto("%s: %s" %(CLIENTNAME,msg) ,0,(GROUP,PORT))

hack()
