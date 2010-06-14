#!/usr/bin/python
from socket import socket, AF_INET,SOCK_DGRAM,IPPROTO_UDP,SOL_SOCKET,SO_REUSEADDR,IP_MULTICAST_TTL,IP_MULTICAST_LOOP,INADDR_ANY,inet_aton,IP_ADD_MEMBERSHIP,IPPROTO_IP
import random
import sys,signal
import struct
from select import select
from threading import Thread
from mc_remote import remoteParser
from mc_local import localParser
#defaults
GROUP = '224.110.42.23'
PORT  = 42023
CLIENTNAME = "Bob Ross"
MCMESSAGE="/hello \"%s\" Says Hello! \"%s\""
# end defaults
var = None
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
        self.localParser= localParser(self)
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
        self.localParser.nick((self.nick,))
    def send(self,msg=""):
        if msg.startswith('/'):
            ret= self.localParser.parse(msg) 
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
        """
        public function, wrapper for _cleanup, which is used for
        the signal and does what we need to have
        """
        self._cleanup(1,2)
    def _cleanup(self,sig,frame):
        '''
        cleans up the socket and kills the read-thread
        '''
        print "cleaning up"
        # we need this to stop the thread
        self.rcvthread.killfunct()
        self.rcvthread.join(1)
        self.s.close()
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
        self.remoteParser= remoteParser(self.chat)
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
    chat = chatter()
    signal.signal(signal.SIGINT,chat._cleanup)
    registerChat(chat)
    chat.initSocket()
    chat.threadedRecv()
    while 1:
        try:
            msg = raw_input()
            chat.send(msg)
        except KeyboardInterrupt:
            chat.cleanup()
            break

def registerChat(chat):
    """ registers ONE global variable, needed for the chat """
    global glob
    glob = chat

def cleanup(chat):
    global glob
    glob.cleanup()

if __name__ == "__main__":
    main()
