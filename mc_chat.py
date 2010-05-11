#!/usr/bin/env python
from socket import * #@UnusedWildImport
import select
import struct
from threading import Thread
import sys
# default values
GROUP = '224.110.42.23'
PORT  = 42023
CLIENTNAME = "Bob Ross"
MCMESSAGE="%s Says Hello!" 
# end defaults
class myThread(Thread):
    def __init__(self,sock):
        Thread.__init__(self)
        self.s = sock

    def run(self):
        print "Start reading:"
class chatter():
    '''
        initializes a chat socket
    '''
    def __init__ ( self, group=GROUP, port=PORT, nick=CLIENTNAME):
        self.group=group
        self.port=port
        self.nick=nick
    def initSocket (self,rcv=1):
        host = ''
        self.s = socket(AF_INET,SOCK_DGRAM,  IPPROTO_UDP)
        self.s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        #s.setsockopt(SOL_SOCKET,socket.SO_REUSEPORT,1)
        self.s.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, 32)
        self.s.setsockopt(IPPROTO_IP,IP_MULTICAST_LOOP,1)
        # just send or also recieve
        if rcv==1:
            self.s.bind((host,PORT))
            mreq = struct.pack("4sl", inet_aton(GROUP), INADDR_ANY)
            self.s.setsockopt(IPPROTO_IP,IP_ADD_MEMBERSHIP,mreq)
        # anouncement message
        self.s.sendto(MCMESSAGE % self.nick,0, (self.group,self.port))

    def send(self,msg=""):
        self.s.sendto("%s: %s" %(self.nick,msg),0,(self.group,self.port))
    def printloop(self):
        while 1:
            ready,output,exception = select.select([self.s],[],[],2) # try every 2 seconds 
            for r in ready:
                if r == self.s:
                    (data,addr) = self.s.recvfrom(1024)
                    print data
    def threadedRecv(self,funct=None,arg=()):
        if funct == None:
            funct = self.printloop
            arg=(self,)
        t_f1 = Thread(target=funct,args=arg)
        t_f1.start()
        

def main():
    chat = chatter()
    chat.initSocket()
    chat.threadedRecv()
    while 1:
        msg = raw_input()
        chat.send(msg)


if __name__ == "__main__":
    main()
