#!/usr/bin/python3

'''
Created on 

@author: 
'''

class BaseFilterElement(object):
    class CheckError(Exception):
        pass

    tokens = ("name", "component", "crypted")
    pass
