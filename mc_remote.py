from mc_parser import parser,Node,HistItem
import subprocess
import shlex
import sys
from time import time
import logging
import string
import warnings
import threading
class McFile():
    def __init__(self,filename,num_of_seq,chat):
        self.filename=filename
        self.num_of_seq=int(num_of_seq)
        self.fparts = {}
        self.chat = chat
        print "starting watchdog"
        self.timer = threading.Timer(1,self.watchdog)
        self.timer.start()
    def complete(self):
        return self.num_of_seq == len(self.fparts.keys())
    def unpack(self,path):
        logging.debug("beginning to write file")
        try:
            out = ""
            f = open(path,"w+")
            for i in range(self.num_of_seq):
                out += self.fparts[i]
            logging.debug("original : %s"%out)
            logging.debug("base64: %s"%out.decode("base64"))
            f.write(out.decode("base64"))
            f.close()
        except Exception as e:
            print "something went wrong:",e
    def watchdog(self):
        logging.debug("I AM THE FUCKING WATCHDOG")
        d = ""
        for i in range(self.num_of_seq):
            if not i in self.fparts.keys():
                logging.debug("demanding",i)
                d += "%d "%i
        logging.info("/fmoar %s %d %s"%(
            self.filename,self.num_of_seq,d))
        self.chat.send_mc("/fmoar %s %d %s"%(
            self.filename,self.num_of_seq,d))
        self.timer = threading.Timer(1,self.watchdog)
        self.timer.start()


class remoteParser(parser):
    """parses commands received over the Multicast link and evaluate them"""
    def __init__(self,chat):
        """ Internal function """
        parser.__init__(self,chat)
    def nick(self,args,addr):
        """the nick will be associated with the ip-address the message it is from
        the iplist associated will be changed for that 
        %MC% sets the nick name for your ip-address
        usage: \\nick "bob Ros$"
        """
        
        args = ' '.join(shlex.split(' '.join(args)))
        logging.debug(args)
        msg = "'%s' now known as '%s'" % (self.chat.resolveNick(addr[0]),args)
        self.chat.iplist[addr[0]].nick = args
        return  msg
    def rot13(self,args,addr):
        """ rot13 decodes text with command /rot13 encryption """
        args = " ".join(args)
        return "%s : rot13 : %s" % (self.chat.resolveNick(addr[0]),
                args.encode('rot13'))
    def hello(self,args,addr):
        """Tries to parse a hello message to find own IP
        it will contain a challenge cookie which will be tested
        against the generated one.
        This should happen only once ( at beginning of the session)

        if the challenge is not taken, the message will be printed out"""
        if int(args[-1]) == self.chat.rnd and self.chat.ip is None:
            print "challenge succeeded. Found your IP: %s"%addr[0]
            self.chat.ip=addr[0]
        else:
            return "hello from \"%s\" : \"%s\"" % (addr[0],args)

    def beep(self,args,addr):
        """Parses beep messages.
        These may contain a frequency and a length
        The parameters  will be passed to the "beep" program with the
        corresponding flags 
        %MC% When activated by user, a beep tone will be produced.  Default tone length is 1000, default frequency is 2000"""
        if self.chat.beep==False:
            return "beeping is turned off, ignoring request from %s with freq/length %s"% (addr[0],args)
        cmd = [ "/usr/bin/beep" ]
        if len(args) >= 1:
            cmd.append("-f%s"%args[0])
        if len(args) >= 2:
            try:
                length = int(args[1])
            except:
                logging.info("malformed length %s" %sys.exc_info()[0])
                length = 100

            if length > 1000:
                length = 1000

            cmd.append("-l%d"%length)
        p = subprocess.Popen(cmd)
        return "%s demands beep (%s)" % (self.chat.resolveNick(addr[0]) ,args)

    def espeak(self,args,addr):
        """when activated, will say args via espeak voice synthesizer
        %MC% when activated by user, a synthesized voice will be produced by the machine.
        """
        if self.chat.espeak==False:
            return "espeak is turned off,ignoring request from %s with args %s" % (addr[0], args)
        cmd = [ "/usr/bin/espeak" ]
        cmd.extend(args)
        p = subprocess.Popen(cmd)
        return "%s demands '%s'" %(self.chat.resolveNick(addr[0]),args)
    def isMcFunct(self,funct):
        if funct.__doc__ is None:
            logging.warning("function %s has no docstring"%funct)
            return False
        return "%MC%" in funct.__doc__ 
    def caps(self,cmd,addr):
        """writes the capabilities to the multicast channel
        %MC% returns the available capabilities of this client. Specific help can be retrieved by appending the function name to the caps-command 
        usage: /caps beep espeak """
        ret = ""
        if len(cmd) is 0:
            for  r in dir(self):
                h = getattr(self,r)
                if self.isMcFunct(h):
                    ret += "%s "% r
            self.chat.send_mc("/echo \"%s\""%ret)
        else:
            for i in cmd:
                ret += "%s: "%i  
                try:
                    fun = getattr(self,i)
                    index = string.find(fun.__doc__,"%MC%")
                    index +=4
                    ret += "%s"% fun.__doc__[index:]
                except Exception as e:
                    ret += "No such function"# %s"%e
                self.chat.send_mc("/echo \"%s\""%ret)
                ret = ""

        return
                
    def echo (self,args,addr):
        """ replaces the original ``chat'' 
        %MC% Original Chat mode, messages will be written like a normal text message by the user
        """
        args = " ".join(args)
        logging.debug("echo COLOR: %d"%self.chat.iplist[addr[0]].color)
        return "[%dm%s[0m: %s"%(self.chat.iplist[addr[0]].color,self.chat.resolveNick(addr[0]), args)
    def parse(self,cmd,addr):
        """parses a message 
        the message should contain a function and a number of 
        parameters together in one string:
        /beep 1000 230
        If there is no such function, the exception will be catched and printed 
        """
        if not self.chat.iplist.has_key(addr[0]):
            self.chat.iplist[addr[0]] = Node(addr[0])
        self.chat.iplist[addr[0]].hst.append( HistItem(time(),cmd ) )
        cmd = cmd[1:]
        logging.debug("REMOTE PARSE:%s"%cmd)
        cmd = shlex.split(cmd)
        funct = cmd[0]
        try:
            return getattr(self,funct)(cmd[1:],addr)
        except Exception as e:
            return "no such remote command '/%s' : %s" %(cmd,e)

    def pset(self,args,addr):
         """saves a ``private'' value for a node
         %MC% Saves a private key-value pair on this machine
         """
         self.chat.iplist[addr[0]].ram[args[0]]=' '.join(args[1:])
         return "for %s: saved %s => %s" %(addr[0],args[0],' '.join(args[1:]))

    def pget(self,args,addr):
        """tries to retrieve value based on a given key
        %MC% Tries to retrieve a given key from the private storage of this machine
        """
        ret = self.chat.iplist[addr[0]].ram.get(args[0],None)
        if ret is None:
            self.chat.send_mc("/error 404 Not Found")
        else:
            self.chat.send_mc("/value %s %s"%(args[0].replace('"','\\"'),ret.replace('"','\\"')))

    def set(self,args,addr):
        """ globally sets a value in all multicast nodes 
        %MC% saves a global variable ( available for everyone in the Multicast )
        """
        logging.debug("SET %s"%args)
        k = args[0]             
        v = " ".join(args[1:]) 
        self.chat.gset(k,v)
        return "saved globaly %s = %s"%(k,v)
    def get(self,args,addr):
        """ tries to retrieve a value globally saved in the struct 
        %MC% tries to retrieve a value from the global key-value storage of this node
        """
        ret = self.chat.gget(args[0])
        # thy shall not unescape thy single ' when inside thy double "
        key = args[0].replace('"','\\"')#.replace('\'','\\\'')
        if ret is None:
            self.chat.send_mc("/error 404 %s Not Found "%key)
            return

        ret = ret.replace('"','\\"')    #.replace('\'','\\\'')
        self.chat.send_mc("/set \"%s\" \"%s\""%(key,ret))

    def error(self,args,addr):
        """ """
        return "Received from %s Error: %s"%(self.chat.resolveNick(addr[0])," ".join(args))
    def value(self,args,addr):
        """ 1. check if we actually requested this value
        2. print it
        3. do something with it
        4. probably save it if its already global """
        return "Received from %s : %s = %s" %(self.chat.resolveNick(addr[0]),args[0]," ".join(args[1:]))

    def file(self,args,addr):
        """ starts a file transfer 
            DEPRECATED 
        """
        return "%s is offering %s with %s chunks"%(self.chat.resolveNick(addr[0]),args[0],args[1])
        ### 
        warnings.warn("deprecated", DeprecationWarning)
        pass

    def fmoar(self,args,addr):
        pass
    def fpart(self,args,addr):
        curr_file = self.chat.files.get(args[0],None)
        if curr_file is None:
            curr_file = self.chat.files[args[0]] = McFile(args[0], args[1],chat=self.chat)

        #                  seqnr         data 
        curr_file.fparts[int(args[2])] = args[3]
        print curr_file.num_of_seq , len(curr_file.fparts)

        print curr_file.num_of_seq == len(curr_file.fparts)
        if curr_file.complete() and curr_file.num_of_seq is int(args[1]):
            # unpack the file and write to disk
            print "finished with file %s"%curr_file.filename
            #curr_file.unpack("here")
            curr_file.timer.cancel()
            curr_file = None
        else:
            if curr_file.num_of_seq != int(args[1]):
                logging.warn("num of sequences CHANGED! Restarting Download")
                curr_file = self.chat.files[args[0]] = McFile(args[0], 
                        args[1],chat=self.chat)
            """
            try:
                curr_file.timer.cancel()
                curr_file.timer = threading.Timer(1,curr_file.watchdog)
                curr_file.timer.start() 
            except:
                pass
            """
            pass


        return 
