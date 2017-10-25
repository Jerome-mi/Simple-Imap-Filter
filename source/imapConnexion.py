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

class Armoured_Message_Header(object):
    def __init__(self, msg_id, internal_date, flags, msg):
        self.msgID = msg_id
        self.internalDateTime = internal_date
        self.internalDate = self.internalDateTime.date()
        self.flags = flags
        _date = msg["Date"]
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
        self.subject = self.decode_header_string(msg["Subject"])
        self.from_ = self.addresses_of_header(msg["From"])
        self.reply_to = self.addresses_of_header(msg["Reply-to"])
        self.to = self.addresses_of_header(msg["To"])
        self.cc = self.addresses_of_header(msg["Cc"])
        self.bcc = self.addresses_of_header(msg["Bcc"])

    def decode_header_string(self, _str):

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

    def addresses_of_header(self, addrs):
        if not addrs:
            return []
        result = []
        if type(addrs) == str:
            result.append(parseaddr(addrs))
        if hasattr(addrs, '_chunks'):
            addrs = decode_header(addrs)
            for addr in addrs:
                if addr[1] == 'unknown-8bit':
                    result.append(parseaddr(addr[0].decode('iso-8859-1', errors='replace')))
                else:
                    result.append(parseaddr(addr[0].decode()))
        return [(self.decode_header_string(name), self.decode_header_string(address)) for name, address in result]

    def __str__(self):
        return str(self.__dict__)

class Cross_Country_Imap_Connexion(BaseFilterElement):
    tokens = (
        "server", "user", "password", )
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
                pass #TODO

    def listFolders(self):
        #TODO list(directory='Archive')
        self.folders = []
        for f in self.M.list_folders():
            if self.server == 'imap.gmail.com':
                if f[2].startswith('[Gmail]'): continue
            self.folders.append(f[2])

    def deleteMessages(self, msgIds):
        if len(msgIds) == 0:
            return
        self.M.set_flags(msgIds, b'\\Deleted')
        self.toExpunge = True

    def copyMessages(self, msgIds, destination):
        if len(msgIds) == 0:
            return
        destination = self.validateFolderName(destination)
        self.M.copy(msgIds, destination)

    def moveMessages(self, msgIds, destination):
        if len(msgIds) == 0:
            return
        destination = self.validateFolderName(destination)
        self.M.copy(msgIds, destination)
        self.deleteMessages(msgIds)

    def flagMessages(self, msgIds, flag, set):
        if len(msgIds) == 0:
            return
        if set:
            self.M.set_flags(msgIds, flag)
        else:
            self.M.remove_flags(msgIds, flag)

    def expungeMailBox(self):
        if self.toExpunge:
            self.M.expunge()

    def messageHeaders(self, folder):
        folder = self.validateFolderName(folder)
        self.select_result = self.M.select_folder(folder)
        message_count = self.select_result[b'EXISTS']
        if self.verbose:
            print("Select %s folder : %s messages" % (folder, message_count))
        if message_count == 0:
            return None
        self.search_all_set = self.M.search()
        datas = self.M.fetch(self.search_all_set, ['RFC822.HEADER', 'INTERNALDATE', 'FLAGS'])
        for msg_Id in datas.keys():
            data = datas[msg_Id]
            internaldate = data[b'INTERNALDATE']
            flags = data[b'FLAGS']
            msg = message_from_bytes(data[b'RFC822.HEADER'])
            yield (Armoured_Message_Header(msg_Id, internaldate, flags, msg))
