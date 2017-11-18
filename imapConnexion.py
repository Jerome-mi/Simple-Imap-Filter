from imaplib import IMAP4
import ssl

from datetime import datetime, date

from email import message_from_bytes
from email.header import decode_header, Header
from email.utils import parseaddr, parsedate_tz

import imapclient
from filterElement import BaseFilterProcessorElement


class ArmouredMessageHeader(object):
    def __init__(self, imap_connexion, folder, msg_id, internal_date, flags, size, msg):
        self.imap_connexion = imap_connexion
        self.folder = folder
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
        self._body = None

    def get_body(self):
        if self._body:
            self.imap_connexion.logger.info(
                'Fetch body for message "%s" in folder "%s" : in cache' % (self.msgID, self.folder))
            return self._body
        else:
            self._body = self.imap_connexion.fetch_text_message_body(self.folder, self.msgID)
            return self._body

    @staticmethod
    def decode_header_string(_str):
        if not _str:
            return ''
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
        output = []
        output.append(("ID", self.msgID))
        output.append(("datetime", self.datetime))
        output.append(("subject", self.subject))
        output.append(("from", self.from_))
        output.append(("to", self.to))
        output.append(("reply_to", self.reply_to))
        output.append(("cc", self.cc))
        output.append(("bcc", self.bcc))
        output.append(("size", self.size))
        output.append(("flags", self.flags))
        return str(output)


class CrossCountryImapConnexion(BaseFilterProcessorElement):
    tokens = (
        "server", "user", "password", )

    def __init__(self, filter_processor, definition):
        self.definition = definition
        self.filter_processor = filter_processor
        self.logger = filter_processor.logger
        self.server = definition["server"]
        self.user = definition["user"]
        self.password = definition["password"]
        self.to_expunge = False
        self.select_result = None
        self.folders = None
        self.search_all_result_set = None
        self.folder_cache = {}
        try:
            self.M = imapclient.IMAPClient(self.server, ssl=True)
        except IMAP4.error:
            ssl_context = ssl.create_default_context()
            self.M = imapclient.IMAPClient(self.server, ssl_context=ssl_context, ssl=True)
        for token in set(self.definition.keys()) - set(BaseFilterProcessorElement.tokens):
            if token not in self.tokens:
                raise Exception('Playbook : "%s" Imap_client : "%s" unknown token : "%s"\nAvailable tokens : ' % (
                    self.filter_processor.current_playbook, self.definition["name"], token))

    def login(self):
        self.to_expunge = False
        self.logger.info('Connecting to : "%s" user %s' % (self.server, self.user))
        cnx = self.M.login(self.user, self.password.decode())
        if cnx:
            self.logger.info('Connected to : "%s"' % self.server)
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
                self.logger.info('Disconnecting from : "%s" user %s' % (self.server, self.user))
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
        header_set = self.get_folder_message_header_set(folder)
        for msg_Id in header_set.keys():
            data = header_set[msg_Id]
            internal_date = data[b'INTERNALDATE']
            flags = data[b'FLAGS']
            size = data[b'RFC822.SIZE']
            msg = message_from_bytes(data[b'RFC822.HEADER'])
            yield ArmouredMessageHeader(self, folder, msg_Id, internal_date, flags, size, msg)

    def store_folder_message_header_set(self, folder):
        self.select_result = self.M.select_folder(folder)
        message_count = self.select_result[b'EXISTS']
        self.logger.info('Select "%s" folder : %s messages' % (folder, message_count))
        if message_count == 0:
            fetched_data_set = {}
        else:
            self.search_all_result_set = self.M.search()
            fetched_data_set = self.M.fetch(
                self.search_all_result_set, ['RFC822.SIZE', 'RFC822.HEADER', 'INTERNALDATE', 'FLAGS'])
        self.logger.info('Fetched "%s" folder : %s messages' % (folder, message_count))
        self.folder_cache[folder] = fetched_data_set
        return fetched_data_set

    def get_folder_message_header_set(self, folder):
        result = self.folder_cache.get(folder)
        if result:
            self.logger.info('Select "%s" folder : in cache' % folder)
            return result
        else:
            return self.store_folder_message_header_set(folder)

    def fetch_text_message_body(self, folder, msgID):
        self.logger.info('Fetch body for message "%s" in folder "%s"' % (msgID, folder))
        self.M.select_folder(folder)
        fetched_body = self.M.fetch([msgID], ['RFC822'])
        msg = message_from_bytes(fetched_body[msgID][b'RFC822'])
        msg_text = ''
        if msg.is_multipart():
            for part in msg.walk():
                msg_text = msg_text + self.decode_text_body_part(part)
        else:
            msg_text = self.decode_text_body_part(msg)
        self.logger.info('Fetched body for message "%s" in folder "%s"' % (msgID, folder))
        return msg_text

    @staticmethod
    def decode_text_body_part(msg_part):
        ct = msg_part.get_content_type()
        cc = msg_part.get_content_charset()  # charset in Content-Type header
        # cte = msg_part.get("Content-Transfer-Encoding")
        # print("part: " + str(ct) + " " + str(cc) + " : " + str(cte))

        if msg_part.get_content_maintype() != "text":
            return ''
        if msg_part.get_content_subtype() != "plain":
            return ''
        result = msg_part.get_payload(decode = True).decode(cc)
        # # html to text
        # if msg.get_content_subtype() == "html":
        #     try:
        #         ddd = html2text.html2text(ddd)
        #     except:
        #         print("error in html2text")
        #
        return result


# def decode_text(payload, charset, default_charset):
#     if charset:
#         try:
#             return payload.decode(charset), charset
#         except UnicodeError:
#             pass
#
#     if default_charset and default_charset != 'auto':
#         try:
#             return payload.decode(default_charset), default_charset
#         except UnicodeError:
#             pass
#
#     for chset in ['ascii', 'utf-8', 'utf-16', 'windows-1252', 'cp850']:
#         try:
#             return payload.decode(chset), chset
#         except UnicodeError:
#             pass
#
#     return payload, None
