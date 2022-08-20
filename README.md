# Bitbucket hook diffstat

## Overview

Bitbucket push webhook handler to generate a list of files changed on a push.

It processes branch updates, and the branch creates events and extracts the file paths of the files whose content was changed in that event, including the removal or creation of the file itself.
In the case of a branch update event, it gets the changeset between the current HEAD of the branch and the previous HEAD of that branch.
In case the branch is created, it gets the changeset between the current HEAD of the branch and the HEAD of the main branch of the repository.
It uses Bitbucket `diffstat`,  `repositories`, and `branches` APIs. It handles some basic retries on unexpected HTTP response codes from BitBucket.

## Usage
```python
from bitbucket_hook_diffstat import process_bitbucket_push_events

result, errors = process_bitbucket_push_events(
    push_payload, repo_owner, repo_name, bitbucket_user, bitbucket_password
)

result # Is a list of zero or more distinct file pathnames
errors # Is a list of text strings indicating the errors which occured during the process. This function does not raise any Exception.
# - zero or more of 
#   "Invalid push change payload"
#   "Unexpected response HTTP status"
#   "Can not process event because it's type is "unknown""
#   "Unhandled error"
```
Where `bitbucket_password` is an "app password" and `bitbucket_user` is available as "Username" in Bitbucket profile settings. This user should be authorized to do Repositories Read.

`push_payload` is a repository push event - https://support.atlassian.com/bitbucket-cloud/docs/event-payloads/#Push

`repo_owner` and `repo_name` one can retrieve from the repository URL https://bitbucket.org/`repo_owner`/`repo_name` 