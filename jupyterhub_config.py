# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Configuration file for JupyterHub
import os
import sys

whitelist = set()
admin = set()

from dockerspawner import DockerSpawner
class MyDockerSpawner(DockerSpawner):
	adminList = admin
	def start(self):
		HOME = '/home/vibrent'
		self.volumes = {
			'jupyterhub-user-{username}': HOME + '/work',
			 os.environ['RELEASE_VOLUME_NAME'] : HOME + '/RELEASE'
		}
		if self.user.name in self.adminList:
			self.volumes[os.environ['SHARED_VOLUME_NAME']] =  HOME + '/shared'
			self.volumes[os.environ['UPLOAD_VOLUME_NAME']] =  HOME + '/UPLOAD'
		return super().start()

c = get_config()

# We rely on environment variables to configure JupyterHub so that we
# avoid having to rebuild the JupyterHub container every time we change a
# configuration parameter.

# Spawn single-user servers as Docker containers
#c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
c.JupyterHub.spawner_class = MyDockerSpawner
# Spawn containers from this image
c.DockerSpawner.container_image = os.environ['DOCKER_NOTEBOOK_IMAGE']
# JupyterHub requires a single-user instance of the Notebook server, so we
# default to using the `start-singleuser.sh` script included in the
# jupyter/docker-stacks *-notebook images as the Docker run command when
# spawning containers.  Optionally, you can override the Docker run command
# using the DOCKER_SPAWN_CMD environment variable.
spawn_cmd = os.environ.get('DOCKER_SPAWN_CMD', "start-singleuser.sh")
c.DockerSpawner.extra_create_kwargs.update({ 'command': spawn_cmd })
# Connect containers to this Docker network
network_name = os.environ['DOCKER_NETWORK_NAME']
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = network_name
# Pass the network name as argument to spawned containers
c.DockerSpawner.extra_host_config = { 'network_mode': network_name }
# Explicitly set notebook directory because we'll be mounting a host volume to
# it.  Most jupyter/docker-stacks *-notebook images run the Notebook server as
# user `vibrent`, and set the notebook directory to `/home/vibrent/work`.
# We follow the same convention.
notebook_dir = os.environ.get('DOCKER_PERSIST_DIR') or '/home/vibrent/work'
c.DockerSpawner.notebook_dir = notebook_dir

# volume_driver is no longer a keyword argument to create_container()
# c.DockerSpawner.extra_create_kwargs.update({ 'volume_driver': 'local' })
# Remove containers once they are stopped
c.DockerSpawner.remove_containers = True
# For debugging arguments passed to spawned containers
c.DockerSpawner.debug = True
c.DockerSpawner.hub_connect_ip = 'localhost'
# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = '0.0.0.0'
#c.JupyterHub.hub_port = 8000

c.JupyterHub.extra_log_file = '/var/log/jupyterhub.log'

# Authenticate users with PAM
#c.JupyterHub.authenticator_class = 'jupyterhub.auth.PAMAuthenticator'
c.JupyterHub.authenticator_class = 'ldapauthenticator.LDAPAuthenticator'
c.LDAPAuthenticator.server_address = 'ldap://SHRDSRVSADDS01.awsvibhealth.local'
c.LDAPAuthenticator.server_port = 389
#c.LDAPAuthenticator.valid_username_regex= '^.*$'
# active directory
c.LDAPAuthenticator.bind_dn_template = 'AWSVIBHEALTH\{username}'
c.LDAPAuthenticator.user_search_base = 'OU=Users,OU=Environment,DC=awsvibhealth,DC=local'
c.LDAPAuthenticator.user_attribute = 'sAMAccountName'
# IOPUB for image visualization
c.iopub_data_rate_limit = 1e6
c.rate_limit_window = 3

# Persist hub data on volume mounted inside container
data_dir = os.environ.get('DATA_VOLUME_CONTAINER', '/data')

c.JupyterHub.cookie_secret_file = os.path.join(data_dir,
    'jupyterhub_cookie_secret')

c.JupyterHub.db_url = 'postgresql://postgres:{password}@{host}/{db}'.format(
    host=os.environ['POSTGRES_HOST'],
    password=os.environ['POSTGRES_PASSWORD'],
    db=os.environ['POSTGRES_DB'],
    port=5433,
)

# shut down idle single-user notebook servers
# default time: 30mins=30*60=1800

hub_dir=os.environ['HUB_DIR']
c.JupyterHub.services = [
    {
        'name': 'cull-idle',
        'admin': True,
        'command': [sys.executable, hub_dir+'services/cull_idle_servers.py', '--timeout=1800'],
    }
]

# Whitlelist users and admins
c.Authenticator.whitelist = whitelist
c.Authenticator.admin_users = admin
c.JupyterHub.admin_access = True
pwd = os.path.dirname(__file__)
with open(os.path.join(pwd, 'userlist')) as f:
	for line in f:
		if not line:
			continue
		parts = line.split()
		if len(parts) >= 1:
			name = parts[0]
			whitelist.add(name)
			if len(parts) > 1 and parts[1] == 'admin':
				admin.add(name)
