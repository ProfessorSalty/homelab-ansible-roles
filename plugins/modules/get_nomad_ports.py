#!/usr/bin/python
from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.basic import AnsibleModule
import urllib.request
import urllib.error
import re
import json

# Copyright: (c) 2021, Greg Smith <me@gregsmith.nyc>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

__metaclass__ = type

DOCUMENTATION = r'''
---
module: get_nomad_ports

short_description: Get all ports assigned to a nomad service

version_added: "1.0.0"

description: Queries a consul agent for the reserved ports of a given job

options:
    nomad_token:
        description: A token with permissions namespace:read-job
        required: true
        type: str
    nomad_job_name:
        description: The name of the Nomad job to inspect
        required: true
        type: str
    nomad_host:
        description: The hostname or ipv4 address of the Nomad agent
        required: false
        default: localhost
        type: str
    nomad_port:
        description: The port number that the Nomad agent is listening on
        required: false
        default: 4646
        type: int
    tls:
        description: Switch whether tls is used
        required: false
        default: True
        type: bool

author:
    - Gregory Smith (@professorsalty)
'''

EXAMPLES = r'''
# Minimal
- name: Get ports for docs job
  professorsalty.homelab.get_nomad_ports:
    nomad_token: abcdef0123456789
    nomad_job: docs
    
'''

RETURN = r'''
ports:
    - name: http
      port: 9000
    - name: https
      port: 9001
'''


protocol_regex = re.compile('^http?://', re.I)


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        nomad_token=dict(type='str', required=True),
        nomad_job_name=dict(type='str', required=True),
        nomad_host=dict(type='str', required=False, default='localhost'),
        nomad_port=dict(type='int', required=False, default=4646),
        tls=dict(type='bool', required=False, default=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    if module.check_mode:
        module.exit_json()

    headers = {'X-Nomad-Token': module.params['nomad_token']}
    protocol = 'https' if module.params['tls'] else 'http'
    url = format_url(protocol, **module.params)
    req = urllib.request.Request(url=url, headers=headers, method='GET')
    try:
        res = urllib.request.urlopen(req)
        json_body = json.loads(res.read().decode('utf-8'))
        task_groups = json_body['config']['TaskGroups']
        ports = [{'name': port['Label'], 'port': port['Value']} for group in task_groups for networks in
                 group['Networks'] for port in networks['ReservedPorts']]
        return module.exit_json(changed=False, ports=ports)
    except urllib.error.URLError as e:
        return module.fail_json(msg=e.reason, error=e)


def format_url(protocol: str, nomad_hostname: str, nomad_port: int, nomad_job_name: str):
    def _format(formatted_hostname: str):
        endpoint = 'v1/job'
        return '{protocol}://{hostname}:{port}/{endpoint}/{jobname}'.format(protocol=protocol,
                                                                            hostname=formatted_hostname,
                                                                            port=nomad_port, endpoint=endpoint,
                                                                            jobname=nomad_job_name)

    match = protocol_regex.match(nomad_hostname)
    if match:
        start_idx = match.end()
        hostname = nomad_hostname[start_idx:]
        return _format(hostname)
    return _format(nomad_hostname)


def main():
    run_module()


if __name__ == '__main__':
    main()
