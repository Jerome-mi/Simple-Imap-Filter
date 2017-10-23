#!/usr/bin/python3

'''
Created on 

@author: 
'''

#http://irp.nain-t.net/doku.php/190imap:030_commandes

import imaplib
import re
from datetime import datetime, date

from email import message_from_bytes
from email.header import decode_header
from email.utils import parseaddr,parsedate_tz

from imapclient import imap_utf7
from filterElement import BaseFilterElement

class MessageHeader(object):
    def __init__(self, _msgid, _internalID, _internalDate, _flags, _msg):
        self.msgID = _msgid
        self.flags = _flags
        self.internalID = _internalID
        _internalDatetime_Tuple = parsedate_tz(_internalDate)
        self.internalDate = date(*_internalDatetime_Tuple[:3])
        self.internalDatetime = datetime(*_internalDatetime_Tuple[:6])
        _date = _msg["Date"]
        _DateTime_Tuple = None
        if _date:
            _DateTime_Tuple = parsedate_tz(_msg["Date"])
        # none if date without TZ
        if _DateTime_Tuple:
            self.date = date(*_DateTime_Tuple[:3])
            self.datetime = datetime(*_DateTime_Tuple[:6])
        else:
            self.date = self.internalDate
            self.datetime = self.internalDatetime
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

    reg_fetch = re.compile(
        r'^(?P<MsgId>[0-9]+) \(INTERNALDATE \"(?P<InternalDate>.*)\" FLAGS \((?P<Flags>.*)\) RFC822.HEADER \{(?P<InternalID>.*)\}')

    reg_folderList = re.compile(r'^\((?P<flags>.*)\) \"(?P<Delimiter>.*)\" (?P<Name>.*)')

    def __init__(self, _filterprocessor, _definition, _args):
        self.verbose = _args.verbose
        self.definition = _definition
        self.filterprocessor = _filterprocessor
        self.server = _definition["server"]
        self.user = _definition["user"]
        self.password = _definition["password"]
        self.M = imaplib.IMAP4_SSL(self.server)
        self.toExpunge = False
        for _token in set(self.definition.keys()) - set(BaseFilterElement.tokens):
            if not _token in self.tokens:
                raise Exception('File : "%s" Imap_client : "%s" unknown token : "%s"\nAvailable tokens : ' % (
                    self.filterprocessor.currentfile, self.definition["name"], _token))


    def connect(self):
        self.toExpunge = False
        if self.verbose:
            print("Connecting to : %s user %s" % (self.server, self.user))
        cnx = self.M.login(self.user, self.password.decode())
        if self.M and self.verbose:
            print("Connected to : %s" % self.server)
        self.listFolders()

    def validateFolderName(self, _folder):
        if not _folder in self.folders:
            _folder = '"' + _folder + '"'
        if not _folder in self.folders:
            raise Exception("Folder %s doesn't exists.\nAvailable folders : %s " % (_folder, self.folders))
        return _folder

    def disconnect(self):
        self.expungeMailBox()
        if self.M:
            self.M.logout()

    def listFolders(self):
        #list(directory='Archive')
        rc, _list = self.M.list()
        if rc != 'OK':
            raise Exception("IMAP list rc %s" % rc)
        self.folders = []
        for f in _list:
            d = imap_utf7.decode(f)
            Flags, Delimiter, Name = self.reg_folderList.match(d).groups()
            self.folders.append(Name)

    def deleteMessages(self, _msgIds):
        if len(_msgIds) == 0:
            return
        _msgSet = ','.join([str(Id) for Id in _msgIds])
        self.M.store(_msgSet,'+FLAGS','\\Deleted')
        self.toExpunge = True

    def copyMessages(self, _msgIds, _destination):
        if len(_msgIds) == 0:
            return
        _msgSet = ','.join([str(Id) for Id in _msgIds])
        _destination = self.validateFolderName(_destination)
        self.M.copy(_msgSet, _destination)

    def moveMessages(self, _msgIds, _destination):
        if len(_msgIds) == 0:
            return
        _msgSet = ','.join([str(Id) for Id in _msgIds])
        _destination = self.validateFolderName(_destination)
        self.M.copy(_msgSet, _destination)
        self.M.store(_msgSet,'+FLAGS','\\Deleted')
        self.toExpunge = True

    def flagMessages(self, _msgIds, _flag, _set):
        if len(_msgIds) == 0:
            return
        _msgSet = ','.join([str(Id) for Id in _msgIds])
        if _set:
            self.M.store(_msgSet, '+FLAGS', _flag)
        else:
            self.M.store(_msgSet, '-FLAGS', _flag)

    def expungeMailBox(self):
        if self.toExpunge:
            self.M.expunge()

    def messageHeaders(self, _folder):
        _folder = self.validateFolderName(_folder)
        _rc, _message_count = self.M.select(imap_utf7.encode(_folder))
        if _rc != 'OK':
            raise Exception("IMAP select rc %s" % _rc)
        if self.verbose:
            print("Select %s folder : %s messages" % (_folder, _message_count[0].decode()))
        if _message_count[0] == b'0':
            return None
        _rc, _datas = self.M.fetch(b'1:*', '(RFC822.HEADER INTERNALDATE FLAGS)')
        if _rc != 'OK':
            raise Exception("IMAP fetch rc %s" % _rc)
        for _data in _datas[::2]:
            _msg_id, _internalDate, _flags, _internalID = self.reg_fetch.match(_data[0].decode()).groups()
            _msg = message_from_bytes(_data[1])
            yield (MessageHeader(int(_msg_id), _internalID, _internalDate,_flags.split(' '),_msg))
