# Ansible role: gitea

This role installs
* [Gitea](https://gitea.io)
* [ACT runner](https://docs.gitea.com/usage/actions/act-runner) (*optional*) with *act_runner* running native on the host.
* [Drone](https://drone.io) (*optional*) with a drone-runner as docker containers.  It also installs the drone-runner-exec runner for jobs to be executed on the local gitea host outside of docker.

It is safe to run multiple times - it will not destroy or overwrite existing configurations.

## Installation directories

The `defaults/main.yml` file defines the variable `gitea_datasets` which define where gitea will store its data.  (datasets is used to encourage use of ZFS for storage).  By default the main dir is `/stuff/gitea`.  All file/dir references here are based on that

## Important files

_/drone/drone.env_
: Contains env variables to configure drone, drone-runner and drone-runner-exec.

_/drone/drone_cmdline.env_
: Contains the **DRONE_TOKEN** and **DRONE_SERVER** variables which hold the token and server location needed for the `drone` cmdline tool.

_/gitea/admin.tokens_
: Contains the **client_id** and **client_secret** variables drone needs for access to gitea

NOTE: drone pulls images defined in the .drone.yml with no authentication.  See [How to prevent DockerHub pull rate limit errors](https://discourse.drone.io/t/how-to-prevent-dockerhub-pull-rate-limit-errors/8324/1) for how to login

## Modifications to target system

The role will create a `git` user on the target system to enable git access via ssh, with the home directory for `git` set as `/stuff/gitea/git`.  For `git push` over ssh to work and reach into the Gitea docker container a bit of ssh port redirection is needed.  An ssh redirection shell script `/usr/local/bin/gitea` that contains

    #!/bin/sh
    ssh -p 2222 -o StrictHostKeyChecking=no git@127.0.0.1 "SSH_ORIGINAL_COMMAND=\"$SSH_ORIGINAL_COMMAND\" $0 $@"

Every user that adds an ssh key to their profile gets an entry in the `git` user `/stuff/gitea/git/.ssh/authorized_keys` that looks similar to this

    command="/usr/local/bin/gitea --config=/data/gitea/conf/app.ini serv key-1",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAwrspgQ2SqKe2EJEzv7O1G123fsut8mJxdJ3CSjOEBS9PnjHVUaugfV71xaDYspef7jQ7JzlDY.... rest of ssh pub key .....

This redirects incoming ssh sessions for the `git` user to `localhost:2222`.  The docker container for Gitea is listening on localhost:2222 and that's how the connection gets in.  See the **SSH Container Passthrough** section in the [Installation with Docker](https://docs.gitea.io/en-us/install-with-docker/) section of the Gitea docs.


## Role Variables

Available variables are listed below along with default values (see `defaults/main.yml`)

* `force_update: false`

    Whether or not to remove any config files before installing.  This ensures a clean install.  Currently the following files can be removed (based on _/stuff/gitea/_:

    _/drone/drone.env_
    _/act_runner-0.2.6-linux-amd64_ (allows re-download of runner binary)
    _/act_runner-0.2.6_config.yml_
    _/.runner_

    **TODO:** Better cleanup of config files - backup existing for example.

* `enable_drone: true`

    Whether or not to install drone and drone-runner containers for CI/CD

* `enable_act: true`

    Whether or not to install the Gitea ACT runner for CI/CD.  This is currently installed locally on the system and controlled via a systemd unit file.

    **TODO:** Move to a container for the act_runner like gitea, drone and drone-runner.

* `gitea_container_port: 3000`
`gitea_drone_port: 3001`
`gitea_dronerunner_port: 3002`

    Defines what port each container will listen on

* `gitea_drone_internal_port: 80`
`gitea_dronerunner_internal_port: 3000`

    These are the ports that drone and drone-runner listen on internally - ~~these vars are used by the molecule testing _molecule/default/tests/test_default.yml_ goss file to verify that the containers are running.~~  No longer using **goss** for verification tests - seems to be abandoned.  Now minimal testing via testinfra is in place.

* `username: "{{ vault_username | default(ansible_user_id) }}"`

    Used for file ownership and first admin user in Gitea (see `gitea_drone_admin` below)  Will be pulled from vault if available.

* `gitea_drone_admin: droneadmin`
`gitea_drone_pass: <some password>`

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

## Admin users

A regular user of Drone cannot enable privileged container settings *(repo -> Settings -> Project Settings -> **Trusted**)*.  In order to run privileged containers, a regular user (eg. *octocat*) must be updated to Admin.  Keep in mind that this user then has admin control over Drone ...

    source /stuff/gitea/drone/drone_cmdline.env
    drone user update octocat --admin


## Molecule testing

Pick the ubuntu version to test under (ubuntu2204, ubuntu2004).  Molecule can be run locally if installed, or via a toolset container.  The container method is slightly more complex (see cmdline below) but does not require anything on the local system other than docker.

Molecule is configured to use Podman for creating the container instances to install the *ansible-gitea* role into and run tests.  The *alpineset2* toolset container shown below is set up to handle that cleanly, and that's how the current CI/CD tests run, both for Drone and Gitea Actions.

*NOTE:* If you wish to use docker for testing, the environment variable DOCKER_HOST must set to the local `/var/run/docker.sock` - that way docker commands from inside the toolset container will use the host volume-mounted `/var/run/docker.sock` to access the current local host docker daemon.  Also, the _molecule/default/molecule.yml_ file needs modification to use docker.

    docker run --rm -it -e MOLECULE_DISTRO=ubuntu2204 -e DOCKER_HOST=unix:///var/run/docker.sock -v "$(pwd)":"${PWD}" -w "${PWD}" -v /var/run/docker.sock:/var/run/docker.sock quay.io/halfwalker/alpineset2 molecule test

The _molecule/default/prepare.yml_ will create a temp directory _molecule/default/molecule_test_  to act as a directory to store the usual gitea and drone data.  By default, running molecule as above will create a podman container named *instance-ubuntu2204* **inside** the *alpineset2* container to run the role against.  The role in turn creates the gitea/drone/drone-runner containers **inside** that *instance-ubuntu2204* container.  It's turtles/containers all the way down ...

### Local testing with ACT runner

Testing on a local machine the same way as the CI/CD tests can be done with the [Gitea ACT runner](https://docs.gitea.com/usage/actions/act-runner).  A sample run

```
act_runner-main-linux-amd64 exec push -W .github/workflows/cicd.yml -j Molecule
```

Note: This example is using the older `-main-` version as this still supports enabling *privileged* containers in the workflow file (**cicd.yml**) with

```
    container:
      image: docker.io/halfwalker/alpineset2
      options: --privileged
```

If using the newer `0.2.6` runner than you will need to generate a config and modify the **privileged** option to *true*, as well as modify the **container:** stanza in `cicd.yml`.  By default the `0.2.6` runner disables the ability to run privileged containers.

```
act_runner-0.2.6-linux-amd64 generate-config | sed 's/privileged: false/privileged: true' > act_config.yml

act_runner-0.2.6-linux-amd64 --config act_config.yml exec push -W .github/workflows/cicd.yml -j Molecule
```

`cicd.yml` changes

```
    container:
      image: docker.io/halfwalker/alpineset2
      privileged: true
```

This role installs the `0.2.6` runner and generates a modified config file in `/stuff/gitea/act_0.2.6_config.yml` as above.

## TODO

- Get proper multi-user Drone working.  See https://discourse.drone.io/t/drone-clis-token-option-does-not-work/6871
- github actions method to show email address (from https://discordapp.com/channels/322538954119184384/1069795723178160168/1168589987026055259)
    ```   
    on:
      push:
    
    jobs:
      comment:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/github-script@v6
            id: get-mail
            with:
              github-token: ${{secrets.GITHUB_TOKEN}}
              script: |
                return (await github.rest.users.getByUsername({
                  username: ${{ tojson(github.event.sender.login) }}
                })).data.email;
              result-encoding: string
          - name: Print Email
            run: |
              echo ${{ steps.get-mail.outputs.result }}
    ```

