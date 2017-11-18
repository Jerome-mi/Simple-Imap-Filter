from filterElement import BaseFilterProcessorElement
import logging


class BaseFilter(BaseFilterProcessorElement):
    tokens = (
        "folder_list", "clause_list", "action_list", "explain")

    def __init__(self, filter_processor, definition):
        """
        """
        self.filter_processor = filter_processor
        self.logger = self.filter_processor.playbook_logger
        self.definition = definition
        self.folders = definition.get("folder_list")
        self.clauses = []
        self.actions = []
        self.IMAP_message_IDs = []
        self.explain = definition.get("explain")
        if self.explain is None:
            self.explain = False
        for _token in set(self.definition.keys()) - set(BaseFilterProcessorElement.tokens):
            if _token not in self.tokens:
                raise self.CheckError('Playbook : "%s" Filter : "%s" unknown token : "%s"\nAvailable tokens : %s' % (
                    self.filter_processor.current_playbook, self.definition["name"], _token, self.tokens))

    def run(self):
        """ Run filter, check coherence actions filters and process message set
        :return:
        """
        for _clauseName in self.definition.get('clause_list', []):
            clause = self.filter_processor.clauses.get(_clauseName)
            if not clause:
                raise self.CheckError('Playbook "%s" : Filter "%s" : unknown clause : "%s"\nAvailable clauses: %s' % (
                    self.filter_processor.current_playbook, self.definition["name"], _clauseName,
                    tuple(self.filter_processor.clauses.keys())))
            self.clauses.append(clause)
        for _actionName in self.definition.get('action_list', []):
            if not self.filter_processor.playbook_actions.get(_actionName):
                raise self.CheckError('Playbook "%s" : Filter "%s" : unknown action : "%s"\nAvailable actions : %s' % (
                    self.filter_processor.current_playbook, self.definition["name"], _actionName,
                    tuple(self.filter_processor.playbook_actions.keys())))
            self.actions.append(self.filter_processor.playbook_actions[_actionName])
        if (self.folders is None) or (len(self.folders) == 0):
            self.folders = self.filter_processor.imap_connexion.folders
        playbook_log_level = self.logger.level
        if self.explain:
            self.logger.setLevel(logging.DEBUG)
        try:
            for _folder in self.folders:
                self.process_message_set(_folder)
        finally:
            self.logger.setLevel(playbook_log_level)

    def process_message_set(self, _folder):
        """ Applies actions on messages
        :return:
        """
        self.IMAP_message_IDs = []

        self.logger.debug('"%s" start running in explain  mode' % self.definition["name"])
        for clause in self.clauses:
            self.logger.debug('Clause "%s" ' % clause.definition)
        for _action in self.actions:
            _action.initialize_filter(self, _folder)

        for _action in self.actions:
            _action.begin()

        for _m in self.message_set(_folder):
            self.IMAP_message_IDs.append(_m.msgID)
            for _action in self.actions:
                _action.run_message(_m)

        for _action in self.actions:
            _action.end()

        self.logger.debug('"%s" end running in explain  mode' % self.definition["name"])

    def message_count(self):
        return len(self.IMAP_message_IDs)

    def match(self, m):
        """ match if ONE clause matches short boolean evaluation
        :param m:
        :return: boolean
        """
        self.logger.debug('Message Header "%s" ' % m)
        if len(self.clauses) == 0:
            return False
        _match = False
        for clause in self.clauses:
            _match = _match or clause.match(m)
            if _match:
                self.logger.debug('"%s" matches' % clause.definition["name"])
                break
        return _match

    def message_set(self, folder):
        """ filtered message header generator
        :return:
        """
        for _m in self.filter_processor.imap_connexion.message_headers(folder):
            if self.match(_m):
                yield _m
