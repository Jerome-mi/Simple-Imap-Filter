#!/usr/bin/python3

'''
Created on 

@author: 
'''

#http://irp.nain-t.net/doku.php/190imap:030_commandes

import os
import yaml
import logging

from cryptography.fernet import Fernet

from filterElement import BaseFilterElement
from actions import BaseAction
from clauses import BaseClause
from filters import BaseFilter
from imapConnexion import Cross_Country_Imap_Connexion

class FilterProcessor(object):
    """

    """
    class CheckError(Exception):
        pass

    elementTypes = ("imap_client" ,"filter" ,"action" ,"clause")
    default_root_dir = '../mailboxes.d'

    def __init__(self):
        self.actions = {}
        self.filters = []
        self.clauses = {}
        self.logger = logging.getLogger()
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        self.logger.addHandler(ch)
        self.filterLogger = logging.getLogger("FilterLogger")
        self.filterLogger.setLevel(logging.INFO)

    def decrypt(self,s):
        try:
            s = bytes(s, "utf-8")
            cipher_suite = Fernet(self.salt)
            return cipher_suite.decrypt(s)
        except Exception:
            self.logger.error("Error during decrypt token %s\nCheck token and salt" % s)
            raise

    def run(self, args):
        self.args = args
        self.logger.setLevel(logging.WARNING)
        if self.args.verbose:
            self.logger.setLevel(logging.INFO)
        if self.args.debug:
                self.logger.setLevel(logging.DEBUG)
        self.logger.info("Running in verbose mode")
        self.logger.info("Reading configuration file : %s" % self.args.conf)
        self.readConf(self.args.conf)

        if self.args.salt:
            key = Fernet.generate_key()
            print(key.decode())
            exit(0)

        if self.args.encrypt:
            cipher_suite = Fernet(self.salt)
            encoded_text = cipher_suite.encrypt(bytes(self.args.encrypt, "utf-8"))
            print(encoded_text.decode())
            exit(0)

        for path, dir, files in os.walk(self.root_dir):
            for file in files:
                fullfile = os.path.join(path, file)
                if file[-4:] != '.yml':
                    self.logger.debug('File "%s" not ending with .yml : skipped' % file)
                    continue
                with open(fullfile, 'r') as stream:
                    if self.setLock(fullfile):
                        try:
                            self.fileLogHandler = logging.FileHandler(fullfile[:-3] +"log",mode='w')
                            self.filterLogger.addHandler(self.fileLogHandler)
                            self.currentfile = fullfile
                            self.logger.info('Running file : "%s"' % fullfile)
                            yamlcfg = yaml.load(stream)
                            self.runFile(yamlcfg, self.args)
                            self.logger.info('end of file : "%s"' % fullfile)
                        except (BaseFilterElement.CheckError, self.CheckError)  as chk:
                            self.logger.error(chk)
                        except yaml.YAMLError:
                            self.logger.error('YAML Error in file "%s" :' % fullfile)
                        except Exception as exc:
                            self.logger.error('File "%s" in error : %s' % (fullfile, exc))
                            pass
                        finally:
                            self.releaseLock(self.root_dir + "/" + fullfile)
                            self.filterLogger.removeHandler(self.fileLogHandler)

    def prepareAnalyse(self, folders):
        print("Analysing mailbox :%s" % self.imapConnexion.definition["name"])
        print("folders : " + str(folders))
        self.filters = []
        self.actions = {}
        self.clauses = {}
        self.addFilter({
            "name": self.imapConnexion.server,
            "component": "filter",
            "folder_list": folders,
            "clause_list": ["All"],
            "action_list": ["Count"],
        })

    def readConf(self, conf):
        with open(conf, 'r') as stream:
            try:
                yamlcfg = dict(yaml.load(stream)[0])
            except :
                self.logger.error('Error in YAML configuration file %s :' % conf)
                raise
            self.salt = yamlcfg.get("salt")
            if self.salt:
                self.salt = bytes(self.salt, 'utf-8')
            else:
                self.logger.warning('No salt for password or sensible data encryption %s :' % conf)
            self.root_dir = yamlcfg.get("root_dir",self.default_root_dir)
            self.logger.info("Root directory : %s" % self.root_dir)

    def checkElement(self, elt, i):
        _name = elt.get("name")
        if not _name:
            raise self.CheckError('File "%s" : Missing name for element "%d"' % (self.currentfile, i))
        if self.currentNames.get(_name):
            raise self.CheckError('File "%s" : Duplicating name %s for component "%d"' % (self.currentfile, _name,  i))
        self.currentNames[_name] = i
        _type = elt.get("component")
        if not _type:
            raise self.CheckError('File "%s" : Missing component for element %d "%s"' % (self.currentfile, i, _name))
        if not _type in self.elementTypes:
            raise self.CheckError('File "%s" : Unknown component for element %d "%s"\nAvailable components : %s' % (self.currentfile, i, _name, self.elementTypes))
        _cryptedFields = elt.get("crypted")
        if _cryptedFields:
            for cf in _cryptedFields:
                if not elt.get(cf):
                    raise self.CheckError('File "%s" : Missing crypted value "%s" for component %d "%s"' % (self.currentfile, cf ,i, _name))

    def decryptElement(self,elt ,i):
        _cryptedFields = elt.get("crypted")
        if not _cryptedFields:
            return
        for cf in _cryptedFields:
            elt[cf]=self.decrypt(elt[cf])

    def parseFile(self, yamlcfg):
        for i,elt in enumerate(yamlcfg):
            self.checkElement(elt ,i)
            self.decryptElement(elt ,i)
            if elt["component"] == "imap_client":
                self.setImapConnexion(elt)
            elif elt["component"] == "clause":
                self.addClause(elt)
            elif elt["component"] == "filter":
                self.addFilter(elt)
            elif elt["component"] == "action":
                self.addAction(elt)

        for _action in self.actions.keys():
            _used = False
            for _filter in self.filters:
                if _action in _filter.definition["action_list"]:
                    _used = True
                    break
            if not _used:
                raise self.CheckError('File "%s" : Action "%s" is not used in any filter"' % (self.currentfile, _action))

        for _clause in self.clauses.keys():
            _used = False
            for _filter in self.filters:
                if _clause in _filter.definition["clause_list"]:
                    _used = True
                    break
            if not _used:
                raise self.CheckError('File "%s" : Clause "%s" is not used in any filter"' % (self.currentfile, _clause))

    def runFile(self, yamlcfg, args):
        self.clearProcessor()
        self.parseFile(yamlcfg)
        try:
            self.imapConnexion.login()
            if args.analyse:
                self.prepareAnalyse(self.imapConnexion.folders)
            for basicAction in BaseAction.basics:
                self.addAction({"name": basicAction, "component": "action", "type": basicAction})
            for basicClause in BaseClause.basics:
                self.addClause({"name": basicClause, "component": "clause", "true": "yes"})
            for filter in self.filters:
                filter.run()
        finally:
            self.imapConnexion.disconnect()

    def clearProcessor(self):
        self.imapClient = None
        self.filters = []
        self.actions = {}
        self.clauses = {}
        self.currentNames = {}

    def addAction(self, definition):
        self.actions[definition["name"]] = BaseAction.newAction(self ,definition)

    def addFilter(self, definition):
        self.filters.append(BaseFilter(self, definition))

    def addClause(self, definition):
        self.clauses[definition["name"]] = BaseClause(self, definition)

    def setImapConnexion(self, definition):
        server = definition.get("server")
        user = definition.get("user")
        password = definition.get("password")
        if not (server and user and password):
            raise self.CheckError("server, user and password are mandatory for imap_client component")
        self.imapConnexion = Cross_Country_Imap_Connexion(self, definition, self.args)

    def setLock(self, filetolock):
        result =  not os.path.exists(filetolock[:-4]+'.lock')
        if result:
            open(filetolock[:-4]+'.lock',mode='w')
        else:
            self.logger.info('File "%s" locked, skipped' % filetolock)
        return result

    def releaseLock(self, filetolock):
        os.unlink(filetolock[:-4]+'.lock')