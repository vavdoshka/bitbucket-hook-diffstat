# Bitbucket hook diffstat

## Overview

Bitbucket push webhook handler to generate a list of files changed on a push.

It processes branch updates/branch creates events and extracts the file paths of the files whose content was changed in that event, including the removal or creation of the file itself.
In the case of a branch update event, it gets the changeset between the current HEAD of the branch and the previous HEAD of that branch.
In case the branch is created, it gets the changeset between the current HEAD of the branch and the HEAD of the main branch of the repository.

It uses Bitbucket `diffstat`,  `repositories`, and `branches` APIs. It handles some basic retries on retyable HTTP response codes from BitBucket.
It aslo perform a basic validation by comparing the expected owner and repo details with the details recieved in the push event, but in addition one should take care of whitelisting Bitbucket public IPs on the server side to make that check efficient.
## Usage
```python
from bitbucket_hook_diffstat import process_bitbucket_push_events

result = process_bitbucket_push_events(
    push_payload, repo_owner, repo_name, bitbucket_user, bitbucket_password
) # it might raise an Exception, please check `bitbucket_hook_diffstat/exceptions.py`

result # Is a dict of a zero or more branch names - strings to the set of one or many file pathnames - strings.
{'master': {'.gitignore'}}
```

`push_payload` is a Bitbucket repository [push event](https://support.atlassian.com/bitbucket-cloud/docs/event-payloads/#Push)

`repo_owner` and `repo_name` one can retrieve from the repository URL `https://bitbucket.org/repo_owner/repo_name` 

`bitbucket_password` is an "app password" and `bitbucket_user` is available as "Username" in Bitbucket profile settings. This user should be authorized to do Repositories Read.
