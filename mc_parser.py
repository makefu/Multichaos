#!/usr/bin/python
import subprocess
import shlex
import sys
from time import time
# default values
class HistItem():
    def __init__(self,timestamp,cmd):
        self.ts =  timestamp
        self.cmd = cmd
    def __repr__(self):
        return "<HistItem ts:%lf command:%d>"%(self.ts,self.cmd)
        
class Node():
    def __init__(self,ip,nick=None,hst=None,ram=None):
        if hst is None:
            self.hst = []
        if nick is None:
            self.nick=ip
        self.ip=ip
        if ram is None:
            self.ram = {}
    def __repr__(self):
        return "<Node ip:%s nick:%s hst:%s ram:%s >"% (self.ip,self.nick,self.hst,self.ram)
    def cleanup(self):
        """
        do cleanup here ( remove history partly,... )
        """
        pass


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
        args = ' '.join(args)
        self.chat.send_mc("/rot13 %s"% args.encode('rot13'))
        return "Encoded to %s" % (args.encode('rot13'))

    def help(self,args):
        '''
        dummy function
        needs args as argument ( because of parsing )
        returns a status ( or message) string
        if the return string is 'None', the string will not be printed
        '''
        print help(self)
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
        arg = ' '.join(args)
        self.chat.send_mc("/nick \"%s\"" % args )
        #return "You are now known as %s" % args
    def espeak(self,args):
        args = ' '.join(args)
        self.chat.send_mc("/espeak %s" % 
                args )
    def beep(self,args):
        '''
        sends beep to the multicast group
        '''
        args = ' '.join(args)
        self.chat.send_mc("/beep \"%s\"" % args )
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
    def caps(self,args):
        return "not yet implemented!"
    def togglesuper(self,args):
        self.chat.super = not self.chat.super
    def raw(self,args):
        self.chat.send_mc(' '.join(args))
    def py (self,args):
        return eval(" ".join(args))
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
            return getattr(self,funct)(cmd.split()[1:])
        except:
            return "no such local command '/%s' : %s" %(cmd,sys.exc_info()[0])
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
        
        args = ' '.join(shlex.split(' '.join(args)))
        print args
        msg = "'%s' now known as '%s'" % (self.chat.resolveNick(addr[0]),args)
        self.chat.iplist[addr[0]].nick = args
        return  msg
    def rot13(self,args,addr):
        '''
        rot13 decodes text with command /rot13 encryption
        '''
        args = " ".join(args)
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

        if int(args[-1]) == self.chat.rnd and self.chat.ip is None:
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
        #print arg, len(arg)
        if len(args) >= 1:
            cmd.append("-f%s"%args[0])
        if len(args) >= 2:
            try:
                length = int(args[1])
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
        cmd.extend(args)
        p = subprocess.Popen(cmd)
        return "%s demands '%s'" %(self.chat.resolveNick(addr[0]),args)
    def caps(self,cmd,addr):
        '''
        writes the capabilities to the multicast channel
        
        not yet implemented.
        '''
        return "not yet implemented!"
    def echo (self,args,addr):
        args = " ".join(args)
        return "%s: %s"%(self.chat.resolveNick(addr[0]), args)
    def parse(self,cmd,addr):
        '''
        parses a message

        the message should contain a function and a number of 
        parameters together in one string:
        /beep 1000 230
        If there is no such function, the exception will be catched and printed
        '''
        if not self.chat.iplist.has_key(addr[0]):
            self.chat.iplist[addr[0]] = Node(addr[0])
        self.chat.iplist[addr[0]].hst.append( HistItem(time(),cmd ) )
        cmd = cmd[1:]
        funct = cmd.split()[0]
        try:
            return getattr(self,funct)(cmd.split()[1:],addr)
        except Exception as e:
            return "no such remote command '/%s' : %s" %(cmd,e)
    def pset(self,args,addr):
        """saves a value for a node"""
        self.chat.iplist[addr[0]].ram[args[0]]=' '.join(args[1:])
        return "for %s: saved %s => %s" %(addr[0],args[0],' '.join(args[1:]))
    def pget(self,args,addr):
        ret = self.chat.iplist[addr[0]].ram.get(args[0],None)
        if ret is None:
            self.chat.send_mc("/error 404 Not Found")
        else:
            self.chat.send_mc("/value %s %s"%(args[0],ret))

    def set(self,args,addr):
        """
        globally sets a value in all multicast nodes
        """
        args = shlex.split(" ".join(args))
        self.chat.gset(args[0]," ".join(args[1:]))
        return "saved globally %s = %s"%(args[0]," ".join(args[1:]))
    def get(self,args,addr):
        """
        tries to retrieve a value globally saved in the struct
        """

        ret = self.chat.gget(args[0])
        print ret
        if ret is None:
            self.chat.send_mc("/error 404 Not Found ")
            return "%s asks for %s, which is unknown to me"%(addr[0],args[0])
        else:
            self.chat.send_mc("/set %s %s"%(args[0],ret))

    def error(self,args,addr):
        return "Received from %s Error: %s"%(self.chat.resolveNick(addr[0])," ".join(args))
    def value(self,args,addr):
        """
        1. check if we actually requested this value
        2. print it
        3. do something with it
        4. probably save it if its already global
        """
        return "Received from %s : %s = %s" %(self.chat.resolveNick(addr[0]),args[0]," ".join(args[1:]))
