#!/usr/bin/python3

import argparse
from filterProcessor import FilterProcessor

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-e", "--encrypt", help="encrypt password and exit")
    argparser.add_argument("-s", "--salt", help="generates salt for encryption and exit",
                           action="store_true", default=False)
    argparser.add_argument("-c", "--conf", help="use configuration file CONF", default="./conf.yml")
    # argparser.add_argument("-t", "--test", help="test configuration and connection", action="store_true", default=False)
    argparser.add_argument("-v", "--verbose", help="verbose mode", action="store_true", default=False)
    argparser.add_argument("-d", "--debug", help="more verbose mode", action="store_true", default=False)
    argparser.add_argument("-a", "--analyse", help="count messages and totalize size for all folders", action="store_true", default=False)
    argparser.add_argument("-f", "--fetchAll", help="fetch all messages in all folders and count",
                           action="store_true", default=False)

    args = argparser.parse_args()

    FilterProcessor().run(args)
