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
    '''
    generic parser class
    depricated
    '''
    def __init__(self,chat):
        self.chat = chat

class ownParser(parser):
    '''
    parses local command calls ( like /nick or /togglebeep )
    initial parsing is done with the "parse" function"
    it will evaluate the function given and tries to call
    the function with that name

    '''
    def __init__(self,chat):
        parser.__init__(self,chat)
    def rot13(self,args):
        '''
        rot13 encrypts a given text and sends it over the line
        magic is done via string.encode('rot13')
        the string is written into the multicast channel
        '''
        self.chat.s.sendto("/rot13 %s" % 
                args.encode('rot13') ,0,(self.chat.group,self.chat.port))
        return "Encoded to %s" % (args.encode('rot13'))
    def help(self,args):
        '''
        dummy function
        needs args as argument ( because of parsing )
        returns a status ( or message) string
        if the return string is 'None', the string will not be printed
        '''
        return "this is the help file you appended %s" % args
    def flushnicks(self,args):
        '''
        flushes the nick table
        '''
        self.chat.iplist.clear()
        return "nicks flushed"
    def nick(self,args):
        '''
        writes our new nick onto the line
        '''

        self.chat.s.sendto("/nick %s" % 
                args ,0,(self.chat.group,self.chat.port))
        #return "You are now known as %s" % args
    def espeak(self,args):
        self.chat.s.sendto("/espeak %s" % 
                args ,0,(self.chat.group,self.chat.port))
    def beep(self,args):
        '''
        sends beep to the multicast group
        '''
        self.chat.s.sendto("/beep %s" % 
                args ,0,(self.chat.group,self.chat.port))
    def togglebeep(self,args):
        '''
        toggles beep on or off
        this is important when to read remote beep commands
        These can be turned on or off with this command
        '''
        self.chat.beep=not self.chat.beep
        return "Beep is now ",self.chat.beep 
    def toggleespeak(self,args):
        self.chat.espeak=not self.chat.espeak
        return "Espeak is now ",self.chat.espeak
    def caps(self,cmd,addr):
        return "not yet implemented!"
    def parse(self,cmd):
        '''
        parses a command string  
        looks like: /beep 1000 200

        it will try/catch unknown commands
        '''
        cmd = cmd[1:]
        funct = cmd.split()[0]
        #print cmd
        try:
            return getattr(self,funct)(' '.join(cmd.split()[1:]))
        except:
            return "no such command '/%s' : %s" %(cmd,sys.exc_info()[0])
class remoteParser(parser):
    '''
    parses commands received over the Multicast link and evaluate them
    '''
    def __init__(self,chat):
        parser.__init__(self,chat)
    def nick(self,args,addr):
        '''
        the nick will be associated with the ip-address the message it is from
        the iplist associated will be changed for that
        '''
        msg = "'%s' now known as '%s'" % (self.chat.resolveNick(addr[0]),args)
        self.chat.iplist[addr[0]] = args 
        return  msg
    def rot13(self,args,addr):
        '''
        rot13 decodes text with command /rot13 encryption
        '''
        return "%s : rot13 : %s" % (self.chat.resolveNick(addr[0]),
                args.encode('rot13'))
    def hello(self,args,addr):
        '''
        tries to parse a hello message to find own IP
        it will contain a challenge cookie which will be tested
        against the generated one.
        This should happen only once ( at beginning of the session)

        if the challenge is not taken, the message will be printed out
        '''
        #print '%s'%args.split()[-1] == '%d'%self.chat.rnd
        #print int('%s'%args.split()[-1]) == self.chat.rnd

        if int(args.split()[-1]) == self.chat.rnd and self.chat.ip is None:
            print "challenge succeeded. Found your IP: %s"%addr[0]
            self.chat.ip=addr[0]
        else:
            return "hello from %s : %s" % (addr[0],args)

    def beep(self,args,addr):
        '''
        Parses beep messages
        These may contain a frequency and a length
        The parameters  will be passed to the "beep" program with the
        corresponding flags
        '''
        if self.chat.beep==False:
            return "beeping is turned off, ignoring request from %s with freq/length %s"% (addr[0],args)
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

    def espeak(self,args,addr):
        if self.chat.espeak==False:
            return "espeak is turned off,ignoring request from %s with args %s" % (addr[0], args)
        cmd = [ "/usr/bin/espeak" ]
        cmd.append(args)
        p = subprocess.Popen(cmd)
        return "%s demands '%s'" %(self.chat.resolveNick(addr[0]),args)
    def caps(self,cmd,addr):
        '''
        writes the capabilities to the multicast channel
        
        not yet implemented.
        '''
        return "not yet implemented!"
    def parse(self,cmd,addr):
        '''
        parses a message

        the message should contain a function and a number of 
        parameters together in one string:
        /beep 1000 230
        If there is no such function, the exception will be catched and printed
        '''
        cmd = cmd[1:]
        funct = cmd.split()[0]
        #print cmd
        #print ' '.join(cmd.split()[1:]),addr
        #try:
        return getattr(self,funct)(' '.join(cmd.split()[1:]),addr)
        #except:
        #    return "no such command '/%s' : %s" %(cmd,sys.exc_info()[0])

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
                        print "%s: %s"%(self.chat.resolveNick(addr[0]), data)
    def requeststop(self):
        '''
        sets stop to 1
        '''
        self.stop=1

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
        self.iplist =  { }
        self.ownParser= ownParser(self)
        self.beep = False
        self.espeak = True
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
        self.ownParser.nick(self.nick)
    def send(self,msg=""):
        if msg.startswith('/'):
            ret= self.ownParser.parse(msg) 
            if ret is not None:
                print ret
        else:
            self.s.sendto("%s" %msg,0,(self.group,self.port))

    def resolveNick(self,ip):
        '''
        Tries to resolve an ip-addres to a  nickname via the 
        iplist dictionary. if the ip-address is unkown to the
        local host, the ip will be returned
        
        '''
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
