
import re
import urllib.parse
import requests

default_page_size = 30

def chomp_params(link):
    grab_param = re.compile("\s*(\w+)=\"(\w*)\"\s*(.*)")
    params = {}
    while True:
        m = grab_param.match(link)
        if not m:
            break
        param, value, link = m.groups()
        params[param] = value
        if not link.startswith(";"):
            break
        link = link[1:]
    return params, link

def parse_url_header(link_url):
    grab_url = re.compile("\s*\<(.*?)\>;\s*(.*)")
    info = {}
    while True:
        m = grab_url.match(link_url)
        if not m:
            break
        url, link_url = m.groups()
        params, link_url = chomp_params(link_url)
        info[url] = params
        link_url = link_url.rstrip()
        if not link_url or link_url[0] != ',':
            break
        link_url = link_url[1:]
    return info

def get_next_link(base_url, headers):
    if 'link' not in headers:
        return
    link_info = parse_url_header(headers['link'])
    is_done = True
    for link, info in link_info.items():
        if info['rel'] == 'next':
            query_url = link
            if query_url.startswith('/'):
                query_url = urllib.parse.urljoin(base_url, query_url)
            return query_url

def list_all_projects(base_api_url, auth=None):
    query_url = urllib.parse.urljoin(base_api_url, f"/api/v2.0/projects?with_detail=false&page_size={default_page_size}")
    while True:
        resp = requests.get(query_url, headers = {'accept': 'application/json'}, auth=auth)
        if resp.status_code != 200:
            raise Exception(f"Failed to list all projects (status_code={resp.status_code}): {resp.text}")
        for project in resp.json():
            project_name = project.get('name')
            if project_name:
                yield project_name

        query_url = get_next_link(base_api_url, resp.headers)
        if not query_url:
            break

def list_all_repositories(base_api_url, project, auth=None):
    query_url = urllib.parse.urljoin(base_api_url, "/api/v2.0/projects")
    query_url = urllib.parse.urljoin(query_url + "/", project) + f"/repositories?page_size={default_page_size}"
    while True:
        resp = requests.get(query_url, headers = {'accept': 'application/json'}, auth=auth)
        if resp.status_code != 200:
            raise Exception(f"Failed to list all repositories for project {project} (status_code={resp.status_code}): {resp.text}")
        for repo in resp.json():
            repo_name = repo.get('name')
            if repo_name:
                yield repo_name

        query_url = get_next_link(base_api_url, resp.headers)
        if not query_url:
            break

def list_artifacts(base_api_url, repository, auth=None):
    project, repository = repository.split('/', 1)
    query_url = urllib.parse.urljoin(base_api_url, "/api/v2.0/projects/")
    query_url = urllib.parse.urljoin(query_url, project + "/repositories/")
    query_url = urllib.parse.urljoin(query_url, urllib.parse.quote(repository, safe='') + f"/artifacts?page_size={default_page_size}")
    while True:
        resp = requests.get(query_url, headers = {'accept': 'application/json'}, auth=auth)
        if resp.status_code != 200:
            raise Exception(f"Failed to list all artifacts for repository {project}/{repository} (status_code={resp.status_code}): {resp.text}")
        for artifact in resp.json():
            digest = artifact.get('digest')
            tags = set()
            tags_obj = artifact.get('tags')
            media_type = artifact.get('media_type')
            if not tags_obj:
                yield digest, set(), media_type
            else:
                for tag in artifact.get('tags', []):
                    tag_name = tag.get('name')
                    if tag_name:
                        tags.add(tag_name)
                yield digest, tags, media_type

        query_url = get_next_link(base_api_url, resp.headers)
        if not query_url:
            break

if __name__ == '__main__':
    import auth
    base_url = 'https://hub.opensciencegrid.org'
    creds = auth.get_docker_creds("hub.opensciencegrid.org")
    for project in list_all_projects(base_url, auth=creds):
        print(f"Project: {project}")
        for repository in list_all_repositories(base_url, project, auth=creds):
            print(f"\tRepo: {repository}")
            for digest, tags, media_type in list_artifacts(base_url, repository, auth=creds):
                print(f"\t\tDigest: {digest}, tags={list(tags)}")
