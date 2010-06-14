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


        

