# This suppresses about 80% of the deprecation warnings from python 3.7.
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import os
    import testinfra.utils.ansible_runner
    # EXAMPLE_1: make the linter fail by importing an unused module
    # Hint: From now on, try running molecule test --destroy never
    import pytest

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

# see https://github.com/ansible/molecule/issues/1873
# and the related #345 issue from 2018
# possible method ?  https://stackoverflow.com/questions/72055550/how-to-check-set-fact-in-molecule
@pytest.fixture()
def AnsibleVars(host):
    all_vars = host.ansible.get_variables()
    # defaults_files = "file=../../defaults/main.yml name=role_defaults"
    # all_vars.update(host.ansible(
    #     "include_vars",
    #     defaults_files)["ansible_facts"]["role_defaults"])
    return all_vars


#
# Test files owned by root
#
@pytest.mark.parametrize("name", [
    ("/etc/systemd/system/gitea.service"),
    ("/etc/systemd/system/drone.service"),
    ("/etc/systemd/system/drone-runner.service"),
    ("/etc/systemd/system/drone-runner-exec.service"),
    ("/etc/systemd/system/act_runner.service"),
])

def test_root_files(host, name, AnsibleVars):
    f = host.file(name)

    assert f.is_file
    assert f.user == 'root'
    assert f.group == 'root'



