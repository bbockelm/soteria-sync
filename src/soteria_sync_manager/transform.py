
import os
import hashlib
import subprocess
import urllib.parse

def convert_digest_to_sif(docker_prefix, repository, artifact):

    source = f'{docker_prefix}/{repository}@{artifact}'

    dest_sif = f'{urllib.parse.quote(source, safe="")}.sif'

    try:
        result = subprocess.run(["singularity", "build", dest_sif, source], check=True)
    except:
        if os.path.exists(dest_sif):
            os.unlink(dest_sif)
        raise

    return dest_sif


def push_sif(source_file, oras_prefix, repository, tag=None):

    if not tag:
        sha = hashlib.sha256()
        with open(source_file, 'rb') as fp:
            read_buf = fp.read(64*1024)
            while read_buf:
                sha.update(read_buf)
                read_buf = fp.read(64*1024)
        digest = f'sha256:{sha.hexdigest()}'

        dest = f'{oras_prefix}/{repository}@{digest}'
    else:
        dest = f'{oras_prefix}/{repository}:{tag}'

    result = subprocess.run(["singularity", "push", source_file, dest], check=True)


def clean_cache():
    subprocess.run(["singularity", "cache", "clean", "-f"], check=True)

if __name__ == '__main__':
    output_file = convert_digest_to_sif("docker://hub.opensciencegrid.org", "brian_bockelman/htcondor-autoscale-manager",
                          "sha256:5e7ed9064fb51fdac3aaac008dd57a45c32e6e0bdeb938f1ddf5311b8e5e6bc6")
    try:
        push_sif(output_file, "oras://hub.opensciencegrid.org", "brian_bockelman/htcondor-autoscale-manager")
        push_sif(output_file, "oras://hub.opensciencegrid.org", "brian_bockelman/htcondor-autoscale-manager", "test-upload")
    finally:
        os.unlink(output_file)
