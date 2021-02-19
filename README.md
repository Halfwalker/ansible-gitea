# Ansible role: gitea

This role installs [Gitea](https://gitea.io) and optionally [Drone](https://drone.io) with a drone-runner as docker containers.

## Installation directories

The `defaults/main.yml` file defines the variable `gitea_datasets` which define where gitea will store its data.  (datasets is used to encourage use of ZFS for storage).  By default the main dir is `/stuff/gitea`.  All file/dir references here are based on that

## Important files

/drone/drone.env
: Contains env variable to configure drone and drone-runner.  Also include the **DRONE_TOKEN** variable which holds the token needed for the `drone` cmdline too.

/gitea/admin.tokens
: Contains the **client_id** and **client_secret** variables drone needs for access to gitea

## Role Variables

Available variables are listed below along with default values (see `defaults/main.yml`)

    force_update: false

Whether or not to remove any config files before installing.  This ensures a clean install.  Currently the following files can be removed:

_/drone/drone.env_

    enable_drone: true

Whether or not to install drone and drone-runner containers for CI/CD

    gitea_container_port: 3000
    gitea_drone_port: 3001
    gitea_dronerunner_port: 3002

Defines what port each container will listen on

    username: "{{ vault_username | default(ansible_user_id) }}"

Used for file ownership and first admin user in Gitea (see `gitea_drone_admin` below)

    gitea_drone_admin: droneadmin
    gitea_drone_pass: <some password>

When Gitea is installed a primary admin user is created with this name.  This is needed in order to generate the oauth2 `client_id` and `client_secret` variables that drone needs to access Gitea.

## Example playbook (gitea.yml)

    - hosts: all
      gather_facts: true
    
      roles:
        - { role: ansible-gitea, tags: 'gitea' }

It can be run with something like

    ansible-playbook -i hosts -l gitea.local gitea.yml -K --tags 'gitea'

## Usage

Assuming the target system name is `gitea.local` ...  Once installed, Gitea will be available at `http://gitea.local:3000`.  Registration is OPEN by default, so register a user (will be a regular user).  After logging into gitea, open another tab to Drone at `http://gitea.local:3001`.  You should be redirected to Gitea to authorize access for Drone.

For adminstration of Gitea use the `gitea_drone_admin` and `gitea_drone_pass` values above to log in.  For cmdline access to Drone use the following (remember, from data dir `/stuff/gitea/drone/drone.env`)

    source /stuff/gitea/drone/drone_cmdline.env
    drone info

