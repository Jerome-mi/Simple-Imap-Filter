#!/usr/bin/python3

'''
Created on 

@author: 
'''

#http://irp.nain-t.net/doku.php/190imap:030_commandes
from datetime import date, timedelta
from filterElement import BaseFilterElement

class BaseClause(BaseFilterElement):
    tokens = (
        "to_domain", "to_full_domain", "to_name", "to_name_cs", "to",
        "from_domain", "from_full_domain", "from_name", "from_name_cs", "from",
        # subject
        "subject_contains", "subject_starts",
        "subject_contains_cs", "subject_starts_cs",
        "age_day", "fresh_day",
        "seen", "flagged",
    )

    def __init__(self, filterProcessor, definition):
        self.filterProcessor = filterProcessor
        self.definition = definition
        self.conditions = []

        for _token in set(self.definition.keys()) - set(BaseFilterElement.tokens):
            if not _token in self.tokens:
                raise Exception('File : "%s" Clause : "%s" unknown token : "%s"\nAvailable tokens : %s' % (
                    self.filterProcessor.currentfile, self.definition["name"], _token, self.tokens))

        for _token in self.tokens:
            if not (self.definition.get(_token) is None):
                self.conditions.append((self.__getattribute__("match_"+_token), self.definition[_token]))

        if len(self.conditions) == 0:
            raise Exception('File : "%s" Clause : "%s" is empty\nAdd a condition to the clause' % (
                self.filterProcessor.currentfile, self.definition["name"]))

    def _adrInAddressList(self, _criteria, _addressList):
        """
        Match if address in address list, NO CASE SENSITIVE
        :param _criteria:
        :param _addressList:
        :return:
        """
        _criteria = _criteria.upper()
        _match = False
        for _address in _addressList:
            _match = _match or _address[1].upper() == _criteria
            if _match: break
        return _match

    def _fullDomainInAddressList(self, _criteria, _addressList):
        """
        Match if full domain in address list, NO CASE SENSITIVE
        :param _criteria:
        :param _addressList:
        :return:
        """
        _criteria = _criteria.upper()
        _match = False
        for _address in _addressList:
            _match = _match or _address[1].split("@")[1].upper() == _criteria
            if _match: break
        return _match

    def _domainInAddressList(self, _criteria, _addressList):
        """
        Match if full domain in address list, NO CASE SENSITIVE
        :param _criteria:
        :param _addressList:
        :return:
        """
        _criteria = _criteria.upper()
        _match = False
        for _address in _addressList:
            if _address[1]:
                _match = _match or _address[1].split("@")[1].upper().endswith(_criteria)
            if _match: break
        return _match

    def _nameInAddressList(self, _criteria, _addressList):
        """
        Match if name in address list, NO CASE SENSITIVE
        :param _criteria:
        :param _addressList:
        :return:
        """
        _match = False
        for _address in _addressList:
            if _address[0]:
                _match = _match or _address[0].upper() == _criteria.upper()
            if _match: break
        return _match

    def _nameInAddressList_cs(self, _criteria, _addressList):
        """
        Match if name in address list, CASE SENSITIVE
        :param _criteria:
        :param _addressList:
        :return:
        """
        _match = False
        for _address in _addressList:
            if _address[0]:
                _match = _match or _address[0] == _criteria
            if _match: break
        return _match

    def match_age_day(self, _criteria, _header):
        return (date.today() - _header.date ) >= timedelta(days=_criteria)

    def match_fresh_day(self, _criteria, _header):
        return (date.today() - _header.date ) < timedelta(days=_criteria)

    # from
    def match_from_domain(self, _criteria, _header):
        return self._domainInAddressList(_criteria, _header.from_)

    def match_from_full_domain(self, _criteria, _header):
        return self._fullDomainInAddressList(_criteria, _header.from_)

    def match_from_name(self, _criteria, _header):
        return self._nameInAddressList(_criteria, _header.from_)

    def match_from_name_cs(self, _criteria, _header):
        return self._nameInAddressList(_criteria, _header.from_)

    def match_from(self, _criteria, _header):
        return self._adrInAddressList(_criteria, _header.from_)

    # to
    def match_to_domain(self, _criteria, _header):
        return self._domainInAddressList(_criteria, _header.to)

    def match_to_full_domain(self, _criteria, _header):
        return self._fullDomainInAddressList(_criteria, _header.to)

    def match_to_name(self, _criteria, _header):
        return self._nameInAddressList(_criteria, _header.to)

    def match_to_name_cs(self, _criteria, _header):
        return self._nameInAddressList_cs(_criteria, _header.to)

    def match_to(self, _criteria, _header):
        return self._adrInAddressList(_criteria, _header.to)

    # subject
    def match_subject_starts(self, _criteria, _header):
        return _header.subject.startswith(_criteria)

    def match_subject_contains(self, _criteria, _header):
        return _criteria in _header.subject

    def match_subject_starts_cs(self, _criteria, _header):
        return _header.subject.upper().startswith(_criteria.upper())

    def match_subject_contains_cs(self, _criteria, _header):
        return _criteria.upper() in _header.subject.upper()

    #flags
    def match_flagged(self, _criteria, _header):
        return _criteria ^ (not b'\\Flagged' in _header.flags)

    def match_seen(self, _criteria, _header):
        return _criteria ^ (not b'\\Seen' in _header.flags)

    # generic match
    def match(self, _header):
        _match = True
        for condition, criteria in self.conditions:
            _match = _match and condition(criteria, _header)
            if not _match: break
        return _match