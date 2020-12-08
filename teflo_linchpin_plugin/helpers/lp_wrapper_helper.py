
import os
import yaml
import stat
import json
import copy
from teflo.exceptions import HelpersError, TefloProvisionerError
from teflo.helpers import ssh_key_file_generator, template_render, get_provider_plugin_class, \
    lookup_ip_of_hostname, file_mgmt
from teflo._compat import string_types
from logging import getLogger

LOG = getLogger(__name__)


class LinchpinPinfileBuilder(object):

    """
    LinchpinResourceBuilder Class used by the Linchpin
    provisioner plugin to be able to take the dictionary
    parameters in a Teflo Provider and build a proper
    Linchpin resource definition dictionary that can be used
    to build the resource group

    """

    _bkr_op_list = ['like', '==', '!=', '<=', '>=', '=', '<', '>']
    _pinfile_keys = ['pinfile', 'topology', 'hooks', 'layout']

    @classmethod
    def build_lp_pinfile(cls, asset, pindict):

        """
        main public method for Linchpin provisioner to interact with.

        :param pindict: Template Pinfile dictionary
        :type Object: dict
        :param asset: the Asset Resource
        :type Object: object
        :return: a Linchpin PinFile dictionary
        """

        if not getattr(asset, 'provider', False):
            return cls._build_resource_group_from_asset(asset, pindict)

        if getattr(asset, 'provider', False) == 'beaker':
            return cls._build_beaker_resource_group(asset, pindict)
        elif getattr(asset, 'provider', False) == 'openstack':
            return cls._build_openstack_resource_group(asset, pindict)
        elif getattr(asset, 'provider', False) == 'libvirt':
            return cls._build_libvirt_resource_group(asset, pindict)
        elif getattr(asset, 'provider', False) == 'aws':
            return cls._build_aws_resource_group(asset, pindict)

    @classmethod
    def _build_pinfile(cls, asset_name, workspace, resource_grp, pindict):

        # check for template data
        temp_data = {}
        temp_data.update(os.environ)
        if 'template_data' in resource_grp and resource_grp.get('template_data', False):
            td = resource_grp.pop('template_data')
            if 'file' in td:
                temp_data.update(file_mgmt('r',
                                           os.path.abspath(os.path.join(workspace, td.get('file')
                                                                        )
                                                           )
                                           )
                                 )
            if 'vars' in td:
                temp_data.update(td.get('vars'))

        if 'pinfile' in resource_grp and resource_grp.get('pinfile', False):
            topo_path = os.path.abspath(os.path.join(workspace,
                                                     resource_grp.get('pinfile').get('path')))
            targets = resource_grp.get('pinfile').get('targets', [])
            pindata = yaml.safe_load(template_render(topo_path, temp_data))
            for target in pindata:
                if isinstance(pindata.get(target).get('topology'), string_types):
                    tp = os.path.abspath(os.path.join(workspace, os.path.dirname(topo_path)))
                    tp = os.path.join(tp, os.path.join('topologies', pindata.get(target).get('topology')))
                    # apply template_data
                    tpd = yaml.safe_load(template_render(tp, temp_data))
                    pindata.get(target).update(topology=tpd)
                if pindata.get(target).get('layout', False) and isinstance(pindata.get(target).get('layout'),
                                                                           string_types):
                    tp = os.path.abspath(os.path.join(workspace, os.path.dirname(topo_path)))
                    tp = os.path.join(tp, os.path.join('layouts', pindata.get(target).get('layout')))
                    # apply template_data
                    tpd = yaml.safe_load(template_render(tp, temp_data))
                    pindata.get(target).update(layout=tpd)
                if pindata.get(target).get('hooks', False) and isinstance(pindata.get(target).get('hooks'),
                                                                          string_types):
                    tp = os.path.abspath(os.path.join(workspace, os.path.dirname(topo_path)))
                    tp = os.path.join(tp, os.path.join('hooks', pindata.get(target).get('hooks')))
                    # apply template_data
                    tpd = yaml.safe_load(template_render(tp, temp_data))
                    pindata.get(target).update(hooks=tpd)
            if targets:
                pindata = {t: v for t, v in pindata.items() if t in targets or t == 'cfgs'}

            return pindata
        if 'cfgs' in resource_grp and resource_grp.get('cfgs', False):
            pindict.update(cfgs=resource_grp.pop('cfgs'))
        if 'resource_definitions' in resource_grp and resource_grp.get('resource_definitions', False):
            count = 0
            rs_count = len(resource_grp.get('resource_definitions'))
            for res in resource_grp.get('resource_definitions'):
                if not res.get('recipesets', False):
                    # Need this since azure_vm does not use name as a key
                    if 'azure_vm' == res.get('role', ''):
                        if not res.get('vm_name', False) and rs_count > 1:
                            res.update(dict(vm_name=asset_name + '_' + str(count)))
                            count += 1
                        elif not res.get('vm_name', False):
                            res.update(dict(vm_name=asset_name))
                    else:
                        if not res.get('name', False) and rs_count > 1:
                            res.update(dict(name=asset_name + '_' + str(count)))
                            count += 1
                        elif not res.get('name', False):
                            res.update(dict(name=asset_name))
                else:
                    # this logic is for bkr assets. The name key is in the recipeset dict not in res def
                    # dict unlike the other providers.
                    for rs in res.get('recipesets'):
                        if not rs.get('name', False) and rs_count > 1:
                            rs.update(dict(name=asset_name + '_' + str(count)))
                            count += 1
                        elif not rs.get('name', False):
                            rs.update(dict(name=asset_name))
            resource_grp.update(dict(resource_group_name='cbn-group'))
            pindict['teflo']['topology'] = dict(topology_name='cbn-topo', resource_groups=[resource_grp])
        if 'topology' in resource_grp and resource_grp.get('topology', False) \
                and isinstance(resource_grp.get('topology'), string_types):
            topo_path = os.path.abspath(os.path.join(workspace,
                                                     resource_grp.get('topology')))
            # apply template_data
            pindata = yaml.safe_load(template_render(topo_path, temp_data))
            pindict['teflo']['topology'] = pindata
        if 'layout' in resource_grp and resource_grp.get('layout', False):
            if isinstance(resource_grp.get('layout'), string_types):
                topo_path = os.path.abspath(os.path.join(workspace, resource_grp.pop('layout')))
                # apply template_data
                pindata = yaml.safe_load(template_render(topo_path, temp_data))
                pindict['teflo']['layout'] = pindata
            if isinstance(resource_grp.get('layout'), dict):
                pindict['teflo']['layout'] = resource_grp.pop('layout')
        else:
            pindict.get('teflo').pop('layout')

        if 'hooks' in resource_grp and resource_grp.get('hooks', False):
            if isinstance(resource_grp.get('hooks'), string_types):
                topo_path = os.path.abspath(os.path.join(workspace, resource_grp.pop('hooks')))
                # apply template_data
                pindata = yaml.safe_load(template_render(topo_path, temp_data))
                pindict['teflo']['hooks'] = pindata
            if isinstance(resource_grp.get('hooks'), dict):
                pindict['teflo']['hooks'] = resource_grp.pop('hooks')
        else:
            pindict.get('teflo').pop('hooks')

        return pindict

    @classmethod
    def _build_resource_group_from_asset(cls, asset, pindict):
        resource_grp = {key: val for key, val in asset.profile().items() if key not in
                        set(getattr(asset, '_fields') + ['tx_id'])}
        return cls._build_pinfile(asset_name=getattr(asset, 'name'),
                                  workspace=getattr(asset, 'workspace'),
                                  resource_grp=resource_grp,
                                  pindict=pindict)

    @classmethod
    def _build_beaker_resource_group(cls, asset, pindict):
        """
        Private beaker specific method to build the resource group and definition. It
        will call the sub methods to build the recipe set, the root
        resource definition, and combine them.

        :param asset: the Teflo Asset object
        :type Object: Asset Resource object
        :param pindict: the pinfile dictionary to fill
        :type dict: dictionary
        :return: a Linchpin resource group dictionary
        """

        # Check that the provider params

        provider = get_provider_plugin_class('beaker')()
        asset_params = asset.profile()
        asset_params.update(dict(workspace=getattr(asset, 'workspace')))
        rs_grp = dict(resource_group_type='beaker')

        cls._check_key_exist_in_provider(provider, asset_params)

        # Build the recipe set
        rs = cls._build_beaker_recipe_set(provider, asset_params)

        # Build the resource def
        rd = cls._build_beaker_resource(asset_params)

        # Update the recipe set and resource def with proper ssh params
        # if ssh param is a key_file
        if rs.get('ssh_key_file', None):
            key_dir = os.path.dirname(rs.get('ssh_key_file')[0])
            files = [os.path.basename(f) for f in rs.get('ssh_key_file')]
            if os.path.dirname(key_dir) == '.':
                key_dir = os.path.abspath(key_dir)
            rd['ssh_keys_path'] = key_dir
            rs['ssh_key_file'] = files

        # Add the recipe set to resource def
        rd.update(dict(recipesets=[rs]))

        rs_grp.update(resource_definitions=[rd])

        # build the final pinfile
        return cls._build_pinfile(asset_name=asset_params.get('name'),
                                  workspace=asset_params.get('workspace'),
                                  resource_grp=rs_grp,
                                  pindict=pindict)

    @classmethod
    def _build_beaker_resource(cls, host_params):
        """
        Private beaker specific method to build the root resource definition.

        :param host_params: the Asset Resource profile dictionary
        :return: a Linchpin resource definition dictionary
        """

        resource_def = dict(role='bkr_server')
        params = host_params['provider']

        # Add the resource def params
        for k, v in params.items():
            if k in ['whiteboard', 'max_attempts', 'attempt_wait_time',
                     'cancel_message', 'job_group']:
                resource_def[k] = v
            if k == 'jobgroup':
                resource_def['job_group'] = v

        return resource_def

    @classmethod
    def _build_beaker_recipe_set(cls, provider, host_params):
        """
        Private beaker specific method to build the beaker
        recipeset.

        :param provider: the Teflo Provider to validate against
        :type Object: Provider object
        :param host_params: the Asset Resource profile dictionary
        :type dict: dictionary
        :return: a Linchpin resource definition dictionary
        """

        recipe_set = dict(count=1)
        params = host_params['provider']

        # Build the recipe set with required parameters
        for k, v in params.items():
            for item in provider.req_params:
                if k == item[0]:
                    recipe_set[k] = v

        # Next add the common parameters
        for k, v in params.items():
            if k == 'whiteboard':
                continue
            for item in provider.comm_opt_params:
                if k == item[0] and k == 'kickstart':
                    recipe_set[k] = os.path.abspath(os.path.join(host_params['workspace'], v))
                    continue
                if k == item[0]:
                    recipe_set[k] = v

        # Next add the linchpin common params that differ in name or type
        for k, v in params.items():
            if k == 'ssh_key':
                continue
            if k == 'job_group':
                continue
            for lp, lt in provider.linchpin_comm_opt_params:
                if k == lp:
                    recipe_set[k] = v

        # Next add the teflo common params that differ in name or type
        # but do the conversion to linchpin name or type.
        for k, v in params.items():
            for cp, ct in provider.teflo_comm_opt_params:
                if k == cp and k == 'tag':
                    for lp, lt in provider.linchpin_comm_opt_params:
                        if lp == 'tags':
                            if not isinstance(v, lt[0]):
                                recipe_set[lp] = [v]
                            else:
                                recipe_set[lp] = v
                if k == cp and k == 'kernel_options':
                    for lp, lt in provider.linchpin_comm_opt_params:
                        if lp == 'kernel_options':
                            if not isinstance(v, lt[0]):
                                ko = ""
                                for i in v:
                                    ko += "%s " % i
                                recipe_set[lp] = ko.strip()
                            else:
                                recipe_set[lp] = v
                if k == cp and k == 'kernel_post_options':
                    for lp, lt in provider.linchpin_comm_opt_params:
                        if lp == 'kernel_options_post':
                            if not isinstance(v, lt[0]):
                                kop = ""
                                for i in v:
                                    kop += "%s " % i
                                recipe_set[lp] = kop.strip()
                            else:
                                recipe_set[lp] = v
                if k == cp and k == 'host_requires_options':
                    for lp, lt in provider.linchpin_comm_opt_params:
                        if lp == 'hostrequires':
                            if dict not in v:
                                hr = []
                                for op in cls._bkr_op_list:
                                    for h in v:
                                        if op in h.strip():
                                            hrt, hrv = h.strip().split(op)
                                            if hrt.strip() in ['force', 'rawxml']:
                                                hr.append({hrt.strip(): hrv.strip()})
                                            else:
                                                hr.append(dict(tag=hrt.strip(),
                                                               op=op,
                                                               value=hrv.strip()))
                                recipe_set[lp] = hr
                            else:
                                recipe_set[lp] = v
                if k == cp and k == 'ksmeta':
                    for lp, lt in provider.linchpin_comm_opt_params:
                        if lp == 'ks_meta':
                            if not isinstance(v, lt[0]):
                                ksm = ""
                                for i in v:
                                    ksm += "%s " % i
                                recipe_set[lp] = ksm.strip()
                            else:
                                recipe_set[lp] = v
                if k == cp and k == 'key_values':
                    for lp, lt in provider.linchpin_comm_opt_params:
                        if lp == 'keyvalues':
                            recipe_set[lp] = v

                if k == cp and k == 'ssh_key':
                    if not isinstance(v, str):
                        keys = [key for key in v if 'ssh-rsa' in key]
                        if len(keys) > 0:
                            recipe_set[k] = keys
                        key_files = [ssh_key_file_generator(host_params['workspace'], kf) for kf in v
                                     if 'ssh-rsa' not in kf]
                        if len(key_files) > 0:
                            recipe_set['ssh_key_file'] = key_files
                    else:
                        recipe_set['ssh_key_file'] = [ssh_key_file_generator(host_params['workspace'], v)]

        # Add only the linchpin specific optional parameters
        for k, v in params.items():
            for item in provider.linchpin_only_opt_params:
                if item[0] == 'max_attempts':
                    continue
                if item[0] == 'attempt_wait_time':
                    continue
                if item[0] == 'cancel_message':
                    continue
                if item[0] == 'tx_id':
                    continue
                if k == item[0]:
                    recipe_set[k] = v

        # Add the asset_id
        if params.get('asset_id', None):
            if recipe_set.get('ids', None):
                recipe_set['ids'].append(params.get('asset_id'))
            else:
                recipe_set['ids'] = [params.get('asset_id')]

        # Finally, update the name with the real name
        recipe_set['name'] = host_params['name']

        return recipe_set

    @classmethod
    def _build_openstack_resource_group(cls, asset, pindict):
        """
        Private openstack specific method to build the resource definition.

        :param asset: the Teflo Asset object
        :type Object: Asset Resource object
        :param pindict: the pinfile dictionary to fill
        :type dict: dictionary
        :return: a Linchpin resource definition dictionary
        """

        resource_def = dict(role='os_server', count=1, verify='false')

        provider = get_provider_plugin_class('openstack')()
        host_params = asset.profile()
        host_params.update(dict(workspace=getattr(asset, 'workspace')))
        rs_grp = dict(resource_group_type='openstack')
        params = host_params['provider']
        creds = getattr(provider, 'credentials')

        # Check that the provider params
        cls._check_key_exist_in_provider(provider, host_params)

        # Add any of the op cred params:
        for key, value in creds.items():
            for cp, ct in provider.opt_credential_params:
                if key == cp and key == 'region':
                    resource_def['region_name'] = value

        # Add in all the required params
        for key, value in params.items():
            for cp, ct in provider.req_params:
                if key == cp:
                    resource_def[key] = value

        # Next add in all the common params
        for key, value in params.items():
            for cp, ct in provider.comm_opt_params:
                if key == cp:
                    resource_def[key] = value

        # Next add the common params that differ by    `
        # name or by type
        for key, value in params.items():
            for cp, ct in provider.linchpin_comm_opt_params:
                if key == cp:
                    resource_def[key] = value

        # Next add the linchpin only opt params
        for key, value in params.items():
            if key == 'tx_id':
                continue
            for cp, ct in provider.linchpin_only_opt_params:
                if key == cp:
                    resource_def[key] = value

        # Finally, add the teflo specific common
        # params that differ by name or type
        for key, value in params.items():
            for cp, ct in provider.teflo_comm_opt_params:
                if key == cp and not resource_def.get('fip_pool'):
                    resource_def['fip_pool'] = value

        # Update name with real name of host resource
        resource_def['name'] = host_params['name']

        # update resource group with resource def
        rs_grp.update(resource_definitions=[resource_def])

        # build final pinfile
        return cls._build_pinfile(asset_name=host_params.get('name'),
                                  workspace=host_params.get('workspace'),
                                  resource_grp=rs_grp,
                                  pindict=pindict)

    @classmethod
    def _build_libvirt_resource_group(cls, asset, pindict):
        """
        Private libvirt specific method to build the resource group and definition.

        :param asset: the Teflo Asset object
        :type Object: Asset Resource object
        :param pindict: the pinfile dictionary to fill
        :type dict: dictionary
        :return: a Linchpin resource definition dictionary
        """

        resource_def = dict()
        host_params = asset.profile()
        host_params.update(dict(workspace=getattr(asset, 'workspace')))
        params = host_params['provider']
        provider = get_provider_plugin_class('libvirt')()
        roles = getattr(provider, '_supported_roles')
        rs_grp = dict(resource_group_type='libvirt')

        for p in provider.req_params:
            if p[0] in params:
                if params[p[0]] and params[p[0]] in roles:
                    for k, v in params.items():
                        if k in ['credential', 'hostname', 'tx_id', 'asset_id']:
                            continue
                        resource_def[k] = v
                else:
                    LOG.error('The specified role type is not one of the supported types.')
                    raise HelpersError('One of the following roles must be specified %s.' % roles)

            else:
                LOG.error('Could not find the role key in the provider parameters.')
                raise HelpersError('The key, role, must be specified to build the resource definition properly.')

        # Update with the real host name
        resource_def['name'] = host_params['name']

        # Update with host specific keys
        if resource_def['role'].find('node') != -1:

            # remove the libvirt_evars if any were specified since they don't belong in the
            # topology file. Those get set as evars in the linchpin cfg.
            for evar in ['libvirt_image_path', 'libvirt_user', 'libvirt_become']:
                resource_def.pop(evar, None)

            # for xml key linchpin expects it in the linchpin workspace
            # need to copy it over to the workspace teflo setups in .results
            if resource_def.get('xml', None):
                xml_path = os.path.join(host_params.get('workspace'), resource_def.get('xml', None))
                lp_ws = os.path.join(
                    os.path.join(os.path.dirname(host_params.get('data_folder')), '.results'), 'linchpin')
                if not os.path.exists(xml_path):
                    raise HelpersError('The xml file does not appear to exist in the teflo workspace.')
                os.system('cp -r -f %s %s ' % (xml_path, lp_ws))
                resource_def.update(dict(xml=os.path.basename(xml_path)))

            # update count for a host resource
            if not resource_def.get('count', False):
                resource_def.update(dict(count=1))

        # update resource group with definition
        rs_grp.update(resource_definitions=resource_def)

        # build final pinfile
        return cls._build_pinfile(asset_name=host_params.get('name'),
                                  workspace=host_params.get('workspace'),
                                  resource_grp=rs_grp,
                                  pindict=pindict)

    @classmethod
    def _build_aws_resource_group(cls, asset, pindict):
        """
        Private aws specific method to build the resource group and definition.

        :param asset: the Teflo Asset object
        :type Object: Asset Resource object
        :param pindict: the pinfile dictionary to fill
        :type dict: dictionary
        :return: a Linchpin resource definition dictionary
        """

        resource_def = dict()
        provider = get_provider_plugin_class('aws')()
        host_params = asset.profile()
        host_params.update(dict(workspace=getattr(asset, 'workspace')))
        params = host_params['provider']
        roles = getattr(provider, '_supported_roles')
        rs_grp = dict(resource_group_type='aws')

        for p in provider.req_params:
            if p[0] in params:
                if params[p[0]] and params[p[0]] in roles:
                    for k, v in params.items():
                        if k in ['credential', 'hostname', 'tx_id', 'asset_id']:
                            continue
                        resource_def[k] = v
                else:
                    LOG.error('The specified role type is not one of the supported types.')
                    raise HelpersError('One of the following roles must be specified %s.' % roles)

            else:
                LOG.error('Could not find the role key in the provider parameters.')
                raise HelpersError('The key, role, must be specified to build the resource definition properly.')

        # Update with the real host name
        resource_def['name'] = host_params['name']

        # Update with host specific keys
        if resource_def['role'].find('ec2') != -1 and len(resource_def['role']) == 7:
            # update count for a host resource
            if not resource_def.get('count', False):
                resource_def.update(dict(count=1))

        # Update the specific params that deal with relative file path to be
        # abs pathes in the scenario workspace
        for key in resource_def:
            if key in ['policy_file', 'template_path']:
                if not os.path.isabs(key):
                    ws_abs = os.path.join(host_params.get('workspace'), key)
                    resource_def[key] = ws_abs

        # update resource group with resource def
        rs_grp.update(resource_definitions=[resource_def])

        # build final pinfile
        return cls._build_pinfile(asset_name=host_params.get('name'),
                                  workspace=host_params.get('workspace'),
                                  resource_grp=rs_grp,
                                  pindict=pindict)

    @classmethod
    def _check_key_exist_in_provider(cls, provider, host_params):

        provider_params = host_params['provider']

        provider_keys = [k[0] for k in provider.req_params]
        provider_keys.extend([k[0] for k in provider.comm_opt_params])
        provider_keys.extend([k[0] for k in provider.linchpin_comm_opt_params])
        provider_keys.extend([k[0] for k in provider.teflo_comm_opt_params])
        provider_keys.extend([k[0] for k in provider.linchpin_only_opt_params])

        # Openstack provider does not have teflo only options
        try:
            provider_keys.extend([k[0] for k in provider.teflo_only_opt_params])
        except AttributeError:
            pass

        for key in provider_params:
            if key in ['hostname', 'credential', 'asset_id', 'job_url']:
                continue
            if key not in provider_keys:
                LOG.warning('specified key: %s is not one supported by the teflo provider. '
                            'It will be ignored. Please run teflo validate -s <scenario.yml> '
                            'to make sure you have the proper parameters.' % key)


class LinchpinResponseBuilder(object):

    @classmethod
    def generate_teflo_response(cls, asset, tx_id, lp_res_resource):
        response = []
        for res in lp_res_resource:
            if 'dummy' in res.get('role'):
                response.extend(cls._generate_dummy_response(asset, tx_id, res))
            if 'aws' in res.get('role'):
                response.extend(cls._generate_aws_response(asset, tx_id, res))
            if 'os' in res.get('role'):
                response.extend(cls._generate_os_response(asset, tx_id, res))
            if 'bkr' in res.get('role'):
                response.extend(cls._generate_bkr_response(asset, tx_id, res))
            if 'libvirt' in res.get('role'):
                response.extend(cls._generate_libvirt_response(asset, tx_id, res))
            if 'gcloud' in res.get('role'):
                response.extend(cls._generate_gcloud_response(asset, tx_id, res))
            if 'azure' in res.get('role'):
                response.extend(cls._generate_azure_response(asset, tx_id, res))
            if 'vmware' in res.get('role'):
                response.extend(cls._generate_vmware_response(asset, tx_id, res))
            if 'duffy' in res.get('role'):
                response.extend(cls._generate_duffy_response(asset, tx_id, res))
            if 'ovirt' in res.get('role'):
                response.extend(cls._generate_ovirt_response(asset, tx_id, res))
            if 'docker' in res.get('role'):
                response.extend(cls._generate_docker_response(asset, tx_id, res))
            if 'openshift' in res.get('role'):
                response.extend(cls._generate_ocp_response(asset, tx_id, res))

        if not response:
            response.append(cls._generate_none_instance_response(tx_id))
        return response

    @classmethod
    def _generate_dummy_response(cls, asset, tx_id, res):
        dummy_res = []
        for host in res['hosts']:
            dummy_res.append(dict(ip='1.1.1.1', node_id=123, name=host, tx_id=tx_id, count=1))
        return dummy_res

    @classmethod
    def _generate_aws_response(cls, asset, tx_id, res):
        aws_res = []
        if res.get('role', False) != 'aws_ec2':
            aws_res.append(cls._generate_none_instance_response(tx_id))
        if res.get('instances'):
            for instance in res.get('instances'):
                ip_add = ""
                hostname = ""
                if instance.get('private_ip', False) is not None \
                        and instance.get('public_ip', False) is not None:
                    ip_add = dict(public=str(instance.get('public_ip')),
                                  private=str(instance.get('private_ip')))
                    hostname = instance.get('public_dns_name')
                else:
                    if instance.get('public_ip', False) is not None \
                            and instance.get('private_ip', False) is None:
                        ip_add = str(instance.get('public_ip'))
                        hostname = instance.get('public_dns_name')
                    if instance.get('public_ip', False) is None \
                            and instance.get('private_ip', False) is not None:
                        ip_add = str(instance.get('private_ip'))
                        hostname = instance.get('private_dns_name')
                aws_res.append({'ip': ip_add,
                                'name': hostname,
                                'asset_id': str(instance.get('id')),
                                'tx_id': tx_id
                                })
            return aws_res

    @classmethod
    def _generate_os_response(cls, asset, tx_id, res):
        os_res = []
        if res.get('servers'):
            for os_server in res.get('servers'):
                ip_add = ""
                if os_server.get('accessIPv6', False) != "":
                    ip_add = str(os_server.get('accessIPv6'))
                if os_server.get('private_v4', False) != "" and os_server.get('accessIPv4', False) != "":
                    ip_add = dict(public=str(os_server.get('public_v4')),
                                  private=str(os_server.get('private_v4')))
                else:
                    if os_server.get('private_v4', False) != "" and os_server.get('accessIPv4', False) == "":
                        ip_add = str(os_server['private_v4'])
                    if os_server.get('private_v4', False) == "" and os_server.get('accessIPv4', False) != "":
                        ip_add = str(os_server['accessIPv4'])

                os_res.append({'ip': ip_add,
                               'asset_id': os_server['id'],
                               'name': os_server['name'],
                               'tx_id': tx_id
                               })
        else:
            os_res.append(cls._generate_none_instance_response(tx_id))
        return os_res

    @classmethod
    def _generate_bkr_response(cls, asset, tx_id, res):
        bkr_res = []
        bkr_res.append({'ip': str(lookup_ip_of_hostname(res['system'])),
                        'asset_id': res['id'],
                        'job_url': res['url'],
                        'name': res['system'].split('.')[0],
                        'tx_id': tx_id
                        })
        return bkr_res

    @classmethod
    def _generate_libvirt_response(cls, asset, tx_id, res):
        lib_res = []

        if res.get('role', False) != 'libvirt_node':
            lib_res.append(cls._generate_none_instance_response(tx_id))
        else:
            lib_res.append({'ip': str(res['ip']),
                            'name': res['name'],
                            'asset_id': None,
                            'tx_id': tx_id
                            })

        return lib_res

    @classmethod
    def _generate_gcloud_response(cls, asset, tx_id, res):
        gc_res = []

        if res.get('role', False) != 'gcloud_gce':
            gc_res.append(cls._generate_none_instance_response(tx_id))
        else:
            if res.get('instance_data', False):
                for gce in res.get('instance_data'):
                    ip_add = ""
                    if (gce.get('private_ip', False) != "" or gce.get('private_ip', False) is not None) and \
                            (gce.get('public_ip', False) != "" or gce.get('public_ip', False) is not None):
                        ip_add = dict(public=str(gce.get('public_ip')),
                                      private=str(gce.get('private_ip')))
                    else:
                        if gce.get('private_ip', False) != "" and gce.get('public_ip', False) == "":
                            ip_add = str(gce['private_ip'])
                        if gce.get('private_ip', False) == "" and gce.get('public_ip', False) != "":
                            ip_add = str(gce['public_ip'])

                    gc_res.append({'ip': ip_add,
                                   'name': res.get('name'),
                                   'asset_id': None,
                                   'tx_id': tx_id
                                   })

        return gc_res

    @classmethod
    def _generate_azure_response(cls, asset, tx_id, res):
        az_res = []

        if res.get('role', False) != 'azure_vm':
            az_res.append(cls._generate_none_instance_response(tx_id))
        else:
            ip_add = ""
            for iface in res.get('properties', {}).get('networkProfile', {}).get('networkInterfaces', []):
                for ipcf in iface.get('properties', {}).get('ipConfigurations', []):
                    props = ipcf.get('properties', {})
                    if props.get('publicIPAddress', {}):
                        ip_add = dict(public=str(props.get('publicIPAddress').get('properties').get('ipAddress')),
                                      private=str(props.get('privateIPAddress')))
                    else:
                        ip_add = str(props.get('privateIPAddress'))

            az_res.append({'ip': ip_add,
                           'name': res.get('name'),
                           'asset_id': res.get('properties', None).get('vmId', None),
                           'tx_id': tx_id
                           })

        return az_res

    @classmethod
    def _generate_vmware_response(cls, asset, tx_id, res):
        vmw_res = []

        if res.get('role', False) != 'vmware_guest':
            vmw_res.append(cls._generate_none_instance_response(tx_id))
        else:
            ip_add = ""
            vm = res.get('instance', {})
            if vm.get('ipv6', False):
                ip_add = vm.get('ipv6', False)
            elif vm.get('ipv4', False):
                ip_add = vm.get('ipv4', False)
            vmw_res.append({'ip': ip_add,
                            'name': vm.get('hw_name'),
                            'asset_id': vm.get('moid', None),
                            'tx_id': tx_id
                            })

        return vmw_res

    @classmethod
    def _generate_duffy_response(cls, asset, tx_id, res):
        df_res = []

        if res.get('role', False) != 'duffy':
            df_res.append(cls._generate_none_instance_response(tx_id))
        else:
            ip_add = ""
            for host in res.get('hosts', []):
                ip_add = host
                df_res.append({'ip': ip_add,
                               'name': host,
                               'asset_id': res.get('ssid', None),
                               'tx_id': tx_id
                               })

        return df_res

    @classmethod
    def _generate_ovirt_response(cls, asset, tx_id, res):
        ov_res = []

        if res.get('role', False) != 'ovirt_vm':
            ov_res.append(cls._generate_none_instance_response(tx_id))
        else:
            vm = res.get('vm')

            ov_res.append({'ip': vm.get('ips').get('address_v4'),
                           'name': vm.get('name'),
                           'asset_id': res.get('id', None),
                           'tx_id': tx_id
                           })

        return ov_res

    @classmethod
    def _generate_docker_response(cls, asset, tx_id, res):
        dk_res = []

        if res.get('role', False) != 'docker_container':
            dk_res.append(cls._generate_none_instance_response(tx_id))
        else:
            dk_res.append({'ip': res.get('Config', {}).get('Hostname', ''),
                           'name': res.get('Config', {}).get('Hostname', ''),
                           'asset_id': res.get('Id', None),
                           'tx_id': tx_id
                           })

        return dk_res

    @classmethod
    def _generate_ocp_response(cls, asset, tx_id, res):
        ocp_res = []

        if 'result' in res:
            ocp_res.append(cls._generate_none_instance_response(tx_id))
        else:
            for name in [k for k in res if k not in ['role', 'resource_group']]:
                ocp_res.append({'ip': res.get(name).get('metadata').get('name'),
                                'name': res.get(name).get('metadata').get('name'),
                                'asset_id': res.get(name).get('metadata').get('uid', None),
                                'tx_id': tx_id
                                })

        return ocp_res

    @classmethod
    def _generate_none_instance_response(cls, tx_id):

        return dict(tx_id=tx_id)
