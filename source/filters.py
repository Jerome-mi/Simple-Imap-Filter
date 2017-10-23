#!/usr/bin/python3

'''
Created on 

@author: 
'''

#http://irp.nain-t.net/doku.php/190imap:030_commandes

from filterElement import BaseFilterElement



class BaseFilter(BaseFilterElement):
    tokens = (
        "folder_list", "clause_list", "action_list", )

    def __init__(self, _filterprocessor, _definition):
        """
        """
        self.filterprocessor = _filterprocessor
        self.definition = _definition
        self.folders = _definition.get("folder_list")
        if not self.folders:
            raise Exception('File : "%s" Filter : "%s" no folder list \nAdd token "folder_list"' % (
                self.filterprocessor.currentfile, self.definition["name"]))
        self.clauses = []
        self.actions = []
        self.IMAPMessageSet = []

        for _token in set(self.definition.keys()) - set(BaseFilterElement.tokens):
            if not _token in self.tokens:
                raise Exception('File : "%s" Filter : "%s" unknown token : "%s"\nAvailable tokens : %s' % (
                    self.filterprocessor.currentfile, self.definition["name"], _token, self.tokens))


    def run(self):
        """ Run filter, check coherence actions filters and process message set
        :return:
        """
        for _clauseName in self.definition.get('clause_list',[]):
            clause = self.filterprocessor.clauses.get(_clauseName)
            if not clause:
                raise Exception('File "%s" : Filter "%s" : unknown clause : "%s"\nAvailable clauses: %s' % (
                    self.filterprocessor.currentfile, self.definition["name"], _clauseName, tuple(self.filterprocessor.clauses.keys())))
            self.clauses.append(clause)
        for _actionName in self.definition.get('action_list',[]):
            if not self.filterprocessor.actions.get(_actionName):
                raise Exception('File "%s" : Filter "%s" : unknown action : "%s"\nAvailable actions : %s' % (
                    self.filterprocessor.currentfile, self.definition["name"], _actionName, tuple(self.filterprocessor.actions.keys())))
            self.actions.append(self.filterprocessor.actions[_actionName])
        for _folder in self.folders:
            self.processMessageSet(_folder)

    def processMessageSet(self, _folder):
        """ Applies actions on messages
        :return:
        """
        self.IMAPMessageSet = []
        for _action in self.actions:
            _action.initializeFilter(self, _folder)
        for _action in self.actions:
            _action.begin()
        for _m in self.messageSet(_folder):
            self.IMAPMessageSet.append(_m.msgID)
            for _action in self.actions:
                _action.runMessage(_m)
        for _action in self.actions:
            _action.end()

    def messageCount(self):
        return len(self.IMAPMessageSet)

    def match(self, _m):
        """ match if ONE clause matches short boolean evaluation
        :param _m:
        :return: boolean
        """
        if len(self.clauses) == 0:
            return True
        _match = False
        for clause in self.clauses:
            _match = _match or clause.match(_m)
            if _match: break
        return _match

    def messageSet(self, _folder):
        """ filtered message header generator
        :return:
        """
        for _m in self.filterprocessor.imapConnexion.messageHeaders( _folder):
            if self.match(_m):
                yield _m
