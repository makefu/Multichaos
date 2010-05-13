#!/usr/bin/python
from socket import * #@UnusedWildImport
from select import select
import struct
from threading import Thread
import sys,signal,os
import subprocess
import random


# default values
GROUP = '224.110.42.23'
PORT  = 42023
CLIENTNAME = "Bob Ross"
MCMESSAGE="/hello %s Says Hello! %s"
chat=None
# end defaults


# our printThread is able to stop ( which is important!)
class parser():
    def __init__(self,chat):
        self.chat = chat

class ownParser(parser):
    def __init__(self,chat):
        parser.__init__(self,chat)
    def rot13(self,args):
        self.chat.s.sendto("/rot13 %s" % 
                args.encode('rot13') ,0,(self.chat.group,self.chat.port))
        return "Encoded to %s" % (args.encode('rot13'))
    def help(self,args):
        return "this is the help file you appended %s" % args
    def flushnicks(self,args):
        self.chat.iplist.clear()
        return "nicks flushed"
    def nick(self,args):
        self.chat.s.sendto("/nick %s" % 
                args ,0,(self.chat.group,self.chat.port))
        #return "You are now known as %s" % args
    def beep(self,args):
        self.chat.s.sendto("/beep %s" % 
                args ,0,(self.chat.group,self.chat.port))
    def togglebeep(self,args):
        self.chat.beep=not self.chat.beep
        return "Beep is now ",self.chat.beep 
    def parse(self,cmd):
        cmd = cmd[1:]
        funct = cmd.split()[0]
        #print cmd
        try:
            return getattr(self,funct)(' '.join(cmd.split()[1:]))
        except:
            return "no such command '/%s' : %s" %(cmd,sys.exc_info()[0])
class remoteParser(parser):
    def __init__(self,chat):
        parser.__init__(self,chat)
    def nick(self,args,addr):
        msg = "'%s' now known as '%s'" % (self.chat.resolveNick(addr[0]),args)
        self.chat.iplist[addr[0]] = args 
        return  msg
    def rot13(self,args,addr):
        return "%s : rot13 : %s" % (self.chat.resolveNick(addr[0]),
                args.encode('rot13'))
    def hello(self,args,addr):
        
        #print '%s'%args.split()[-1] == '%d'%self.chat.rnd
        #print int('%s'%args.split()[-1]) == self.chat.rnd

        if int(args.split()[-1]) == self.chat.rnd and self.chat.ip is None:
            print "challenge succeeded. Found your IP: %s"%addr[0]
            self.chat.ip=addr[0]
        else:
            return "/hello from %s : %s" % (addr[0],args)

    def beep(self,args,addr):
        if self.chat.beep==False:
            return "beeping is turned of, ignoring request from %s with freq/length %s"% (addr[0],args)
        cmd = [ "/usr/bin/beep" ]
        arg = args.split()
        #print arg, len(arg)
        if len(arg) >= 1:
            cmd.append("-f%s"%arg[0])
        if len(arg) >= 2:
            try:
                length = int(arg[1])
            except:
                print "malformed length %s" %sys.exc_info()[0]
                length = 100

            if length > 1000:
                length = 1000

            cmd.append("-l%d"%length)
        p = subprocess.Popen(cmd)
        return "%s demands beep (%s)" % (self.chat.resolveNick(addr[0]) ,args)
    def parse(self,cmd,addr):
        cmd = cmd[1:]
        funct = cmd.split()[0]
        #print cmd
        #print ' '.join(cmd.split()[1:]),addr
        try:
            return getattr(self,funct)(' '.join(cmd.split()[1:]),addr)
        except:
            return "no such command '/%s' : %s" %(cmd,sys.exc_info()[0])

class printThread(Thread):
    '''
    Printing thread which is able to stop
    '''
    def __init__(self,sock,chat):
        Thread.__init__(self)
        self.s=sock
        self.stop=0
        self.chat=chat
        self.remoteParser= remoteParser(self.chat)
    def run(self,*args):
        while 1:
            # break if we do not want to loop on
            if self.stop == 1:
                print "stopping"
                break
            ready,output,exception = select([self.s],[],[],1) # try every second
            for r in ready:
                if r == self.s:
                    (data,addr) = self.s.recvfrom(1024)
                    if data.startswith('/'):
                        ret=self.remoteParser.parse(data,addr)
                        if ret is not None:
                            print "%s" %ret
                    else:
                        print "%s: %s"%(self.chat.resolveNick(addr[0]), data)
    def requeststop(self):
        self.stop=1

class chatter():
    '''
        initializes a chat socket
    '''
    def __init__ ( self, group=GROUP, port=PORT, nick=CLIENTNAME):
        self.group=group
        self.ip=None
        self.port=port
        self.nick=nick
        self.iplist =  { }
        self.ownParser= ownParser(self)
        self.beep = False
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
        random.seed()
        self.rnd = random.randint(42,32000)
        self.s.sendto(MCMESSAGE % ( self.nick, self.rnd),0, (self.group,self.port))
        self.ownParser.nick(self.nick)
    def send(self,msg=""):
        if msg.startswith('/'):
            ret= self.ownParser.parse(msg) 
            if ret is not None:
                print ret
        else:
            self.s.sendto("%s" %msg,0,(self.group,self.port))

    def resolveNick(self,ip):
        if ip in self.iplist:
            return self.iplist[ip]
        else:
            return ip

    #########################
    # boring stuff from here:
    ##########################

    def threadedRecv(self,cl=None,killthreadfunct=None):
        '''
        cl is the class which should be started ( shall be a class extending Thread )
        killthreadfunction is the function which we use to kill the thread
        We need to know which the function is to kill the thread
        '''
        # thread into receiveloop
        if cl==None:
            self.rcvthread=printThread(self.s,self)
        else:
            self.rcvthread=cl

        if killthreadfunct==None:
            self.rcvthread.killfunct=self.rcvthread.requeststop
        else:
            self.rcvthread.killfunct=killthreadfunct

        self.rcvthread.start()
        
    def cleanup(self):
        print "cleaning up"
        # we need this to stop the thread
        self.rcvthread.killfunct()
        self.rcvthread.join(1)
        self.s.close()
        
def handler(signum,frame):
    print "shutting down"
    global chat
    chat.cleanup()
    sys.exit()



def main():
    global chat
    chat = chatter()
    signal.signal(signal.SIGINT,handler)
    chat.initSocket()
    chat.threadedRecv()
    while 1:
        try:
            msg = raw_input()
            #msg = sys.stdin.readline()
            chat.send(msg)
        except KeyboardInterrupt:
            chat.cleanup()
            break

if __name__ == "__main__":
    main()
