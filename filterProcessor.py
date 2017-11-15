import os
import yaml
import logging
import logging.handlers

from cryptography.fernet import Fernet

from filterElement import BaseFilterElement
from actions import BaseAction
from clauses import BaseClause
from filters import BaseFilter
from imapConnexion import CrossCountryImapConnexion


class FilterProcessor(object):
    """

    """
    class CheckError(Exception):
        pass

    element_types = ("imap_client", "filter", "action", "clause")
    default_root_dir = '../mailboxes.d'

    def __init__(self):
        self.args = None
        self.imap_connexion = None
        self.salt = None
        self.playbook_log_handler = None
        self.root_dir = self.default_root_dir
        self.current_playbook = ''
        self.imap_client = None
        self.playbook_filters = []
        self.playbook_actions = {}
        self.clauses = {}
        self.playbook_names = {}
        self.logger = logging.getLogger("FilterProcessorLogger")
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(self.formatter)
        self.logger.addHandler(ch)
        self.playbook_logger = logging.getLogger("PlaybookLogger")
        self.playbook_logger.setLevel(logging.INFO)
        self.playbook_output = logging.getLogger("PlaybookOutput")
        self.playbook_output.setLevel(logging.INFO)
        self.log_file = None

    def decrypt(self, s):
        try:
            s = bytes(s, "utf-8")
            cipher_suite = Fernet(self.salt)
            return cipher_suite.decrypt(s)
        except Exception:
            self.logger.error("Error during decrypt token %s\nCheck token and salt" % s)
            raise

    def encrypt_keys(self, full_file):
        if self.set_lock(full_file):
            try:
                self.logger.info('Reading key file : "%s"' % full_file)
                with open(full_file, 'r') as stream:
                    yaml_keys = yaml.load(stream)
                if not yaml_keys:
                    return
                cipher_suite = Fernet(self.salt)
                new_yaml_keys = {}
                for key in yaml_keys.keys():
                    if key.startswith('encrypt_'):
                        new_key = key.replace('encrypt_', 'encrypted_')
                        new_yaml_keys[new_key] = cipher_suite.encrypt(bytes(yaml_keys[key], "utf-8")).decode()
                    if key.startswith('encrypted_'):
                        new_yaml_keys[key] = yaml_keys[key]
                with open(full_file, 'w') as stream:
                    yaml.dump(new_yaml_keys, stream)
            except yaml.YAMLError:
                self.logger.error('YAML Error in playbook "%s" :' % full_file)
            finally:
                self.release_lock(full_file)

    def run(self, args):
        self.args = args

        self.logger.setLevel(logging.WARNING)
        if self.args.verbose:
            self.logger.setLevel(logging.INFO)
        if self.args.debug:
                self.logger.setLevel(logging.DEBUG)
        self.logger.info("Running in verbose mode")
        self.logger.info("Reading configuration file : %s" % self.args.conf)
        self.read_conf(self.args.conf)

        if self.args.salt:
            key = Fernet.generate_key()
            print(key.decode())
            exit(0)

        if self.args.encrypt:
            cipher_suite = Fernet(self.salt)
            encoded_text = cipher_suite.encrypt(bytes(self.args.encrypt, "utf-8"))
            print(encoded_text.decode())
            exit(0)

        for path, directory, files in os.walk(self.root_dir):
            for file in files:
                full_file = os.path.join(path, file)
                if file[-4:] == '.key':
                    self.encrypt_keys(full_file)
                    continue
                if file[-4:] != '.yml':
                    self.logger.debug('File "%s" not ending with .yml : skipped' % file)
                    continue
                with open(full_file, 'r') as stream:
                    if self.set_lock(full_file):
                        try:
                            self.playbook_log_handler = logging.handlers.RotatingFileHandler(
                                full_file[:-3] + "log", maxBytes=102400, backupCount=5)
                            self.playbook_log_handler.setFormatter(self.formatter)
                            self.playbook_logger.addHandler(self.playbook_log_handler)
                            playbook_output_handler = logging.FileHandler(full_file[:-3] + "out", mode='w')
                            self.playbook_output.addHandler(playbook_output_handler)
                            self.current_playbook = full_file
                            self.logger.info('Running playbook : "%s"' % full_file)
                            yamlcfg = yaml.load(stream)

                            self.run_playbook(yamlcfg, self.args)

                            self.logger.info('end of playbook : "%s"' % full_file)
                        except (BaseFilterElement.CheckError, self.CheckError) as chk:
                            self.logger.error(chk)
                            self.playbook_logger.error(chk)
                        except yaml.YAMLError:
                            self.logger.error('YAML Error in playbook "%s" :' % full_file)
                            self.playbook_logger.error('YAML Error in playbook "%s" :' % full_file)
                        except Exception as exc:
                            self.logger.error('Playbook "%s" in error : %s' % (full_file, exc))
                            self.playbook_logger.error('Playbook "%s" in error : %s' % (full_file, exc))
                            pass
                        finally:
                            self.release_lock(full_file)
                            self.playbook_logger.removeHandler(self.playbook_log_handler)
                            self.playbook_output.removeHandler(playbook_output_handler)

    def prepare_fetch_all(self, folders):
        self.playbook_output.info("Fetch all mailbox :%s" % self.imap_connexion.definition["name"])
        self.playbook_output.info("folders : " + str(folders))
        self.logger.info("Fetch all mailbox :%s" % self.imap_connexion.definition["name"])
        self.logger.info("folders : " + str(folders))
        self.playbook_filters = []
        self.playbook_actions = {}
        self.clauses = {}
        self.add_playbook_filter({
            "name": self.imap_connexion.server,
            "component": "filter",
            "folder_list": folders,
            "clause_list": ["All"],
            "action_list": ["Count"],
        })

    def prepare_analyse(self, folders):
        self.playbook_output.info("Analysing mailbox :%s" % self.imap_connexion.definition["name"])
        self.playbook_output.info("folders : " + str(folders))
        self.logger.info("Analysing mailbox :%s" % self.imap_connexion.definition["name"])
        self.logger.info("folders : " + str(folders))
        self.playbook_filters = []
        self.playbook_actions = {}
        self.clauses = {}
        self.add_playbook_filter({
            "name": self.imap_connexion.server,
            "component": "filter",
            "folder_list": folders,
            "clause_list": ["All"],
            "action_list": ["TotalSize"],
        })

    def read_conf(self, conf):
        with open(conf, 'r') as stream:
            try:
                yamlcfg = dict(yaml.load(stream)[0])
            except:  # TODO
                self.logger.error('Error in YAML configuration file %s :' % conf)
                raise
            self.salt = yamlcfg.get("salt")
            if self.salt:  # todo test isinstance str
                self.salt = bytes(self.salt, 'utf-8')
            else:
                if not self.args.salt:
                    self.logger.warning('No salt for password or sensible data encryption %s :' % conf)
            self.set_log_file(yamlcfg.get("log"))
            self.root_dir = yamlcfg.get("root_dir", self.default_root_dir)
            self.logger.info("Root directory : %s" % self.root_dir)

    def check_element(self, elt, i):
        _name = elt.get("name")
        if not _name:
            raise self.CheckError('Playbook "%s" : Missing name for element "%d"' % (self.current_playbook, i))
        if self.playbook_names.get(_name):
            raise self.CheckError('Playbook "%s" : Duplicating name %s for component "%d"' % (
                self.current_playbook, _name,  i))
        self.playbook_names[_name] = i
        _type = elt.get("component")
        if not _type:
            raise self.CheckError('Playbook "%s" : Missing component for element %d "%s"' % (
                self.current_playbook, i, _name))
        if _type not in self.element_types:
            raise self.CheckError('Playbook "%s" : Unknown component for element %d "%s"\nAvailable components : %s' % (
                self.current_playbook, i, _name, self.element_types))
        encrypted_fields = elt.get("encrypted")
        if encrypted_fields:
            for cf in encrypted_fields:
                if not elt.get(cf):
                    raise self.CheckError('Playbook "%s" : Missing encrypted value "%s" for component %d "%s"' % (
                        self.current_playbook, cf, i, _name))

    def decrypt_element(self, elt):
        encrypted_fields = elt.get("encrypted")
        if not encrypted_fields:
            return
        for cf in encrypted_fields:
            elt[cf] = self.decrypt(elt[cf])

    def parse_playbook(self, yamlcfg):
        for i, elt in enumerate(yamlcfg):
            self.check_element(elt, i)
            self.decrypt_element(elt)
            if elt["component"] == "imap_client":
                self.set_imap_connexion(elt)
            elif elt["component"] == "clause":
                self.add_playbook_clause(elt)
            elif elt["component"] == "filter":
                self.add_playbook_filter(elt)
            elif elt["component"] == "action":
                self.add_playbook_action(elt)

        for _action in self.playbook_actions.keys():
            _used = False
            for _filter in self.playbook_filters:
                if _action in _filter.definition["action_list"]:
                    _used = True
                    break
            if not _used:
                raise self.CheckError('Playbook "%s" : Action "%s" is not used in any filter"' % (
                    self.current_playbook, _action))

        for _clause in self.clauses.keys():
            _used = False
            for _filter in self.playbook_filters:
                if _clause in _filter.definition["clause_list"]:
                    _used = True
                    break
            if not _used:
                raise self.CheckError('Playbook "%s" : Clause "%s" is not used in any filter"' % (
                    self.current_playbook, _clause))

    def run_playbook(self, yamlcfg, args):
        self.clear_processor()
        self.parse_playbook(yamlcfg)
        try:
            self.imap_connexion.login()
            if args.fetchAll:
                self.prepare_fetch_all(self.imap_connexion.folders)
            elif args.analyse:
                self.prepare_analyse(self.imap_connexion.folders)
            for basicAction in BaseAction.basics:
                self.add_playbook_action({"name": basicAction, "component": "action", "type": basicAction})
            for basicClause in BaseClause.basics:
                self.add_playbook_clause({"name": basicClause, "component": "clause", basicClause: "yes"})
            for f in self.playbook_filters:
                f.run()
        finally:
            self.imap_connexion.disconnect()

    def clear_processor(self):
        self.imap_client = None
        self.playbook_filters = []
        self.playbook_actions = {}
        self.clauses = {}
        self.playbook_names = {}

    def add_playbook_action(self, definition):
        self.playbook_actions[definition["name"]] = BaseAction.newAction(self, definition)

    def add_playbook_filter(self, definition):
        self.playbook_filters.append(BaseFilter(self, definition))

    def add_playbook_clause(self, definition):
        self.clauses[definition["name"]] = BaseClause(self, definition)

    def set_imap_connexion(self, definition):
        server = definition.get("server")
        user = definition.get("user")
        password = definition.get("password")
        if not (server and user and password):
            raise self.CheckError("server, user and password are mandatory for imap_client component")
        self.imap_connexion = CrossCountryImapConnexion(self, definition, self.args)

    def set_log_file(self, log_file_name):
        if log_file_name:
            self.log_file = log_file_name
            self.logger.addHandler(logging.handlers.RotatingFileHandler(self.log_file, maxBytes=102400, backupCount=5))

    def set_lock(self, file_to_lock):
        result = not os.path.exists(file_to_lock + '.lock')
        if result:
            open(file_to_lock + '.lock', mode='w')
        else:
            self.logger.info('Playbook "%s" locked, skipped' % file_to_lock)
        return result

    @staticmethod
    def release_lock(file_to_lock):
        os.unlink(file_to_lock + '.lock')
