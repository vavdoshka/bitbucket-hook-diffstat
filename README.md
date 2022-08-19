# Bitbucket hook diffstat

## Overview

This is a simple webhook handler for Bitbucket repository push events.

It processes branch update and branch create events and extracts the file paths which were changed in that event.
In case of branch update event get's the changset between current HEAD of the branch and the previous HEAD of that branch.
In case if branch is created it get's the changset between current HEAD of the branch and HEAD of main branch of the repository.

## Usage
Set following environment variables:
```
BITBUCKET_PROJECT_SLUG
BITBUCKET_REPO_SLUG
BITBUCKET_USER
BITBUCKET_PASSWORD
```
Where `BITBUCKET_PASSWORD` is an "app password" and `BITBUCKET_USER` is available as "Username" in Bitbucket profile settings.

Replace or enhance `class Handler` with your custom logic to trigger some custom CI pipelines for example.

Host it somewhere

Create the PUSH webhook trigger in your Bitbucket repository.