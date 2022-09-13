
import base64
import json
import os.path

def get_docker_creds(registry_hostname):
    location = os.path.expanduser("~/.singularity/docker-config.json")
    with open(location, 'r') as fp:
        docker_config = json.load(fp)

    registry_auth = docker_config.get("auths", {}).get(registry_hostname)
    if not registry_auth:
        raise Exception(f"Cached docker configuration does not include credentials for {registry_hostname}")

    auth = registry_auth.get("auth")
    if not auth:
        raise Exception(f"Cached docker configuration has missing authentication information for {registry_hostname}")

    creds = base64.b64decode(auth).decode().split(":", 1)
    if len(creds) != 2:
        raise Exception(f"Cached docker configuration has malformed credentials for {registry_hostname}")

    return tuple(creds)
