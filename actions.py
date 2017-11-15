from filterElement import BaseFilterElement
import copy
from urllib import request, parse


class BaseAction(BaseFilterElement):
    def __init__(self, filter_processor, definition):
        self.filter_processor = filter_processor
        self.name = definition["name"]
        self.definition = definition
        self.logger = self.filter_processor.playbook_output
        self.filter = None
        self.folder = None

    # automatically created. if exist, replaced with the basic one
    basics = ["Count", "Delete", "Print", "Trash", "Seen", "Unseen", "Flag", "Unflag", "TotalSize"]

    def initialize_filter(self, _filter, folder):
        self.filter = _filter
        self.folder = folder

    def check_definition(self):
        pass

    def run_message(self, m):
        pass

    def begin(self):
        pass

    def end(self):
        pass

    @classmethod
    def newAction(cls, filter_processor, definition):
        _name = definition["name"]
        _type = definition["type"] + "Action"
        try:
            _newAction = {subcls.__name__: subcls
                          for subcls in cls.__subclasses__()}[_type](filter_processor, definition)
        except:  # TODO
            raise cls.CheckError('Playbook : "%s" : Action : "%s" unknown type "%s"\nAvailable types: %s' % (
                filter_processor.current_playbook, _name, definition["type"],
                tuple(subcls.__name__[:-len("Action")] for subcls in cls.__subclasses__())))
        _newAction.check_definition()
        return _newAction


class PrintAction(BaseAction):
    def run_message(self, _m):
        self.logger.info(_m)


class SeenAction(BaseAction):
    def end(self):
        self.filter_processor.imap_connexion.flag_messages(
            self.filter.IMAP_message_set, b'\\Seen', True)


class UnseenAction(BaseAction):
    def end(self):
        self.filter_processor.imap_connexion.flag_messages(
            self.filter.IMAP_message_set, b'\\Seen', False)


class FlagAction(BaseAction):
    def end(self):
        self.filter_processor.imap_connexion.flag_messages(
            self.filter.IMAP_message_set, b'\\Flagged', True)


class UnflagAction(BaseAction):
    def end(self):
        self.filter_processor.imap_connexion.flag_messages(
            self.filter.IMAP_message_set, '\\Flagged', False)


class DeleteAction(BaseAction):
    def end(self):
        self.filter_processor.imap_connexion.delete_messages(self.filter.IMAP_message_set)


class TrashAction(BaseAction):
    def end(self):
        self.filter_processor.imap_connexion.move_messages(self.filter.IMAP_message_set, "Trash")


class MoveAction(BaseAction):
    def check_definition(self):
        if not self.definition.get("destination"):
            raise self.CheckError('Playbook : "%s" : Action : "%s" : no destination\nAdd a destination folder'
                                  % (self.filter_processor.current_playbook , self.name))

    def end(self):
        self.filter_processor.imap_connexion.move_messages(self.filter.IMAP_message_set, self.definition["destination"])


class CopyAction(BaseAction):
    def check_definition(self):
        if not self.definition.get("destination"):
            raise self.CheckError('Playbook : "%s" : Action : "%s" : no destination\nAdd a destination folder'
                                  % (self.filter_processor.current_playbook , self.name))

    def end(self):
        self.filter_processor.imap_connexion.copy_messages(self.filter.IMAP_message_set, self.definition["destination"])


class CountAction(BaseAction):
    def end(self):
        self.logger.info('Filter "%s" : Folder "%s" : summary : %s message(s)' % (
            self.filter.definition.get("name"), self.folder, self.filter.message_count()))


class TotalSizeAction(BaseAction):
    total_size = 0
    folder_total_size = 0
    def begin(self):
        self.folder_total_size = 0

    def run_message(self, m):
        self.folder_total_size += m.size

    def end(self):
        if self.folder_total_size > 1024 * 1024 :
            self.folder_total_size_human = "%d Mo" % round(self.folder_total_size / (1024*1024), 2)
        else:
            self.folder_total_size_human = "%d Ko" % round(self.folder_total_size / 1024, 2)
        self.total_size += self.folder_total_size
        if self.total_size > 1024 * 1024 :
            self.total_size_human = "%d Mo" % round(self.total_size / (1024*1024), 2)
        else:
            self.total_size_human = "%d Ko" % round(self.total_size / 1024, 2)

        self.logger.info('Filter "%s" : Folder "%s" : summary : %s message(s), total folder size : %s, total size : %s' % (
            self.filter.definition.get("name"), self.folder, self.filter.message_count(), self.folder_total_size_human, self.total_size_human))

class UrlAction(BaseAction):
    def check_definition(self):
        self.url = self.definition["url"]
        self.data = self.definition["data"]

    def run_message(self, m):
        msg_data = []
        #  [key , value from yml],
        #  "user" , "foo"],
        #  "message", key, value from message
        #  "message", "msg", "subject"
        for l in copy.deepcopy(self.data):
            if len(l) == 3:
                l.pop(0)
                l[1] = m.__dict__[l[1]]
            msg_data.append(tuple(l))
        encoded_data = "?" + parse.urlencode(msg_data)
        full_url = self.url + encoded_data
        if self.definition.get("test"):
            self.logger.info("testing")
            self.logger.info(full_url)
        else:
            self.logger.info("calling")
            self.logger.info(full_url)
            response = request.urlopen(full_url)
            self.logger.info(response)
