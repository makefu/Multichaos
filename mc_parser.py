#!/usr/bin/python
import logging
import random
# default values
logging.basicConfig(level=logging.INFO)
class HistItem():
    def __init__(self,timestamp,cmd):
        self.ts =  timestamp
        self.cmd = cmd
    def __repr__(self):
        return "<HistItem ts:%lf command:%s>"%(self.ts,self.cmd)
        
class Node():
    def __init__(self,ip,color=None,nick=None,hst=None,ram=None):
        """ """
        if hst is None:
            self.hst = []
        if nick is None:
            self.nick=ip
        self.ip=ip
        if color is None:
            self.color = random.randint(32,35)
        else:
            self.color = color
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
    """
    generic parser class
    depricated
    """
    def __init__(self,chat):
        self.chat = chat

class ownParser(parser):
    """ parses local command calls ( like /nick or /togglebeep )
    initial parsing is done with the "parse" function"
    it will evaluate the function given and tries to call
    the function with that name 
    """
    def __init__(self,chat):
        """ """
        parser.__init__(self,chat)
    def rot13(self,args):
        """
        rot13 encrypts a given text and sends it over the line
        magic is done via string.encode('rot13')
        the string is written into the multicast channel
        """
        args = ' '.join(args)
        self.chat.send_mc("/rot13 %s"% args.encode('rot13'))
        return "Encoded to %s" % (args.encode('rot13'))

    def help(self,args):
        """dummy function
        needs args as argument ( because of parsing )
        returns a status ( or message) string
        if the return string is 'None', the string will not be printed """
        print help(self)
        return "this is the help file you appended %s" % args
    def flushnicks(self,args):
        """flushes the nick table"""
        self.chat.iplist.clear()
        return "nicks flushed"
    def nick(self,args):
        """writes our new nick onto the line"""
        arg = ' '.join(args)
        self.chat.send_mc("/nick \"%s\"" % args )
        #return "You are now known as %s" % args
    def espeak(self,args):
        """ """
        args = ' '.join(args)
        self.chat.send_mc("/espeak %s" % 
                args )
    def beep(self,args):
        """sends beep to the multicast group """
        args = ' '.join(args)
        self.chat.send_mc("/beep \"%s\"" % args )
    def togglebeep(self,args):
        """toggles beep on or off
        this is important when to read remote beep commands
        These can be turned on or off with this command """
        self.chat.beep=not self.chat.beep
        return "Beep is now ",self.chat.beep 
    def toggleespeak(self,args):
        self.chat.espeak=not self.chat.espeak
        return "Espeak is now ",self.chat.espeak
    def caps(self,args):
        return "not yet implemented!"
    def togglesuper(self,args):
        """ """
        self.chat.super = not self.chat.super
    def raw(self,args):
        """ """
        msg = ' '.join(args)
        logging.debug("RAW:%s"%msg)
        #msg = ' '.join(args)
        self.chat.send_mc(msg)
    def py (self,args):
        """ """
        return eval(" ".join(args))
    def hist (self,args):
        """ """
        str = ""
        for (k,i) in self.chat.iplist.items():
            str +="User: %s\n"%self.chat.resolveNick( k)
            for h in i.hst:
                str += "%s\n"%h
        return str
    def setall(self,args):
        """ """
        for k,v in self.chat.gram.items():
            self.chat.send_mc("/set \"%s\" \"%s\""%(k,v))

    def ack(self,args):
        """ acknowledges a file !! to be implemented"""
        pass
    def parse(self,cmd):
        """parses a command string  
        looks like: /beep 1000 200
        it will try/catch unknown commands
        """
        cmd = cmd[1:]
        #cmd  = shlex.split(cmd)
        cmd = cmd.split()
        funct = cmd[0]
        logging.debug(cmd)
        try:
            return getattr(self,funct)(cmd[1:])
        except Exception as e:
            return "no such local command '/%s' : %s" %(cmd,e)
    def ld(self,args):
        """ lists the current downloads"""
        for v in self.chat.files.values():
            compstr = "[32m[+][0m" if v.complete() else "31m[-]0m" 
            print "%s %s : %d of %d fparts"%(
                    compstr,v.filename,len(v.fparts.keys()),v.num_of_seq)


