import logging
import threading

class OutFile:
    def __init__(self,filename,st,chunksize,chat):
        self.numchunks = 0
        self.chunks = self._to_chunks(st,chunksize)
        self.chsz = chunksize
        self.fname = filename
        self.chat = chat
    def _to_chunks(self,st,chunksize):
        ret = []
        rest = st.encode("base64").replace('\n','')
        while len(rest) > chunksize:
            ret.append(rest[:chunksize])
            #print ret
            rest = rest[chunksize:]
            #print rest
        ret.append(rest)
        print ret
        self.numchunks = len(ret)
        return ret

    def send_out(self):
        for i in range(self.numchunks):
            print i
            self.send_chunk(i)
    def send_chunk(self,chid):
            logging.debug("sending file :%s num %d"%(self.fname,chid))
            self.chat.send_mc("/fpart %s %d %d %s" %(
                self.fname,self.numchunks,chid,self.chunks[chid]))

class InFile():
    """
    defines a class which provides functionality to be
    received over the multicast netwok
    """
    def __init__(self,filename,num_of_seq,chat):
        self.filename=filename
        self.num_of_seq=int(num_of_seq)
        self.fparts = {}
        self.chat = chat
        self.stopped = False
        print "starting watchdog"
        self.timer = threading.Timer(1,self.watchdog)
        self.timer.start()
    def complete(self):
        """ Tells if the Multicast File is complete"""
        return self.num_of_seq == len(self.fparts.keys())
    def stopdl(self):
        """ stop the current download, stops the 
        request for new chunks """
        self.timer.cancel()
        self.stopped = True
    def startdl(self):
        """ starts the download again """
        self.timer = threading.Timer(1,self.watchdog)
        self.timer.start()
        self.started = True
    def unpack(self,path):
        """ unpacks ( un-base64 ) the file into
        a given file-path"""
        logging.debug("beginning to write file")
        try:
            out = ""
            f = open(path,"w+")
            for i in range(self.num_of_seq):
                out += self.fparts[i]
            #logging.debug("original : %s"%out)
            #logging.debug("base64: %s"%out.decode("base64"))
            f.write(out.decode("base64"))
            f.close()
        except Exception as e:
            print "something went wrong:",e
    def watchdog(self):
        """ watcher function which tries to
        find ``missed'' chunks and demands them via
        Multicast """

        logging.debug("I AM THE FUCKING WATCHDOG")
        d = ""
        for i in range(self.num_of_seq):
            if not i in self.fparts.keys():
                logging.debug("demanding",i)
                d += "%d "%i
        #logging.debug("/fmoar %s %d %s"%(
        #    self.filename,self.num_of_seq,d))
        self.chat.send_mc("/fmoar %s %d %s"%(
            self.filename,self.num_of_seq,d))
        self.timer = threading.Timer(1,self.watchdog)
        self.timer.start()


