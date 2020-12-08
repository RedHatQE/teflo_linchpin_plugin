# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Red Hat, Inc.
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
    teflo_linchpin_plugin.provisioner_plugin.linchpin

    Integration module for Linchpin provisioner

    https://github.com/CentOS-PaaS-SIG/linchpin

    :copyright: (c) 2020 Red Hat, Inc.
    :license: GPLv3, see LICENSE for more details.
"""
import yaml
import sys
import errno
import os
import json
import stat
import copy
from os import path, environ, pardir, makedirs
from teflo._compat import ConfigParser

try:
    from linchpin import LinchpinAPI
    from linchpin.context import LinchpinContext
except ImportError:
    pass
from teflo.core import ProvisionerPlugin, Inventory
from teflo.exceptions import TefloProvisionerError
from teflo.helpers import schema_validator, gen_random_str
from .helpers import LinchpinPinfileBuilder, LinchpinResponseBuilder


class TefloContext(LinchpinContext):
    # Really only subclassing so we can utilize our logger
    # when linchpin api logs any activity

    def setup_logging(self):
        self.console = self.cbn_logger

    def add_logger(self, logger):
        self.cbn_logger = logger


class Logger(object):
    # redirect stdout (and thus print() function) to logfile *and* terminal
    # http://stackoverflow.com/a/616645
    def __init__(self, logger):
        self.stdout = sys.stdout
        self.logger = logger
        sys.stdout = self

    def __del__(self):
        # sys.stdout = self.stdout
        pass

    def write(self, message):
        self.logger.info(message)

    def flush(self):
        pass


class LinchpinWrapperProvisionerPlugin(ProvisionerPlugin):
    __plugin_name__ = 'linchpin-wrapper'

    __schema_file_path__ = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                        "files/schema.yml"))
    __schema_ext_path__ = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                       "files/lp_schema_extensions.py"))

    def __init__(self, profile):
        super(LinchpinWrapperProvisionerPlugin, self).__init__(profile)
        # creating logger for this plugin to get added to teflo's loggers
        self.create_logger(name='teflo_linchpin_plugin', data_folder=self.config.get('DATA_FOLDER'))

        self.linchpin_api = LinchpinAPI(self._init_context())
        # setup meta key which defines when hooks execute
        setattr(self.linchpin_api, '__meta__', 'TEFLO')
        self.linchpin_api.setup_rundb()
        # use the settings for the disable progress bar and multiprocessing
        self.linchpin_api.setup_pbar()
        self._create_inv = False

    def _init_context(self):
        context = TefloContext()
        context.add_logger(self.logger)
        # point linchpin workspace to teflo workspace
        context.set_cfg('lp', 'workspace', self.workspace)
        context.set_evar('workspace', self.workspace)
        context.workspace = self.workspace
        context.setup_logging()
        context.load_config(config_path=path.abspath(path.join(self.workspace, 'linchpin.conf')))
        context.load_global_evars()
        # point linchpin rundb to teflo .results dir
        results_dir = path.abspath(path.join(self.data_folder, pardir,
                                             '.results'))
        if path.exists(results_dir):
            lws_path = path.join(results_dir, 'linchpin')
        else:
            lws_path = path.join(self.data_folder, 'linchpin')
        full_rundb_path = path.join(lws_path, 'rundb-::mac::.json')
        context.set_cfg('lp', 'rundb_conn', full_rundb_path)
        context.set_evar('rundb_conn', full_rundb_path)
        # point linchpin inventory directory to the teflo inventory dirs
        inv_dir = self.config.get('INVENTORY_FOLDER', None)
        if not inv_dir:
            inv_dir = path.join(results_dir, 'inventory')
        context.set_evar('inventory_path', path.join(inv_dir, 'master-' + path.basename(self.data_folder)))
        context.set_evar('default_inventories_path', inv_dir)
        context.set_evar('inventories_folder', 'inventory')
        # setup other settings for teflo
        context.set_cfg('lp', 'distill_data', True)
        context.set_evar('generate_resources', False)
        context.set_evar('debug_mode', True)
        # Settings to disable progress bar and multiprocessing which were hanging teflo process
        context.set_evar('no_monitor', True)
        context.no_monitor = True
        # setup the default_ssh_key_location to be the scenario workspace for libvirt and aws
        context.set_evar('default_ssh_key_path', os.path.join(
            os.path.abspath(self.workspace), 'keys'))

        if os.environ.get('CREDS_PATH', False):
            context.set_evar('default_credentials_path', os.environ.get('CREDS_PATH'))
        # set verbose
        if self.config.get('LOG_LEVEL', 'info') == 'debug':
            context.verbosity = 4
        else:
            context.verbosity = 1

        return (context)

    def _load_credentials(self):

        if self.provider_credentials and [i for i in self.get_schema_keys()
                                          if hasattr(self.asset, i) and i in ['pinfile', 'topology']]:
            self.logger.error('Trying to use Teflo credentials mapping with Linchpin pinfile/topology file.')
            raise TefloProvisionerError('Incompatible credential mechanism.')

        if self.provider_credentials and \
                'resource_group_type' in self.provider_params and not \
                [i for i in self.get_schema_keys() if hasattr(self.asset, i) and i in ['pinfile', 'topology']] or \
                hasattr(self.asset, 'provider'):
            if self.provider_params.get('resource_group_type', False) == 'openstack' or \
                    self.provider_params.get('name') == 'openstack':
                # Linchpin supports Openstack environment variables
                # https://linchpin.readthedocs.io/en/latest/openstack.html#credentials-management
                # It is better to keep the credentials in memory
                # This is also reduce complexity by not calling openstack directly
                environ['OS_USERNAME'] = self.provider_credentials['username']
                environ['OS_PASSWORD'] = self.provider_credentials['password']
                environ['OS_AUTH_URL'] = self.provider_credentials['auth_url']
                environ['OS_PROJECT_NAME'] = self.provider_credentials['tenant_name']
                if 'domain_name' in self.provider_credentials:
                    environ['OS_DOMAIN_NAME'] = self.provider_credentials['domain_name']
            elif self.provider_params.get('resource_group_type', False) == 'beaker' or \
                    self.provider_params.get('name') == 'beaker':
                bkr_conf = path.join(path.abspath(self.data_folder), 'beaker.conf')
                environ['BEAKER_CONF'] = bkr_conf
                creds = self.provider_credentials
                with open(bkr_conf, 'w') as conf:
                    if 'hub_url' in self.provider_credentials:
                        conf.write('HUB_URL = "%s"\n' % creds['hub_url'])
                    if 'ca_cert' in self.provider_credentials:
                        conf.write('CA_CERT = "%s"\n' % creds['ca_cert'])
                    if 'password' in self.provider_credentials:
                        conf.write('AUTH_METHOD = "password"\n')
                        conf.write('USERNAME = "%s"\n' % creds['username'])
                        conf.write('PASSWORD = "%s"\n' % creds['password'])
                    elif 'keytab' in self.provider_credentials:
                        conf.write('AUTH_METHOD = "krbv"\n')
                        conf.write('KRB_PRINCIPAL = "%s"\n' % creds['keytab_principal'])
                        conf.write('KRB_KEYTAB = "%s"\n' % creds['keytab'])
                        if 'realm' in self.provider_credentials:
                            conf.write('KRB_REALM = "%s"\n' % creds['realm'])
                        if 'service' in self.provider_credentials:
                            conf.write('KRB_SERVICE = "%s"\n' % creds['service'])
                        if 'ccache' in self.provider_credentials:
                            conf.write('KRB_CCACHE = "%s"\n' % creds['ccache'])
            elif self.provider_params.get('resource_group_type', False) == 'libvirt':
                creds = self.provider_credentials
                if not path.exists(path.expanduser('~/.config/libvirt')):
                    os.makedirs(path.expanduser('~/.config/libvirt'))
                libvirt_auth = path.join(path.expanduser('~/.config/libvirt'), 'auth.conf')
                environ['LIBVIRT_AUTH_FILE'] = libvirt_auth
                if path.exists(libvirt_auth):
                    os.remove(libvirt_auth)
                config = ConfigParser()
                config.add_section('credentials-teflo')
                config.set('credentials-teflo', 'username', creds['username'])
                config.set('credentials-teflo', 'password', creds['password'])
                with open(libvirt_auth, 'w') as cfg:
                    config.write(cfg)
            elif self.provider_params.get('resource_group_type', False) == 'aws':
                creds = self.provider_credentials
                if not path.exists(path.expanduser('~/.aws/')):
                    os.makedirs(path.expanduser('~/.aws/'))
                aws_auth = path.join(path.expanduser('~/.aws/'), 'credentials')
                environ['AWS_PROFILE'] = 'Credentials'
                if path.exists(aws_auth):
                    os.remove(aws_auth)
                config = ConfigParser()
                config.add_section('Credentials')
                for k, v in creds.items():
                    config.set('Credentials', k, v)
                with open(aws_auth, 'w') as cfg:
                    config.write(cfg)
            elif self.provider_params.get('resource_group_type', False) == 'gcloud':
                if not self.provider_credentials.get('service_account_email', False) or \
                        not self.provider_credentials.get('credentials_file', False) or \
                        not self.provider_credentials.get('project_id', False):
                    self.logger.error('Missing one or more Gcloud credential parameters.')
                    raise TefloProvisionerError('Missing required credential parameters')
                environ['GCE_EMAIL'] = self.provider_credentials['service_account_email']
                environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.provider_credentials['credentials_file']
                environ['GOOGLE_CLOUD_PROJECT'] = self.provider_credentials['project_id']
            elif self.provider_params.get('resource_group_type', False) == 'azure':
                if not self.provider_credentials.get('subscription_id', False) or \
                        not self.provider_credentials.get('tenant', False):
                    self.logger.error('Missing one or more Azure credential parameter - subscription_id, tenant')
                    raise TefloProvisionerError('Missing required credential parameters')
                if self.provider_credentials.get('client_id', False) and \
                        self.provider_credentials.get('ad_user', False):
                    self.logger.error('Found both client_id and ad_user')
                    raise TefloProvisionerError('Found conflicting credential parameters.')
                if self.provider_credentials.get('secret', False) and \
                        self.provider_credentials.get('ad_password', False):
                    self.logger.error('Found both secret and ad_password')
                    raise TefloProvisionerError('Found conflicting credential parameters.')
                if self.provider_credentials.get('subscription_id', False):
                    environ['AZURE_SUBSCRIPTION_ID'] = self.provider_credentials['subscription_id']
                if self.provider_credentials.get('subscription_id', False):
                    environ['AZURE_TENANT'] = self.provider_credentials['tenant']
                if self.provider_credentials.get('client_id', False):
                    environ['AZURE_CLIENT_ID'] = self.provider_credentials['client_id']
                if self.provider_credentials.get('secret', False):
                    environ['AZURE_SECRET'] = self.provider_credentials['secret']
                if self.provider_credentials.get('ad_user', False):
                    environ['AZURE_AD_USER'] = self.provider_credentials['ad_user']
                if self.provider_credentials.get('password', False):
                    environ['AZURE_PASSWORD'] = self.provider_credentials['password']
            elif self.provider_params.get('resource_group_type', False) == 'vmware':
                if not self.provider_credentials.get('hostname', False) or \
                        not self.provider_credentials.get('username', False) or \
                        not self.provider_credentials.get('password', False):
                    self.logger.error('Missing one or more VMware credential parameter - hostname, username, password')
                    raise TefloProvisionerError('Missing required credential parameters')
                environ['VMWARE_HOST'] = self.provider_credentials['hostname']
                environ['VMWARE_USER'] = self.provider_credentials['username']
                environ['VMWARE_PASSWORD'] = self.provider_credentials['password']
                if self.provider_credentials.get('port', False):
                    environ['VMWARE_PORT'] = self.provider_credentials['port']
                if self.provider_credentials.get('validate_certs', False):
                    environ['VMWARE_VALIDATE_CERTS'] = self.provider_credentials['validate_certs']
            elif self.provider_params.get('resource_group_type', False) == 'ovirt':
                if not self.provider_credentials.get('ovirt_url', False) or \
                        not self.provider_credentials.get('ovirt_username', False) or \
                        not self.provider_credentials.get('ovirt_password', False):
                    self.logger.error('Missing one or more oVirt credential parameter - ovirt_url, '
                                      'ovirt_username, ovirt_password')
                    raise TefloProvisionerError('Missing required credential parameters')
                environ['OVIRT_URL'] = self.provider_credentials['ovirt_url']
                environ['OVIRT_USERNAME'] = self.provider_credentials['ovirt_username']
                environ['OVIRT_PASSWORD'] = self.provider_credentials['ovirt_password']
                if self.provider_credentials.get('ovirt_ca_file', False):
                    environ['OVIRT_CA_FILE'] = self.provider_credentials['ovirt_ca_file']
            elif self.provider_params.get('resource_group_type', False) == 'openshift':
                if not self.provider_credentials.get('api_url', False):
                    self.logger.error('Missing one or more OpenShift credential parameter - api_url')
                    raise TefloProvisionerError('Missing required credential parameters')
                environ['K8S_AUTH_HOST'] = self.provider_credentials['api_url']
                if self.provider_credentials.get('api_token', False):
                    environ['K8S_AUTH_API_KEY'] = self.provider_credentials['api_token']
                if self.provider_credentials.get('kubeconfig', False):
                    environ['K8S_AUTH_KUB_CONFIG'] = self.provider_credentials['kubeconfig']
                if self.provider_credentials.get('context', False):
                    environ['K8S_AUTH_CONTEXT'] = self.provider_credentials['context']
                if self.provider_credentials.get('cert_file', False):
                    environ['K8S_AUTH_CERT_FILE'] = self.provider_credentials['cert_file']
                if self.provider_credentials.get('key_file', False):
                    environ['K8S_AUTH_KEY_FILE'] = self.provider_credentials['key_file']
                if self.provider_credentials.get('ssl_ca_cert', False):
                    environ['K8S_AUTH_SSL_CA_CERT'] = self.provider_credentials['ssl_ca_cert']
                if self.provider_credentials.get('verify_ssl', False):
                    environ['K8S_AUTH_VERIFY_SSL'] = self.provider_credentials['verify_ssl']
                if self.provider_credentials.get('username', False):
                    environ['K8S_AUTH_USERNAME'] = self.provider_credentials['username']
                if self.provider_credentials.get('password', False):
                    environ['K8S_AUTH_PASSWORD'] = self.provider_credentials['password']

        else:
            self.logger.warning('No teflo credential is being used. Assuming using provisioner specific method. ')

    def _create_pinfile(self):

        tpath = path.abspath(path.join(path.dirname(__file__), "files/PinFile.yml"))
        with open(tpath, 'r') as template:
            pindict = yaml.safe_load(template)

        """
        Need to deep copy the pinfile dict because once you get
        the results back from LinchpinAPI for some reason the layout
        data in global memory gets modified.
        i.e. layout when pinfile is loaded and supported by the API
        layout:
          inventory_layout:
            hosts:
              example-node:
                count: 1
                host_groups:
                  - example
        i.e. layout when the API returns the results of the up action
        layout:
          inventory_layout:
            hosts:
            - count: 1
              name: example-node
              host_groups:
              - example
        """
        pindict = copy.deepcopy(LinchpinPinfileBuilder.build_lp_pinfile(self.asset, pindict))

        self.logger.debug('Generated PinFile:\n%s' % yaml.dump(pindict))
        self.pinfile = pindict

    def _create_inventory(self, results):
        cfg_data = {}
        for target in results:
            if results.get(target).get('cfgs', False):
                cfg_data = results[target]['cfgs']['user']
            if results.get(target).get('inputs').get('layout_data', False):

                inv = self.linchpin_api.generate_inventory(
                    resource_data=results[target]['outputs']['resources'],
                    layout=results[target]['inputs']['layout_data']['inventory_layout'],
                    topology_data=results[target]['inputs']['topology_data'],
                    config_data=cfg_data
                )
                inv_path = results[target]['outputs']['inventory_path'][-1]
                inv_obj = Inventory.get_instance(config=self.config, uid=gen_random_str(10), inv_dump=inv)
                inv_obj.create_master(all_hosts=[])
                self._create_inv = True

    def _create(self):
        host = getattr(self.asset, 'name')
        code, results = self._lp_action()
        if code:
            raise TefloProvisionerError("Failed to provision asset %s" % host)
        try:
            if self.provider_params.get('count', 1) > 1:
                self.logger.info('Successfully created %s host resources'
                                 % self.provider_params.get('count'))
            else:
                self.logger.info('Successfully created asset %s' % host)
        except KeyError:
            self.logger.info('Successfully created asset %s' % host)
        tx_id = list(results)[0]
        results = self.linchpin_api.get_run_data(
            tx_id, ('cfgs', 'inputs', 'outputs'))
        self.logger.debug(json.dumps(results, indent=2))

        self._create_inventory(results)
        # Run post hooks once the inventory has been generated
        self.linchpin_api.run_hooks('post', 'up')
        resources = [res for target in results for res in results.get(target).get('outputs').get('resources')]

        if self._create_inv:
            return LinchpinResponseBuilder.generate_teflo_response(tx_id=tx_id,
                                                                    lp_res_resource=[],
                                                                    asset=self.asset)
        else:
            return LinchpinResponseBuilder.generate_teflo_response(tx_id=tx_id,
                                                                    lp_res_resource=resources,
                                                                    asset=self.asset)

    def create(self):
        """Create method. (must implement!)

        Provision the host supplied.
        """
        host = getattr(self.asset, 'name')
        self.logger.info('Provisioning Asset %s.' % host)
        self._create_pinfile()
        self._load_credentials()
        res = self._create()
        self.logger.info('Provisioning Asset %s is complete.' % host)
        return res

    def delete(self):
        """Delete method. (must implement!)

        Teardown the host supplied.
        """
        host = getattr(self.asset, 'name')
        self._create_pinfile()
        self._load_credentials()
        try:
            txid = self.provider_params.get('tx_id')
        except KeyError:
            txid = None
            self.logger.warning('No tx_id found for Asset: %s, this could mean it was not successfully'
                                ' provisioned. Attempting to perform the destroy without a tx_id'
                                ' but this might not work, so you may need to manually cleanup resources.' % host)
        self.logger.info('Delete Asset %s.' % host)
        rc, results = self._lp_action(txid=txid)
        if rc > 0:
            raise TefloProvisionerError('Failed to destroy the asset %s with return code %s.'
                                         ' Refer to the Linchpin stdout for more information.' % (host, rc))

        # Run post hooks if any
        self.linchpin_api.run_hooks('post', 'destroy')
        self.logger.info('Linchpin successfully deleted asset %s.' % host)

    def _lp_action(self, **kwargs):
        """
        wrapper function for calling the linchpin api
        to do up or destroy. We only supply txid when
        teflo is trying to destroy resources. So assume
        when no txid is provided that we are being asked
        to create resources.
        """
        results = None

        Log = Logger(logger=self.logger)
        if 'txid' in kwargs:
            results = self.linchpin_api.do_action(self.pinfile, action='destroy', tx_id=kwargs.get('txid'))
        elif 'validate' in kwargs:
            results = self.linchpin_api.do_validation(self.pinfile)
        else:
            results = self.linchpin_api.do_action(self.pinfile, action='up')
        del Log

        return results

    def authenticate(self):
        raise NotImplementedError

    def validate(self):

        # validate teflo plugin schema first
        schema_validator(schema_data=self.build_profile(self.asset),
                         schema_files=[self.__schema_file_path__],
                         schema_ext_files=[self.__schema_ext_path__])

        # validate linchpin pinfile
        self._create_pinfile()
        code, results = self._lp_action(validate=True)
        self.logger.info(code)
        self.logger.info(results)
        if code != 0:
            self.logger.error('linchpin topology rc: %s' % code)
            self.logger.error(results)
            raise TefloProvisionerError('Linchpin failed to validate pinfile.')
