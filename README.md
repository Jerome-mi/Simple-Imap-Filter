SimpleImapFilter is a simple IMAP filter written in python,
it is :
- not a stable program, but almost works, especially delete action

- based on the holy imapclient library

- using YAML for configuration file and filter configuration

- aimed to be used by (almost) human beings

**PRE REQUISITES** :
- python 3
- imap client
- linux machine but certainly works on others

**INSTALL** :
- install imapclient first of all

- send flowers to the imapclient developper

- rename conf.yml.sample to conf.yml

- run "SimpleImapFilter -s"
- and use output into conf.yml for salt

**USE** :

run SimpleImapFilter.py

option : 
-a full message anlysis, fetch all messages in all mailboxes, all folders, usefull for debug

the program "walk" the root directory and for all .yml file in subfolders run the .yml file

the program can be cronifized as it locks .yml files while filtering

each .yml file is composed by :
- one imap_client : with IMAP server and credentials
- a list of filters
- a dictionary of clauses
- a dictionary of actions

**Filters**

a filter **applies** an **ordered list of actions** on a list of messages matching with **ONE** of the clauses in his (ordered) clause list


**Actions**

basic actions are : "Count", "Delete", "Print", "Trash", "Seen", "Unseen", "Flag", "Unflag"

(they can be used even if not declared in .yml file)

DO NOT USE DELETE ACTION except if you have tested this program at least six month on your mailbox
USE TRASH ACTION if you want to safely delete your mails


non-basic actions are : "Url" (Alpha version), "Copy", "Move" 

-**Url** calls an Url

-**Copy** copy the filtered message set to his **destination**
 
-**Move** copy the filtered message set to his **destination** and **trash** it

**Clauses**

Clause is a list of condition, a clause is True when **ALL** conditions are True
implemented conditions are :         
        "to_domain", "to_full_domain", "to_name", "to_name_cs", "to",
        "from_domain", "from_full_domain", "from_name", "from_name_cs", "from",
        "subject_contains", "subject_starts",
        "subject_contains_cs", "subject_starts_cs",
        "age_day", "fresh_day",
        "seen", "flagged",

"cs" suffixes means case sensitive, other conditions are non case sensitive
