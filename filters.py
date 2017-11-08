from filterElement import BaseFilterElement


class BaseFilter(BaseFilterElement):
    tokens = (
        "folder_list", "clause_list", "action_list", )

    def __init__(self, _filter_processor, _definition):
        """
        """
        self.filter_processor = _filter_processor
        self.definition = _definition
        self.folders = _definition.get("folder_list")
        if not self.folders:
            raise self.CheckError('Playbook : "%s" Filter : "%s" no folder list \nAdd token "folder_list"' % (
                self.filter_processor.current_playbook, self.definition["name"]))
        self.clauses = []
        self.actions = []
        self.IMAP_message_set = []

        for _token in set(self.definition.keys()) - set(BaseFilterElement.tokens):
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
        for _folder in self.folders:
            self.process_message_set(_folder)

    def process_message_set(self, _folder):
        """ Applies actions on messages
        :return:
        """
        self.IMAP_message_set = []
        for _action in self.actions:
            _action.initialize_filter(self, _folder)
        for _action in self.actions:
            _action.begin()
        for _m in self.message_set(_folder):
            self.IMAP_message_set.append(_m.msgID)
            for _action in self.actions:
                _action.run_message(_m)
        for _action in self.actions:
            _action.end()

    def message_count(self):
        return len(self.IMAP_message_set)

    def match(self, m):
        """ match if ONE clause matches short boolean evaluation
        :param m:
        :return: boolean
        """
        if len(self.clauses) == 0:
            return False
        _match = False
        for clause in self.clauses:
            _match = _match or clause.match(m)
            if _match:
                break
        return _match

    def message_set(self, folder):
        """ filtered message header generator
        :return:
        """
        for _m in self.filter_processor.imap_connexion.message_headers(folder):
            if self.match(_m):
                yield _m
