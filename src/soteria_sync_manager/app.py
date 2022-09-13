
import collections
import os
import re

from flask import Flask
from flask_apscheduler import APScheduler

import soteria_sync_manager.auth as auth
import soteria_sync_manager.harbor_utils as harbor_utils
import soteria_sync_manager.transform as transform

app = Flask(__name__)

app.config['HARBOR_HOSTNAME'] = 'hub.opensciencegrid.org'

for key, val in os.environ.items():
    if key.startswith("FLASK_"):
        app.config[key[6:]] = val

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

last_spider_results = {}

@scheduler.task("interval", id="singularity_update", seconds=10)
def spider_harbor_projects():

    harbor = app.config['HARBOR_HOSTNAME']
    base_api = f'https://{harbor}'
    project_filter = re.compile(app.config.get("PROJECT_FILTER", ".*"))
    repo_filter = re.compile(app.config.get("REPOSITORY_FILTER", ".*"))

    harbor_auth = auth.get_docker_creds(harbor)

    project_results = collections.defaultdict(set)
    for project in harboor_utils.list_all_projects(base_api, auth=harbor_auth):
        if not project_filter.search(project):
            continue
        results = spider.convert_project_to_singularity(harbor_hostname, project, repository_filter=repo_filter, auth=harbor_auth)
        for key, val in results.items():
            project_results[key].update(val)

    global last_spider_results
    last_spider_results = project_results

    transform.clean_cache()

@app.route("/metrics")
def metrics():
    return f"failed_artifacts {last_spider_results.get('failed_artifacts', 0)}\nsuccessful_artifacts {last_spider_results.get('successful_artifacts', 0)}"

def entry():
    app.run()

if __name__ == '__main__':
    entry()
