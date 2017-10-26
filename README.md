SimpleImapFilter is a simple IMAP filter written in python,
it is :
- not yet a stable program, but almost works, especially the delete action

- based on the holy imapclient library

- using YAML for configuration file and filters configuration

- aimed to be used by (almost) human beings

**PRE REQUISITES** :
- python 3
- imapclient
- linux machine but certainly works on others

**INSTALL** :
- install imapclient first of all

- send flowers to the imapclient developper

- rename conf.yml.sample to conf.yml

- run "SimpleImapFilter -s" to generate a salt key, and use output into conf.yml for salt

**CONFIGURE FILTERS**
- copy one of the sample files into a sub directory of mailboxes.d
- rename it as .yml file
- configure it with imap server and credentials
run SimpleImapFilter -e <password> to encrypt your password
- copy the output into configuration file
- add clauses, actions if needed, and filter(s)

**USE** :

run SimpleImapFilter.py

options :
-c to specify a configuration file, ./conf.yml by default
-d, -v verbose mode, d for debug
-s generates salt key
-e encrypt password or any value to be encrypted in configurations files
-a full message anlysis, fetch all messages in all mailboxes, all folders, usefull for debug. It is equivalent of a filter linked to all folders of a mailbox, with the clause "All" and the action "Count"

the program "walks" the root directory, for all .yml file in subfolders "runs" the file

the program can be cronifized as it locks .yml files while filtering, so if launched while previous process is still running will not cause any trouble

the program outputs it's log into a specific log file for each .yml file, in the same place 

each .yml file is composed by components :
- one imap_client : with IMAP server and credentials
- filters
- clauses
- actions

**Filters**

a filter **applies** an **ordered list of actions** on a list of messages matching with **ONE** of the clauses in his (ordered) clause list
if the clause list of a filter is empty, no messages will pass through it
to perform actions to all messages of a folder, use the basic clause "All" which is provided by default


**Actions**

basic actions are : "Count", "Delete", "Print", "Trash", "Seen", "Unseen", "Flag", "Unflag"

(they can be used even if not declared in .yml file)

DO NOT USE DELETE ACTION except if you have tested this program at least six month on your mailbox
USE TRASH ACTION if you want to safely delete your mails


non-basic actions are : "Url" (Alpha version), "Copy", "Move" 

-**Url** calls an Url

-**Copy** copy the filtered message set to his **destination**
 
-**Move** copy the filtered message set to his **destination** and **delete** it

**Clauses**

Clause is a list of condition, a clause is True when **ALL** conditions are True
implemented conditions are :         
        "to_domain", "to_full_domain", "to_name", "to_name_cs", "to",
        "from_domain", "from_full_domain", "from_name", "from_name_cs", "from",
        "subject_contains", "subject_starts",
        "subject_contains_cs", "subject_starts_cs",
        "age_day", "fresh_day",
        "seen", "flagged",
        "All",

"cs" suffixes means case sensitive, other conditions are non case sensitive
"All" condition is allways true, it is used by the basic clause "All" which is provided by default
