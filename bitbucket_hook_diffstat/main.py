import http.client
from base64 import b64encode
import json

def get_changed_paths(connection, repo_owner, repo_name, from_commit, to_commit, headers):

    error = None
    changed_paths = set()
    url = f"/2.0/repositories/{repo_owner}/{repo_name}/diffstat/{to_commit}..{from_commit}"
    i = 0
    while True:
        i += 1
        connection.request("GET", url, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            error = 'Unexpected response HTTP status' \
                    f' {response.status} with reason "{response.reason}"' \
                    f' - a response on a GET request "https://{connection.host}{url}"' \
                    f' with headers "{list(headers.keys())}" (headers values are truncated).'
            return changed_paths, error

        json_data = json.loads(response.read().decode("utf-8"))
        with open(f"changed_paths-{i}.json", "w") as file:
                file.write(json.dumps(json_data))

        changed_paths.update(extract_changed_paths(json_data))
        if "next" not in json_data:
            break
        url = json_data["next"]


    return changed_paths, error

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



