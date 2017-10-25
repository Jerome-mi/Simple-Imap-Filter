#!/usr/bin/python3

'''
Created on 

@author: 
'''

#http://irp.nain-t.net/doku.php/190imap:030_commandes

import copy
from urllib import request, parse


class BaseAction(object):
    def __init__(self, filterprocessor, definition):
        self.filterprocessor = filterprocessor
        self.name = definition["name"]
        self.definition = definition
        self.logger = self.filterprocessor.filterLogger

    # automaticaly created. if exist, replaced with basic
    basics = ["Count", "Delete", "Print", "Trash", "Seen", "Unseen", "Flag", "Unflag"]

    # def run(self, _filter):
    #     self.filter = _filter
    #     self.count = 0
    #     self.IMAPMessageSet = []
    #     self.begin()
    #     for _m in _filter.messageSet():
    #         self.IMAPMessageSet.append(_m.msgID)
    #         self.runMessage(_m)
    #         self.count += 1
    #     self.end()

    def initializeFilter(self, filter, folder):
        self.filter = filter
        self.folder = folder

    def checkDefinition(self):
        pass

    def runMessage(self,m):
        pass

    def begin(self):
        pass

    def end(self):
        pass

    @classmethod
    def newAction(cls, filterprocessor, definition):
        _name = definition["name"]
        _type = definition["type"] + "Action"
        try:
            _newAction = {subcls.__name__: subcls for subcls in cls.__subclasses__()}[_type](filterprocessor, definition)
        except:
            raise Exception('File : "%s" : Action : "%s" unknown type "%s"\nAvailable types: %s' % (
                filterprocessor.currentfile, _name,definition["type"], tuple(subcls.__name__[:-len("Action")] for subcls in cls.__subclasses__())))
        _newAction.checkDefinition()
        return _newAction


class PrintAction(BaseAction):
    """ basic action print message
    """
    def runMessage(self,_m):
        self.logger.info(_m)


class SeenAction(BaseAction):
    """
    """
    def end(self):
        self.filterprocessor.imapConnexion.flagMessages(
            self.filter.IMAPMessageSet, b'\\Seen', True)

class UnseenAction(BaseAction):
    """
    """
    def end(self):
        self.filterprocessor.imapConnexion.flagMessages(
            self.filter.IMAPMessageSet, b'\\Seen', False)

class FlagAction(BaseAction):
    """
    """
    def end(self):
        self.filterprocessor.imapConnexion.flagMessages(
            self.filter.IMAPMessageSet, b'\\Flagged', True)

class UnflagAction(BaseAction):
    """
    """
    def end(self):
        self.filterprocessor.imapConnexion.flagMessages(
            self.filter.IMAPMessageSet, '\\Flagged', False)

class DeleteAction(BaseAction):
    """ basic action delete message
    """
    def end(self):
        self.filterprocessor.imapConnexion.deleteMessages(self.filter.IMAPMessageSet)

class TrashAction(BaseAction):
    """ basic action move message to Trash
    """
    def end(self):
        self.filterprocessor.imapConnexion.moveMessages(self.filter.IMAPMessageSet, "Trash")


class MoveAction(BaseAction):
    """ copy message to destination and delete it
    """
    def checkDefinition(self):
        if not self.definition.get("destination"):
            raise Exception('Missing destination for action "%s"' % (self.name))

    def end(self):
        self.filterprocessor.imapConnexion.moveMessages(self.filter.IMAPMessageSet, self.definition["destination"])


class CopyAction(BaseAction):
    """ copy message to destination
    """
    def checkDefinition(self):
        if not self.definition.get("destination"):
            raise Exception('Missing destination for action "%s"' % (self.name))

    def end(self):
        self.filterprocessor.imapConnexion.copyMessages(self.filter.IMAPMessageSet, self.definition["destination"])


class CountAction(BaseAction):
    """ basic action print count at end
    """
    def end(self):
        self.logger.info('Filter "%s" : Folder "%s" : summary : %s message(s)' % (
            self.filter.definition.get("name") , self.folder ,self.filter.messageCount()))


class UrlAction(BaseAction):
    """ send HTTP GET to url from a message
    """
    def checkDefinition(self):
        self.url = self.definition["url"]
        self.data = self.definition["data"]

    def runMessage(self,m):
        msgdata = []
        #  [key , value from yml],
        #  "user" , "foo"],
        #  "message", key, value from message
        #  "message", "msg", "subject"
        for l in copy.deepcopy(self.data):
            if len(l) == 3:
                l.pop(0)
                l[1] = m.__dict__[l[1]]
            msgdata.append(tuple(l))
        encodeddata = "?" +parse.urlencode(msgdata)
        full_url = self.url + encodeddata
        if self.definition.get("test"):
            self.logger.info("testing")
            self.logger.info(full_url)
        else:
            self.logger.info("calling")
            self.logger.info(full_url)
            response = request.urlopen(full_url)
            self.logger.info(response)
