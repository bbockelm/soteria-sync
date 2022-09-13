
import os
import collections

import soteria_sync_manager.harbor_utils as harbor_utils
import soteria_sync_manager.transform as transform

def convert_repository_to_singularity(harbor_hostname, repository, auth=None):
    print(f"Scanning repository docker://{harbor_hostname}/{repository} for missing Singularity images...")
    base_api_url = f'https://{harbor_hostname}'
    digest_info = {}
    tag_info = {}
    media_info = {}
    media_digest_info = {}  # Maps digest to media type
    for digest, tags, media_type in harbor_utils.list_artifacts(base_api_url, repository, auth=auth):
        digest_info[digest] = tags
        media_digest_info[digest] = media_type
        for tag in tags:
            media_info[tag] = media_type
            tag_info[tag] = digest

    missing_singularity_tags = set()
    missing_singularity_digests = collections.defaultdict(set)
    missing_singularity_artifacts = set()

    for tag in tag_info:
        if not tag.endswith('-singularity') and media_info.get(tag) in ['application/vnd.docker.container.image.v1+json', 'application/vnd.oci.image.config.v1+json']:
            sing_tag = f'{tag}-singularity'
            if sing_tag not in tag_info:
                print(f"Singularity version of tag {tag} is missing from repository {repository}")
                missing_singularity_tags.add(tag)
                missing_singularity_digests[tag_info[tag]].add(tag)
            else: # Check for mutated tags.
                needs_update = False
                sing_digest = tag_info.get(sing_tag)
                if not sing_digest:
                    orig_tags = None
                else:
                    orig_tags = [tag for tag in digest_info[sing_digest] if tag.startswith("sha256-")]
                if not orig_tags:
                    needs_update = True
                else:
                    orig_digest_parts = orig_tags[0].split("-")
                    if len(orig_digest_parts) != 3 or orig_digest_parts[2] != "singularity":
                        needs_update = True
                    else:
                        orig_digest = f'{orig_digest_parts[0]}:{orig_digest_parts[1]}'
                        needs_update = tag_info[tag] != orig_digest
                if needs_update:
                    print(f"Tag {tag} has mutated and is in need of update")
                    missing_singularity_tags.add(tag)
                    missing_singularity_artifacts.add(tag_info[tag])
                    missing_singularity_digests[tag_info[tag]].add(tag)

    for digest in digest_info:
        sing_digest = f'{digest.replace(":", "-")}-singularity'
        if sing_digest not in tag_info and media_digest_info.get(digest) in ['application/vnd.docker.container.image.v1+json', 'application/vnd.oci.image.config.v1+json']:
            print(f"Singularity version of digest {digest} is missing from repository {repository}")
            missing_singularity_artifacts.add(digest)

    docker_prefix = f'docker://{harbor_hostname}'
    oras_prefix = f'oras://{harbor_hostname}'
    results = collections.defaultdict(set)
    for digest in missing_singularity_artifacts:
        dest_tag = f'{digest.replace(":", "-")}-singularity'
        print(f"Creating Singularity version of artifact {digest}...")
       
        try: 
            dest_sif = transform.convert_digest_to_sif(docker_prefix, repository, digest)
        except:
            results['failed_artifacts'].add(f'{repository}@{digest}')
            continue
        try:
            print(f"Pushing Singularity version of artifact {digest}...")
            transform.push_sif(dest_sif, oras_prefix, repository)
            print(f"Pushing Singularity version of artifact {digest} as tag {dest_tag}...")
            transform.push_sif(dest_sif, oras_prefix, repository, tag=dest_tag)
            for tag in missing_singularity_digests[digest]:
                dest_tag = f'{tag}-singularity'
                print(f"Pushing Singularity version of artifact {digest} as tag {dest_tag}...")
                transform.push_sif(dest_sif, oras_prefix, repository, tag=dest_tag)
        except:
            results['failed_artifacts'].add(f'{repository}@{digest}')
            continue
        finally:
            os.unlink(dest_sif)
        results['successful_artifacts'].add(f'{repository}@{digest}')
    print(f"Finished scanning repository docker://{harbor_hostname}/{repository} for missing Singularity images...")
    return results


def convert_project_to_singularity(harbor_hostname, project, repository_filter=None, auth=None):
    base_api_url = f'https://{harbor_hostname}'
    results = collections.defaultdict(set)
    for repo in harbor_utils.list_all_repositories(base_api_url, project, auth=auth):
        if repository_filter:
            if not repository_filter.search(repo):
                continue
        repo_results = convert_repository_to_singularity(harbor_hostname, repo, auth=auth)
        for key, val in repo_results.items():
            results[key].update(val)
    return results


if __name__ == '__main__':
    import re
    import auth
    harbor_hostname = "hub.opensciencegrid.org"
    creds = auth.get_docker_creds(harbor_hostname)
    results = convert_repository_to_singularity(harbor_hostname, 'brian_bockelman/htcondor-autoscale-manager', auth=creds)
    print(results)
    results = convert_project_to_singularity(harbor_hostname, 'brian_bockelman', repository_filter=re.compile('open-science-pool-registry|htcondor-autoscale-manager|centos'), auth=creds)
    print(results)
    transform.clean_cache()
