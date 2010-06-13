#!/usr/bin/python
from socket import *
import random
import sys,signal
import struct
import mc_parser
from select import select
from threading import Thread
import mc_remote
import logging
#defaults
GROUP = '224.110.42.23'
PORT  = 42023
CLIENTNAME = "Bob Ross"
MCMESSAGE="/hello \"%s\" Says Hello! \"%s\""
chat=None
# end defaults
class chatter():
    '''
        initializes a chat socket
    '''
    def __init__ ( self, group=GROUP, port=PORT, nick=CLIENTNAME):
        '''
        the chatter class provides a number of parameters
        first is the multicast group, second is the ip and port
        the nick 
        iplist provides a dictionary for mapping ip-addresses to a nick name
        a local parser will be instanciated
        the variable beep tells if the client should beep or not
        '''
        self.group=group
        self.ip=None
        self.port=port
        self.nick=nick
        self.iplist =  {}
        self.ownParser= mc_parser.ownParser(self)
        self.beep = False
        self.espeak = True
        self.gram= {}
        self.files = {}
        self.out_files = {}
    
    def send_mc(self,arg):
        self.s.sendto("%s" %
                arg,0,(self.group,self.port))
    def gset(self,key,value):
        """
        here you may want to add some persistency stuff
        """
        self.gram[key] = value
    def gget(self,key):
        """
        persistency goes here
        """
        return self.gram.get(key,None)

        pass
    def initSocket (self,rcv=1):
        '''
        Initializes a Multicast socket
        additionally it will send an ip_add_membership
        a random seed will be generated for the /hello message

        '''
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

        # seeds 
        random.seed()
        # generate seed
        self.rnd = random.randint(42,23000)
        self.s.sendto(MCMESSAGE % ( self.nick, self.rnd),0, (self.group,self.port))
        self.ownParser.nick((self.nick,))
    def send(self,msg=""):
        if msg.startswith('/'):
            ret= self.ownParser.parse(msg) 
            if ret is not None:
                print ret
        else:
            """
            this is the default case
            """
            self.s.sendto("/echo %s" %msg,0,(self.group,self.port))

    def resolveNick(self,ip):
        '''
        Tries to resolve an ip-addres to a  nickname via the 
        iplist dictionary. if the ip-address is unkown to the
        local host, the ip will be returned
        '''
        return self.iplist[ip].nick if ip in self.iplist else ip
        

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
        '''
        cleans up the socket and kills the read-thread
        '''
        print "cleaning up"
        # we need this to stop the thread
        self.rcvthread.killfunct()
        self.rcvthread.join(1)
        self.s.close()
        
def handler(signum,frame):
    '''
    handler for SIGINT
    '''
    print "shutting down"
    global chat
    chat.cleanup()
    sys.exit()





class printThread(Thread):
    '''
    Printing thread which is able to stop
    '''
    def __init__(self,sock,chat):
        '''
        constructor for printing Loop

        the chat is the reference to the original chat object
        a remote parser will be instanciated
        '''
        Thread.__init__(self)
        self.s=sock
        self.stop=0
        self.chat=chat
        self.remoteParser= mc_remote.remoteParser(self.chat)
    def run(self,*args):
        '''
        Thread function
        It is able to stop via setting self.stop to 1
        It will wait for a max of 1 second on a socket
        via select. 
        If the text received is a command ( /bla )
        it will be evaulated and eventually executed
        '''
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
                        """
                        default case : no /command
                        """
                        print "%s: %s"%(self.chat.resolveNick(addr[0]), data)
    def requeststop(self):
        '''
        sets stop to 1
        '''
        self.stop=1
def main():
    global chat
    chat = chatter()
    signal.signal(signal.SIGINT,handler)
    chat.initSocket()
    chat.threadedRecv()
    while 1:
        try:
            msg = raw_input()
            chat.send(msg)
        except KeyboardInterrupt:
            chat.cleanup()
            break

if __name__ == "__main__":
    main()
