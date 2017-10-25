#!/usr/bin/python3

'''
Created on 

@author: 
'''

#http://irp.nain-t.net/doku.php/190imap:030_commandes

from imaplib import IMAP4
import ssl
import re
from datetime import datetime, date

from email import message_from_bytes
from email.header import decode_header,Header
from email.utils import parseaddr,parsedate_tz

import imapclient
from filterElement import BaseFilterElement

class MessageHeader(object):
    def __init__(self, _msgid, _internalID, _internalDate, _flags, _msg):
        self.msgID = _msgid
        self.internalID = _internalID
        self.internalDateTime = _internalDate
        self.internalDate = self.internalDateTime.date()
        self.flags = _flags
        _date = _msg["Date"]
        _DateTime_Tuple = None
        if _date:
            if isinstance(_date, Header):
                _date = str(_date)
                _date = _date[:_date.find('(')]
            _DateTime_Tuple = parsedate_tz(_date)
        # none if date without TZ
        if _DateTime_Tuple:
            self.date = date(*_DateTime_Tuple[:3])
            self.datetime = datetime(*_DateTime_Tuple[:6])
        else:
            self.date = self.internalDate
            self.datetime = self.internalDateTime
        self.subject = self.decodeHeaderString(_msg["Subject"])
        self.from_ = self.addressesOfHeader(_msg["From"])
        self.reply_to = self.addressesOfHeader(_msg["Reply-to"])
        self.to = self.addressesOfHeader(_msg["To"])
        self.cc = self.addressesOfHeader(_msg["Cc"])
        self.bcc = self.addressesOfHeader(_msg["Bcc"])

    def decodeHeaderString(self, _str):

        # if not _bytes:
        #     return ''
        # try:
        #     _str = _bytes.decode()
        # except:
        #     _str = _bytes.decode('iso-8859-1')
        if not _str:
            return None
        headers = decode_header(_str)
        result = ''
        for h, e in headers:
            if e:
                if e == 'unknown-8bit':
                    h = h.decode('iso-8859-1', errors='replace')
                else:
                    h = h.decode(e)
            if type(h) == bytes:
                h = h.decode()
            else:
                h = str(h)
            result = result + h
        return result

    def addressesOfHeader(self, _adrs):
        if not _adrs:
            return []
        result = []
        if type(_adrs) == str:
            result.append(parseaddr(_adrs))
        if hasattr(_adrs, '_chunks'):
            _adrs = decode_header(_adrs)
            for _adr in _adrs:
                if _adr[1] == 'unknown-8bit':
                    result.append(parseaddr(_adr[0].decode('iso-8859-1', errors='replace')))
                else:
                    result.append(parseaddr(_adr[0].decode()))
        return [(self.decodeHeaderString(_name), self.decodeHeaderString(_adr)) for _name, _adr in result]

    def __str__(self):
        return str(self.__dict__)

class ImapConnexion(BaseFilterElement):
    tokens = (
        "server", "user", "password", )

    # reg_fetch = re.compile(
    #     r'^(?P<MsgId>[0-9]+) \(INTERNALDATE \"(?P<InternalDate>.*)\" FLAGS \((?P<Flags>.*)\) RFC822.HEADER \{(?P<InternalID>.*)\}')

    #reg_folderList = re.compile(r'^\((?P<flags>.*)\) \"(?P<Delimiter>.*)\" (?P<Name>.*)')

    def __init__(self, filterProcessor, definition, args):
        self.verbose = args.verbose
        self.definition = definition
        self.filterProcessor = filterProcessor
        self.server = definition["server"]
        self.user = definition["user"]
        self.password = definition["password"]
        self.toExpunge = False
        try:
            self.M = imapclient.IMAPClient(self.server, ssl=True)
        except IMAP4.error :
            ssl_context = ssl.create_default_context()
            self.M = imapclient.IMAPClient(self.server,ssl_context=ssl_context, ssl=True)

        for _token in set(self.definition.keys()) - set(BaseFilterElement.tokens):
            if not _token in self.tokens:
                raise Exception('File : "%s" Imap_client : "%s" unknown token : "%s"\nAvailable tokens : ' % (
                    self.filterProcessor.currentfile, self.definition["name"], _token))


    def login(self):
        self.toExpunge = False
        if self.verbose:
            print("Connecting to : %s user %s" % (self.server, self.user))
        cnx = self.M.login(self.user, self.password.decode())
        if cnx and self.verbose:
            print("Connected to : %s" % self.server)
        self.listFolders()

    def validateFolderName(self, folder):
        if not folder in self.folders:
            folder = '"' + folder + '"'
        if not folder in self.folders:
            raise Exception("Folder %s doesn't exists.\nAvailable folders : %s " % (folder, self.folders))
        return folder

    def disconnect(self):
        self.expungeMailBox()
        if self.M:
            try:
                self.M.logout()
            except:
                pass

    def listFolders(self):
        #list(directory='Archive')
        self.folders = []
        for f in self.M.list_folders():
            if self.server == 'imap.gmail.com':
                if f[2].startswith('[Gmail]'): continue
            self.folders.append(f[2])

    def deleteMessages(self, msgIds):
        if len(msgIds) == 0:
            return
        _msgSet = ','.join([str(Id) for Id in msgIds])
        self.M.store(_msgSet,'+FLAGS','\\Deleted')
        self.toExpunge = True

    def copyMessages(self, msgIds, destination):
        if len(msgIds) == 0:
            return
        msgSet = ','.join([str(Id) for Id in msgIds])
        destination = self.validateFolderName(destination)
        self.M.copy(msgSet, destination)

    def moveMessages(self, msgIds, destination):
        if len(msgIds) == 0:
            return
        msgSet = ','.join([str(Id) for Id in msgIds])
        destination = self.validateFolderName(destination)
        self.M.copy(msgSet, destination)
        self.M.store(msgSet,'+FLAGS','\\Deleted')
        self.toExpunge = True

    def flagMessages(self, msgIds, flag, set):
        if len(msgIds) == 0:
            return
        msgSet = ','.join([str(Id) for Id in msgIds])
        if set:
            self.M.store(msgSet, '+FLAGS', flag)
        else:
            self.M.store(msgSet, '-FLAGS', flag)

    def expungeMailBox(self):
        if self.toExpunge:
            self.M.expunge()

    def messageHeaders(self, folder):
        folder = self.validateFolderName(folder)
        self.selectResult = self.M.select_folder(folder)
        message_count = self.selectResult[b'EXISTS']
        if self.verbose:
            print("Select %s folder : %s messages" % (folder, message_count))
        return None
        if message_count == 0:
            return None
        datas = self.M.fetch(range(1,message_count+1), ['RFC822.HEADER', 'INTERNALDATE', 'FLAGS'])
        for msg_Id in datas.keys():
            data = datas[msg_Id]
            #msg_Id = data[b'SEQ']
            internalID = 0
            internalDate = data[b'INTERNALDATE']
            flags = data[b'FLAGS']
            msg = message_from_bytes(data[b'RFC822.HEADER'])
            yield (MessageHeader(msg_Id, internalID, internalDate, flags,msg))
