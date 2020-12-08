# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Red Hat, Inc.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
    tests.test_linchpin_wrapper_plugin

    Unit tests for testing teflo LinchpinWrapperProvisionerPlugin class.

    :copyright: (c) 2018 Red Hat, Inc.
    :license: GPLv3, see LICENSE for more details.
"""

import copy
import json
import pytest
import mock
import os
from teflo.resources import Asset
from teflo.utils.config import Config
from teflo.exceptions import TefloProvisionerError
from teflo_linchpin_plugin import LinchpinWrapperProvisionerPlugin
from teflo._compat import string_types
from linchpin import LinchpinAPI
from linchpin.exceptions import HookError

@pytest.fixture
def cbn_config():
    os.environ['TEFLO_SETTINGS'] = '../assets/teflo.cfg'
    cfg = Config()
    cfg.load()
    return cfg

def os_params():
    return dict(
        groups='client',
        provider=dict(
            name='openstack',
            credential='openstack',
            image='image',
            flavor='small',
            networks=['network'],
            keypair='key',
            floating_ip_pool='pool',
            tx_id=1,
            count=1
        )
    )


def beaker_params():
    return dict(
        groups='client',
        provider=dict(
            name='beaker',
            credential='beaker-creds',
            arch='x86_64',
            distro='RHEL-7.5',
            variant='Server',
            whiteboard='teflo beaker resource examples',
            tx_id=1
        )
    )


def libvirt_params():
    return dict(
        groups='client',
        resource_group_type='libvirt',
        resource_definitions=[dict(
            name='test-libvm',
            role='libvirt_node',
            vcpus=2,
            memory=1024,
            uri='qemu:///system',
            image_src='http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2',
            ssh_key='teflo',
            networks=[dict(name='test_libvirt_net')]
        )],
        tx_id=1,
    )


def aws_params():
    return dict(
        groups='client',
        resource_group_type='aws',
        resource_definitions=[dict(
            name='aws',
            role='aws_ec2',
            flavor='t2.nano',
            image='ami-0200c593f80612761',
            region='us-east-2',
        )],
        tx_id=1
    )


def ocp_params():
    return dict(
        groups='ocp-pod',
        resource_group_type='openshift',
        resource_definitions=[dict(
            role='openshift_inline',
            namespace='dummy',
            definition=dict(
                kind='Pod',
                apiVersion='v1',
                metadata=dict(name='test1'),
                spec=dict(containers=[dict(
                    name='hello-openshift',
                    image='openshift/hello-openshift'
                )])
            )
        )],
        tx_id=1
    )


def docker_params():
    return dict(
        groups='dock-container',
        resource_group_type='docker',
        resource_definitions=[dict(
            role='docker_container',
            image='custom_fedora29:python',
            command='sleep infinity',
            name='myfedora29',
            devices=["/dev/kvm:/dev/kvm"]
        )],
        tx_id=1
    )


def azure_params():
    return dict(
        groups='az',
        resource_group_type='azure',
        resource_definitions=[dict(
            role='azure_vm',
            vm_name='TestMultiVm',
            deepclean=True,
            resource_group='ccit'
        )],
        tx_id=1
    )


def pinfile_params():
    return dict(
        pinfile=dict(path='dummy/PinFile',
                     targets=['dummy-topo']),
        tx_id=1
    )

def topofile_params():
    return dict(
        topology='dummy/topologies/dummy.yml',
        tx_id=1
    )

def topo_and_layout_file_params():
    return dict(
        topology='dummy/topologies/dummy.yml',
        layout='dummy/layouts/layout.yml',
        tx_id=1
    )


def topo_and_layout_dict_params():
    return dict(
        topology='dummy/topologies/dummy.yml',
        layout=dict(
            inventory_layout=dict(
                vars=dict(hostname='__IP__'),
                hosts={
                    "example-node": dict(
                        count=3,
                        host_groups=['example']
                    ),
                    "test-node":dict(
                        count=1,
                        host_groups=['test']
                    )
                }
            )
        ),
        tx_id=1
    )


def pinfile_template_params():
    return dict(
        pinfile=dict(path='dummy/PinFile',
                     targets=['dummy-topo']),
        template_data=dict(
            vars=dict(instance_name='test-instance'),
            file='dummy/template_data.yml'
        ),
        tx_id=1
    )


@pytest.fixture(params=['os', 'aws', 'beaker', 'libvirt', 'ocp', 'docker', 'azure'])
def asset(request, cbn_config):
    return Asset(
        name='host01',
        provisioner='linchpin-wrapper',
        config=cbn_config,
        parameters=copy.deepcopy(eval('%s_params()' % request.param))
    )


@pytest.fixture(params=['pinfile', 'topofile', 'topo_and_layout_file', 'topo_and_layout_dict', 'pinfile_template'])
def asset_dummy(request, cbn_config):
    return Asset(
        name='host_dummy',
        provisioner='linchpin-wrapper',
        config=cbn_config,
        parameters=copy.deepcopy(eval('%s_params()' % request.param))
    )


@pytest.fixture
def linchpin_wrapper_plugin(asset):
    return LinchpinWrapperProvisionerPlugin(asset)


@pytest.fixture
def lp_dummy_plugin(asset_dummy):
    return LinchpinWrapperProvisionerPlugin(asset_dummy)


class TestLinchpinWrapperProvisionerPlugin(object):
    def do_action(*args, **kwargs):
        pinfile = args[1]
        if pinfile.get('teflo', False):
            resource = pinfile['teflo']['topology']['resource_groups'][0]
            cloud = resource['resource_group_type']
        else:
            cloud = 'dummy'
        if kwargs['action'] == 'up':
            if cloud == 'openstack':
                results = {"1":{}}
            if cloud == 'beaker':
                results = {"2":{}}
            if cloud == 'libvirt':
                results = {"3":{}}
            if cloud == 'aws':
                results = {"4":{}}
            if cloud == 'dummy':
                results = {"5":{}}
            if cloud == 'openshift':
                results = {"6":{}}
            if cloud == 'docker':
                results = {"7":{}}
            if cloud == 'azure':
                results = {"8":{}}
            if cloud == 'libvirt':
                results = {"8":{}}
            return 0, results
        elif kwargs['action'] == 'destroy':
            return 0, None

    def up_failed(self, *args, **kwargs):
        return (1, {})

    def get_run_data(*args, **kwargs):
        if args[1] == "1":
            cloud = 'openstack'
        if args[1] == "2":
            cloud = 'beaker'
        if args[1] == "3":
            cloud = 'libvirt'
        if args[1] == "4":
            cloud = 'aws'
        if args[1] == "5":
            cloud = 'dummy'
        if args[1] == "6":
            cloud = 'ocp'
        if args[1] == "7":
            cloud = 'docker'
        if args[1] == "8":
            cloud = 'azure'
        if args[1] == "9":
            cloud = 'libvirt'
        sample_file = '../assets/linchpin_%s_count_results.json' % cloud
        with open(sample_file) as sample:
            results = json.load(sample)
        return results

    def destroy_failed(self, *args, **kwargs):
        return (1, {})

    def post_hook_success(self, *args, **kwargs):
        return {}

    def post_hook_failed(self, *args, **kwargs):
        raise HookError('Failed to run hook')


    @staticmethod
    def test_linchpin_constructor(linchpin_wrapper_plugin):
        assert isinstance(linchpin_wrapper_plugin, LinchpinWrapperProvisionerPlugin)

    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', do_action)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(LinchpinAPI, 'run_hooks', post_hook_success)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_delete_and_post_hook_pass(linchpin_wrapper_plugin):
        linchpin_wrapper_plugin.delete()

    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', up_failed)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_failed_create(linchpin_wrapper_plugin):
        with pytest.raises(TefloProvisionerError):
            res = linchpin_wrapper_plugin.create()

    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', up_failed)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_dummy_failed_create(lp_dummy_plugin):
        with pytest.raises(TefloProvisionerError):
            res = lp_dummy_plugin.create()


    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', do_action)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(LinchpinAPI, 'run_hooks', post_hook_failed)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_create_and_hook_fail(linchpin_wrapper_plugin):
        with pytest.raises(HookError):
            res = linchpin_wrapper_plugin.create()

    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', destroy_failed)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_failed_os_destroy(linchpin_wrapper_plugin):
        with pytest.raises(TefloProvisionerError):
            linchpin_wrapper_plugin.delete()

    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', do_action)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(LinchpinAPI, 'run_hooks', post_hook_failed)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_delete_and_post_hook_failed(linchpin_wrapper_plugin):
        with pytest.raises(HookError):
            linchpin_wrapper_plugin.delete()

    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', do_action)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_wrapper_create(linchpin_wrapper_plugin):
        res = linchpin_wrapper_plugin.create()
        assert (isinstance(res[0]['ip'], string_types) or isinstance(res[0]['ip'],dict))


    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', do_action)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_dummy_create(lp_dummy_plugin):
        res = lp_dummy_plugin.create()
        assert (res[0]['tx_id'] == "5")

    @staticmethod
    @mock.patch.object(LinchpinAPI, 'do_action', up_failed)
    @mock.patch.object(LinchpinAPI, 'get_run_data', get_run_data)
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_failed_create(linchpin_wrapper_plugin):
        with pytest.raises(TefloProvisionerError):
            res = linchpin_wrapper_plugin.create()

    @staticmethod
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_validate(linchpin_wrapper_plugin):
        linchpin_wrapper_plugin.validate()

    @staticmethod
    @mock.patch.object(Asset, 'workspace', '../assets/lp_workspace')
    def test_linchpin_dummy_validate(lp_dummy_plugin):
        lp_dummy_plugin.validate()