from imaplib import IMAP4
import ssl

from datetime import datetime, date

from email import message_from_bytes
from email.header import decode_header, Header
from email.utils import parseaddr, parsedate_tz

import imapclient
from filterElement import BaseFilterElement


class ArmouredMessageHeader(object):
    def __init__(self, msg_id, internal_date, flags, size, msg):
        self.msgID = msg_id
        self.internalDateTime = internal_date
        self.internalDate = self.internalDateTime.date()
        self.flags = flags
        self.size = size
        _date = msg["Date"]
        date_time_tuple = None
        if _date:
            if isinstance(_date, Header):
                _date = str(_date)
                _date = _date[:_date.find('(')]
            date_time_tuple = parsedate_tz(_date)
        # none if date without TZ
        if date_time_tuple:
            self.date = date(*date_time_tuple[:3])
            self.datetime = datetime(*date_time_tuple[:6])
        else:
            self.date = self.internalDate
            self.datetime = self.internalDateTime
        self.subject = self.decode_header_string(msg["Subject"])
        self.from_ = self.addresses_of_header(msg["From"])
        self.reply_to = self.addresses_of_header(msg["Reply-to"])
        self.to = self.addresses_of_header(msg["To"])
        self.cc = self.addresses_of_header(msg["Cc"])
        self.bcc = self.addresses_of_header(msg["Bcc"])

    @staticmethod
    def decode_header_string(_str):
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


class CrossCountryImapConnexion(BaseFilterElement):
    tokens = (
        "server", "user", "password", )

    def __init__(self, filter_processor, definition, args):
        self.verbose = args.verbose
        self.definition = definition
        self.filter_processor = filter_processor
        self.server = definition["server"]
        self.user = definition["user"]
        self.password = definition["password"]
        self.to_expunge = False
        self.select_result = None
        self.folders = None
        self.search_all_result_set = None
        try:
            self.M = imapclient.IMAPClient(self.server, ssl=True)
        except IMAP4.error:
            ssl_context = ssl.create_default_context()
            self.M = imapclient.IMAPClient(self.server, ssl_context=ssl_context, ssl=True)
        for token in set(self.definition.keys()) - set(BaseFilterElement.tokens):
            if token not in self.tokens:
                raise Exception('Playbook : "%s" Imap_client : "%s" unknown token : "%s"\nAvailable tokens : ' % (
                    self.filter_processor.current_playbook, self.definition["name"], token))

    def login(self):
        self.to_expunge = False
        if self.verbose:
            print("Connecting to : %s user %s" % (self.server, self.user))
        cnx = self.M.login(self.user, self.password.decode())
        if cnx and self.verbose:
            print("Connected to : %s" % self.server)
        self.list_folders()

    def validate_folder_name(self, folder):
        if folder not in self.folders:
            folder = '"' + folder + '"'
        if folder not in self.folders:
            raise Exception("Folder %s doesn't exists.\nAvailable folders : %s " % (folder, self.folders))
        return folder

    def disconnect(self):
        self.expunge_mail_box()
        if self.M:
            try:
                self.M.logout()
            except:
                pass  # TODO

    def list_folders(self):
        # TODO list(directory='Archive')
        self.folders = []
        for f in self.M.list_folders():
            if self.server.upper() == 'IMAP.GMAIL.COM':
                if f[2].startswith('[Gmail]'):
                    continue
            self.folders.append(f[2])

    def delete_messages(self, msg_ids):
        if len(msg_ids) == 0:
            return
        self.M.set_flags(msg_ids, b'\\Deleted')
        self.to_expunge = True

    def copy_messages(self, msg_ids, destination):
        if len(msg_ids) == 0:
            return
        destination = self.validate_folder_name(destination)
        self.M.copy(msg_ids, destination)

    def move_messages(self, msg_ids, destination):
        # if len(msg_ids) == 0:
        #     return
        # destination = self.validate_folder_name(destination)
        self.copy_messages(msg_ids, destination)
        self.delete_messages(msg_ids)

    def flag_messages(self, msg_ids, flag, on):
        if len(msg_ids) == 0:
            return
        if on:
            self.M.add_flags(msg_ids, flag)
        else:
            self.M.remove_flags(msg_ids, flag)

    def expunge_mail_box(self):
        if self.to_expunge:
            self.M.expunge()

    def message_headers(self, folder):
        folder = self.validate_folder_name(folder)
        self.select_result = self.M.select_folder(folder)
        message_count = self.select_result[b'EXISTS']
        if self.verbose:
            print("Select %s folder : %s messages" % (folder, message_count))
        if message_count == 0:
            return None
        self.search_all_result_set = self.M.search()
        datas = self.M.fetch(self.search_all_result_set, ['RFC822.SIZE', 'RFC822.HEADER', 'INTERNALDATE', 'FLAGS'])
        for msg_Id in datas.keys():
            data = datas[msg_Id]
            internal_date = data[b'INTERNALDATE']
            flags = data[b'FLAGS']
            size = data[b'RFC822.SIZE']
            msg = message_from_bytes(data[b'RFC822.HEADER'])
            yield (ArmouredMessageHeader(msg_Id, internal_date, flags, size, msg))
