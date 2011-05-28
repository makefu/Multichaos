import logging
import warnings
import os
from mc_parser import parser
from mc_file import IOFile

class localParser(parser):
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

    def encoding(self,args):
        enc = "ascii" if len(args) == 0 else args[0]
        self.chat.encoding = args[0]
    def nick(self,args):
        """writes our new nick onto the line"""
        args = ' '.join(args)
        self.chat.send_mc("/nick %s" % args )
        #return "You are now known as %s" % args
    def echo8(self,args):
        self.chat.send_mc(args[0].encode("UTF-8"))
    def espeak(self,args):
        """ """
        args = ' '.join(args)
        self.chat.send_mc("/espeak %s" % args )

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
            if v.stopped:
                compstr = "[33m[#][0m"
            elif v.complete():
                compstr = "[32m[+][0m" 
            else: # running
                compstr = "[31m[-][0m" 
            print "%s %s : %d of %d fparts"%(
                    compstr,v.fname,len(v.fparts.keys()),v.numchunks)
    def ls(self,args):
        directory = args[0] if len(args) > 0 else "."
        return os.listdir(directory)
    def cd(self,args):
        if len(args[0]) is 0:
            return "need to supply a path"
        os.chdir(args[0])

    def saveas(self,args):
        """ saves a download to the file to a specific place"""
        curr_file = self.chat.files[args[0]]
        if not curr_file.complete():
            warnings.warn("download not yet completed!")
        else:
            outfile = args[1] if len(args) is 2 else args[0]
            curr_file.unpack(outfile)
            print "unpacking %s to %s" %(args[0],outfile)

    def stopdl(self,args):
        """ somewhat tries to ignore specific download """
        self.chat.files[args[0]].stopdl()
        return "stopped %s"%args[0]

    def killdl(self,args):
        curr_file = self.chat.files[args[0]]
        curr_file.stopdl()
        self.chat.files[args[0]] = None
        return "killed %s"%args[0]

    def startdl(self,args):
        self.chat.files[args[0]].startdl()
        return "started %s"%args[0]

    def lol(self,args):
        """ be able to set the log level (100(fatal) - 0(debug)) 
        i am not sure if it really works :("""
        logging.basicConfig(level=int(args[0]))
        return "Loglevel is now at %s"%args[0]


    def sendsf(self,args):
        """ send string via file interface"""
        fname = args[0] if len(args) > 0 else "custom_string"
        st    = args[1] if len(args) > 1 else "THIS IS A TEST STRRIIIIING"*2000
        chsz  = int(args[2]) if len(args) > 2 else 901
            
        aut = self.chat.files[fname]= IOFile(self.chat,filename=fname,st=st,chunksize=chsz)
        aut.send_out()
    def loadfile(self,args):
        fname = args[0] 
        if self.chat.files.get(fname,None) is not None:
            warnings.warn("overwriting existing file!")
        chsz = int(args[2]) if len(args) > 1 else 901
        with open(fname) as fil:
                self.chat.files[fname] = IOFile(self.chat,fname,chsz,fil.read())

    def sendfile(self,args):
        fname = args[0] if len(args) > 0 else "sample_file"
        if self.chat.files.get(fname,None) is not None:
            logging.info("will not load existing file again, load if you still want to send a new file!")
        else:
            self.loadfile([fname])
        fil = self.chat.files.get(fname,None)
        assert fil is not None # this should never happen(TM)
        fil.send_out()
