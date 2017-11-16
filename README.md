SimpleImapFilter is a simple IMAP filter written in python,
it is :

- not yet a stable program, but almost works, especially the delete action

- documented by me, so in poor english

- based on the holy imapclient library

- using YAML for configuration file and filters configuration, called playbooks

- using logging module to perform output and logs

- only fetching header of messages and body only when needed

- not fully optimized for the moment

and :

- aimed to be used by (almost) human beings, even if it's not obvious for the moment

**PRE REQUISITES** :
- python 3
- imapclient
- linux machine but certainly works on others

**INSTALL** :
- install imapclient

- send flowers to the imapclient developer

- rename conf.yml.sample to conf.yml

- run "SimpleImapFilter.py -s" to generate a salt key, and use the output into conf.yml for salt

**CONFIGURE FILTERS**
- copy one of the sample playbook files into a sub directory of mailboxes.d
- rename it as ".yml"
- configure it with imap server and login
- run SimpleImapFilter -e <password> to encrypt your password
- copy the output into the playbook
- add clauses, actions if needed, and filter(s) in the playbook

**USE** :

run SimpleImapFilter.py

options :
-c to specify a configuration file, ./conf.yml by default
-d, -v : verbose mode, d for debug
-s generates salt key
-e encrypt password or any value to be encrypted in playbooks
-f fetch all messages in all mailboxes, all folders, useful for debug. It is equivalent of a filter linked to all folders of a mailbox, with the clause "All" and the action "Count"
-a analyse messages in all mailboxes, all folders, and print count and size. It is equivalent of a filter linked to all folders of a mailbox, with the clause "All" and the action "TotalSize"

fetch all and analyse options deactivate other filters and actions, it is equivalent to a dry run.

the program "walks" the root directory, for each playbook (.yml file) in sub-folders "runs" the playbook

the program can be "cronifized" as it locks playbooks while filtering, so if it is launched while the previous process is still running, it will just continue to the next playbook

for each playbook, log and output are written in separates files (.log and .out), in the same directory
 
each .yml playbook is composed by components :
- one imap_client : with IMAP server and credentials
- filters
- clauses
- actions

**Filters**

- a filter **applies** an **ordered list of actions** on a list of messages matching with **ONE** of the clauses in his (ordered) clause list for messages in a list of folders
- if the clause list of a filter is empty, no messages will pass through it
- to perform actions to all messages in a folder, use the basic clause "All" which is provided by default
- if the list of folders is empty then **ALL FOLDERS** will be processed 


**Actions**

basic actions are : "Count", "Delete", "Print", "Trash", "Seen", "Unseen", "Flag", "Unflag", "TotalSize"

(they can be used even if not declared in the playbook because they dont need complement of definition like "destination" etc...)

DO NOT USE DELETE ACTION except if you have tested this program at least six month on your mailbox
USE TRASH ACTION if you want to safely delete your mails

non-basic actions are : "Url" (Alpha version), "Copy", "Move"

DO NOT USE COPY ACTION WITHOUT MOVE OR TRASH in recurrent filter usage, as it will generate duplicates in destination folder and full the box 

-**Url** calls an Url

-**Copy** copy the filtered message set to his **destination**
 
-**Move** copy the filtered message set to his **destination** and **delete** it

**Clauses**

Clause is a list of conditions, a clause is True when **ALL** conditions are True
available conditions are :         
        "to_domain", "to_full_domain", "to_name", "to_name_cs", "to",
        "from_domain", "from_full_domain", "from_name", "from_name_cs", "from",
        "subject_contains", "subject_starts",
        "subject_contains_cs", "subject_starts_cs",
        "age_day", "fresh_day",
        "size_ko", "size_mo",
        "seen", "flagged",
        "body_contains",
        "body_contains_cs",
        "All",

"cs" suffixes means case sensitive, other conditions are not
"All" condition is always true, it is used by the basic clause "All" which is provided by default. 
