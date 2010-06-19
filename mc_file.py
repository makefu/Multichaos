import logging
import threading
class IOFile:
    def __init__(self,chat,filename,chunksize=901,st=None,numchunks=0):
        self.fname = filename
        self.chat = chat
        self.timer = threading.Timer(1,self.watchdog)
        if st is not None:
            # then generate chunks from the provided string
            print "adding iofile"
            self.fparts = self._to_chunks(st,chunksize)
            self.numchunks = len(self.fparts)
        else:
            self.fparts = {}
            self.numchunks = numchunks
            self.chunksize = None
            self.timer.start()
        pass
        self.stopped = False
    def _to_chunks(self,st,chunksize):
        ret = {}
        rest = st.encode("base64").replace('\n','')
        i=0
        while len(rest) > chunksize:
            ret[i]=rest[:chunksize]
            rest = rest[chunksize:]
            i +=1
        ret[i] = rest
        return ret
    def send_out(self):
        for i in range(self.numchunks):
            print i
            self.send_chunk(i)
    def send_chunk(self,chid):
            logging.debug("sending file :%s num %d"%(self.fname,chid))
            self.chat.send_mc("/fpart %s %d %d %s" %(
                self.fname,self.numchunks,chid,self.fparts[chid]))
    def watchdog(self):
        """ watcher function which tries to
        find ``missed'' chunks and demands them via
        Multicast """

        d = ""
        for i in range(self.numchunks):
            if not i in self.fparts.keys():
                logging.debug("For %s demanding %s"%(self.fname,i))
                d += "%d "%i
        #logging.debug("/fmoar %s %d %s"%(
        self.chat.send_mc("/fmoar %s %d %s"%(
            self.fname,self.numchunks,d))
        self.timer = threading.Timer(1,self.watchdog)
        self.timer.start()

    def unpack(self,path):
        """ unpacks ( un-base64 ) the file into
        a given file-path"""
        logging.debug("beginning to write file")
        try:
            out = ""
            f = open(path,"w+")
            for i in range(self.numchunks):
                out += self.fparts[i]
            #logging.debug("original : %s"%out)
            #logging.debug("base64: %s"%out.decode("base64"))
            f.write(out.decode("base64"))
            f.close()
        except Exception as e:
            print "something went wrong:",e
    def complete(self):
        """ Tells if the Multicast File is complete"""
        return self.numchunks == len(self.fparts.keys())

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
