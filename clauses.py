from datetime import date, timedelta
from filterElement import BaseFilterElement


class BaseClause(BaseFilterElement):

    tokens = (
        "to_domain", "to_full_domain", "to_name", "to_name_cs", "to",
        "from_domain", "from_full_domain", "from_name", "from_name_cs", "from",
        "subject_contains", "subject_starts",
        "subject_contains_cs", "subject_starts_cs",
        "age_day", "fresh_day",
        "size_ko", "size_mo",
        "seen", "flagged",
        "All",
    )

    # automatically created. if exist, replaced with the basic one
    basics = ["All", ]

    def __init__(self, filter_processor, definition):
        self.filter_processor = filter_processor
        self.definition = definition
        self.conditions = []

        for token in set(self.definition.keys()) - set(BaseFilterElement.tokens):
            if token not in self.tokens:
                raise self.CheckError('Playbook : "%s" Clause : "%s" unknown token : "%s"\nAvailable tokens : %s' % (
                    self.filter_processor.current_playbook, self.definition["name"], token, self.tokens))

        for token in self.tokens:
            if not (self.definition.get(token) is None):
                self.conditions.append((self.__getattribute__("match_" + token), self.definition[token]))

        if len(self.conditions) == 0:
            raise self.CheckError('Playbook : "%s" Clause : "%s" is empty\nAdd a condition to the clause' % (
                self.filter_processor.current_playbook, self.definition["name"]))

    @staticmethod
    def adr_in_address_list(criteria, address_list):
        """
        Match if address in address list, NO CASE SENSITIVE
        :param criteria:
        :param address_list:
        :return:
        """
        criteria = criteria.upper()
        match = False
        for _address in address_list:
            match = match or _address[1].upper() == criteria
            if match:
                break
        return match

    @staticmethod
    def full_domain_in_address_list(criteria, address_list):
        """
        Match if full domain in address list, NO CASE SENSITIVE
        :param criteria:
        :param address_list:
        :return:
        """
        criteria = criteria.upper()
        match = False
        for _address in address_list:
            match = match or _address[1].split("@")[1].upper() == criteria
            if match:
                break
        return match

    @staticmethod
    def domain_in_address_list(criteria, address_list):
        """
        Match if full domain in address list, NO CASE SENSITIVE
        :param criteria:
        :param address_list:
        :return:
        """
        criteria = criteria.upper()
        match = False
        for _address in address_list:
            if _address[1]:
                match = match or _address[1].split("@")[1].upper().endswith(criteria)
            if match:
                break
        return match

    @staticmethod
    def name_in_address_list(criteria, address_list):
        """
        Match if name in address list, NO CASE SENSITIVE
        :param criteria:
        :param address_list:
        :return:
        """
        match = False
        for _address in address_list:
            if _address[0]:
                match = match or _address[0].upper() == criteria.upper()
            if match:
                break
        return match

    @staticmethod
    def name_in_address_list_cs(criteria, address_list):
        """
        Match if name in address list, CASE SENSITIVE
        :param criteria:
        :param address_list:
        :return:
        """
        match = False
        for _address in address_list:
            if _address[0]:
                match = match or _address[0] == criteria
            if match:
                break
        return match

    @staticmethod
    def match_age_day(criteria, header):
        return (date.today() - header.date) >= timedelta(days=criteria)

    @staticmethod
    def match_fresh_day(criteria, header):
        return (date.today() - header.date) < timedelta(days=criteria)

    # from
    def match_from_domain(self, criteria, header):
        return self.domain_in_address_list(criteria, header.from_)

    def match_from_full_domain(self, criteria, header):
        return self.full_domain_in_address_list(criteria, header.from_)

    def match_from_name(self, criteria, header):
        return self.name_in_address_list(criteria, header.from_)

    def match_from_name_cs(self, criteria, header):
        return self.name_in_address_list(criteria, header.from_)

    def match_from(self, criteria, header):
        return self.adr_in_address_list(criteria, header.from_)

    # to
    def match_to_domain(self, criteria, header):
        return self.domain_in_address_list(criteria, header.to)

    def match_to_full_domain(self, criteria, header):
        return self.full_domain_in_address_list(criteria, header.to)

    def match_to_name(self, criteria, header):
        return self.name_in_address_list(criteria, header.to)

    def match_to_name_cs(self, criteria, header):
        return self.name_in_address_list_cs(criteria, header.to)

    def match_to(self, criteria, header):
        return self.adr_in_address_list(criteria, header.to)

    # subject
    @staticmethod
    def match_subject_starts(criteria, header):
        return header.subject.startswith(criteria)

    @staticmethod
    def match_subject_contains(criteria, header):
        return criteria in header.subject

    @staticmethod
    def match_subject_starts_cs(criteria, header):
        return header.subject.upper().startswith(criteria.upper())

    @staticmethod
    def match_subject_contains_cs(criteria, header):
        return criteria.upper() in header.subject.upper()

    # flags
    @staticmethod
    def match_flagged(criteria, header):
        return criteria == (b'\\Flagged' in header.flags)

    @staticmethod
    def match_seen(criteria, header):
        return criteria == (b'\\Seen' in header.flags)

    # size
    @staticmethod
    def match_size_ko(criteria, header):
        return header.size >= (criteria * 1024)

    @staticmethod
    def match_size_mo(criteria, header):
        return header.size >= (criteria * 1024 * 1024)

    # specials
    @staticmethod
    def match_All(criteria, header):
        return True

    # generic match
    def match(self, header):
        match = True
        for condition, criteria in self.conditions:
            match = match and condition(criteria, header)
            if not match:
                break
        return match
