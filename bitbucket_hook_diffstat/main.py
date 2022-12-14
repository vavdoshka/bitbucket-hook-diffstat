import http.client
from base64 import b64encode
import json
import os
from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import RetryError, HTTPError
from bitbucket_hook_diffstat.exceptions import (
    BitbucketMaxRetryError,
    PayloadBadFormatError,
    BitbucketHTTPError,
    GenericError,
    BitbucketHookDiffstatError,
)


class ChangeSetHash:
    def __init__(self, from_hash, to_hash, branch_name):
        self.from_hash = from_hash
        self.to_hash = to_hash
        self.branch_name = branch_name


def request_get(session, url):
    try:
        response = session.get(url)
        response.raise_for_status()
    except RetryError as e:
        raise BitbucketMaxRetryError(e)
    except HTTPError as e:
        raise BitbucketHTTPError(e)
    return response.json()


def get_repo_main_branch(session, repo_owner, repo_name):
    url = f"https://api.bitbucket.org/2.0/repositories/{repo_owner}/{repo_name}"
    return request_get(session, url)["mainbranch"]["name"]


def get_branch_from_to_commits(session, repo_owner, repo_name, branch_name):

    main_branch = get_repo_main_branch(session, repo_owner, repo_name)
    from_commit = get_branch_head_commit(session, repo_owner, repo_name, main_branch)
    to_commit = get_branch_head_commit(session, repo_owner, repo_name, branch_name)

    return (from_commit, to_commit)


def get_branch_head_commit(session, repo_owner, repo_name, branch_name):
    url = f"https://api.bitbucket.org/2.0/repositories/{repo_owner}/{repo_name}/refs/branches/{branch_name}"
    return request_get(session, url)["target"]["hash"]


def get_changed_paths(session, repo_owner, repo_name, from_commit, to_commit):

    changed_paths = set()
    url = f"https://api.bitbucket.org/2.0/repositories/{repo_owner}/{repo_name}/diffstat/{to_commit}..{from_commit}"
    while True:
        json_data = request_get(session, url)
        changed_paths.update(extract_changed_paths(json_data))
        if "next" not in json_data:
            break
        url = json_data["next"]

    return changed_paths


def extract_changed_paths(json_data):
    changed_paths = set()
    for item in json_data["values"]:
        # Diffstat object can have one of these statuses -
        # modified,removed,added,renamed. It is not complete list though, no docuemntation describes it.
        # just some examples - https://developer.atlassian.com/cloud/bitbucket/rest/api-group-commits/#api-repositories-workspace-repo-slug-diffstat-spec-get
        # In Diffstat one or both of ["old"] and ["new"] data can be defined. It contains path to changed file.
        # for example if file was added only then ["new"]["path"] is set to the file path and ["old"] is None
        # if file was removed only then ["old"]["path"] is set and ["new"] is None.
        # But because all what we need is a set of all changed paths independently of their status,
        # we need to check if ["old"] or ["new"] are defined and if they are, then add them to the set.

        if "old" in item and item["old"] is not None:
            changed_paths.add(item["old"]["path"])
        if "new" in item and item["new"] is not None:
            changed_paths.add(item["new"]["path"])
    return changed_paths


def detect_branch_change_event_type(push_change_payload):
    if push_change_payload["new"] is not None and push_change_payload["old"] is None:
        return "branch_created"
    elif push_change_payload["new"] is None and push_change_payload["old"] is not None:
        return "branch_removed"
    elif (
        push_change_payload["new"] is not None
        and push_change_payload["old"] is not None
    ):
        return "branch_updated"


def extract_branch_name(push_change_payload):
    event_type = detect_branch_change_event_type(push_change_payload)
    if event_type == "branch_created" or event_type == "branch_updated":
        return push_change_payload["new"]["name"]
    elif event_type == "branch_removed":
        return push_change_payload["old"]["name"]
    else:
        return "unknown"


def extract_from_to_commit_hashes(push_change_payload, session, repo_owner, repo_name):
    event_type = detect_branch_change_event_type(push_change_payload)
    if event_type == "branch_updated":
        return (
            push_change_payload["old"]["target"]["hash"],
            push_change_payload["new"]["target"]["hash"],
        )

    elif event_type == "branch_created":
        from_commit, to_commit = get_branch_from_to_commits(
            session, repo_owner, repo_name, push_change_payload["new"]["name"]
        )
        return from_commit, to_commit
    elif event_type == "branch_removed":
        # ignore branch remove events
        return None, None


def get_change_set_hashes(push_changes, session, repo_owner, repo_name):
    change_sets_hashes = []

    for push_change_payload in push_changes:

        if (
            "new" not in push_change_payload
            or "old" not in push_change_payload
            or (
                push_change_payload["new"] is None
                and push_change_payload["old"] is None
            )
        ):
            raise PayloadBadFormatError(
                'Push payload formated wrong. \'push/changes\' item should contain at least one of "new" and "old" change details.'
            )

        if (
            push_change_payload["new"] is not None
            and push_change_payload["new"]["type"] != "branch"
        ) or (
            push_change_payload["old"] is not None
            and push_change_payload["old"]["type"] != "branch"
        ):
            # tag creation or some other non branch change related event
            continue

        from_hash, to_hash = extract_from_to_commit_hashes(
            push_change_payload, session, repo_owner, repo_name
        )

        branch_name = extract_branch_name(push_change_payload)
        if from_hash is not None and to_hash is not None:
            change_sets_hashes.append(ChangeSetHash(from_hash, to_hash, branch_name))
    return change_sets_hashes


def get_changed_paths_per_event(change_sets_hashes, session, repo_owner, repo_name):
    changed_paths = defaultdict(set)
    for change_set_hash in change_sets_hashes:
        changed_path_set = get_changed_paths(
            session,
            repo_owner,
            repo_name,
            change_set_hash.from_hash,
            change_set_hash.to_hash,
        )
        if changed_path_set not in changed_paths[change_set_hash.branch_name]:
            changed_paths[change_set_hash.branch_name].update(changed_path_set)
    return changed_paths


def validate_webhook_origin(push_payload, repo_owner, repo_name):
    try:
        origin_repo = push_payload["repository"]["full_name"]
    except KeyError:
        raise PayloadBadFormatError(
            f"Could not validate payload origin, 'repository/full_name' is missing."
        )
    expected_repo = f"{repo_owner}/{repo_name}"
    if origin_repo != expected_repo:
        raise PayloadBadFormatError(
            f"Push payload origin repo is '{origin_repo}' while expected is {expected_repo}."
        )


def process_bitbucket_push_events(
    push_payload, repo_owner, repo_name, bitbucket_user, bitbucket_password
):

    validate_webhook_origin(push_payload, repo_owner, repo_name)

    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.auth = (bitbucket_user, bitbucket_password)

    changed_paths = defaultdict(set)
    push_changes = push_payload["push"]["changes"]

    try:
        change_sets_hashes = get_change_set_hashes(
            push_changes, session, repo_owner, repo_name
        )

        changed_paths = get_changed_paths_per_event(
            change_sets_hashes, session, repo_owner, repo_name
        )
    except BitbucketHookDiffstatError as e:
        raise e
    except Exception as e:
        raise GenericError(e)

    return dict(changed_paths)


if __name__ == "__main__":

    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            # don't want to retry
            self.send_response(200)
            self.wfile.write("POST request for {}".format(self.path).encode("utf-8"))

            content_length = int(
                self.headers["Content-Length"]
            )  # <--- Gets the size of data
            post_data = self.rfile.read(content_length)  # <--- Gets the data itself
            push_payload = json.loads(post_data.decode("utf-8"))

            print(
                process_bitbucket_push_events(
                    push_payload,
                    os.getenv("BITBUCKET_REPO_OWNER"),
                    os.getenv("BITBUCKET_REPO_NAME"),
                    os.getenv("BITBUCKET_USER"),
                    os.getenv("BITBUCKET_PASSWORD"),
                )
            )

    def run(server_class=HTTPServer, handler_class=Handler):
        server_address = ("", 8000)
        httpd = server_class(server_address, handler_class)
        httpd.serve_forever()

    print("starting http server")
    run()
