# User Guide

### To return to documentation home page press [here](https://redhatqe.github.io/teflo_linchpin_plugin/docs/index.html)

## Installation

### Before Install
In order for Linchpin to install successfully. You must make sure certain pre-reqs and rpms are installed.
For the list of 
[minimum requirements](https://linchpin.readthedocs.io/en/latest/installation.html#minimal-software-requirements) refer to their installation documentation.

### Install
To install the plugin you can use pip. 
```bash
$ pip install git+https://gitlab.cee.redhat.com/ccit/teflo/plugins/teflo_linchpin_plugin.git@<tagged_version>
```

This will install 
* Teflo software from our Gerrit respository 
* Linchpin from pypi

### Post Install
Some dependencies are required by certain providers that are not installed by Linchpin by default.
Specifically for:
* Beaker
* Libvirt
* Docker
* Azure
* OpenShift
* VMware

To install the required dependencies you have a couple options. 

You can install using pip
```bash
$ pip install linchpin[beaker]
``` 
or 

you can install using the linchpin `setup` command. 
```bash
$ linchpin setup beaker
$ linchpin setup libvirt [--ask-sudo-pass]
```

For more information about the 
[setup](https://linchpin.readthedocs.io/en/latest/installation.html#linchpin-setup-automatic-dependency-installation) 
command refer to the installation guide.

## Credentials
When provisioning resources that require credentials you have a couple different options:

* Provide the Linchpin `credentials` dictionary, that points to a credentials file,
 as part of the resource definition

**Note**

When using a credentials file with Linchpin. You will need to make sure the following
values, **vault_encryption=False** and **vaul_pass=''** are set under `[evars]` in the 
linchpin.conf if the file is not encrypted.


```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    resource_group_type: openstack
    resource_definitions:
      - name: {{ name | default('database') }}
        role: os_server
        flavor: {{ flavor | default('m1.small') }}
        image:  rhel-7.5-server-x86_64-released
        count: 1
        keypair: {{ keypair | default('db2-test') }}
        networks:
          - {{ networks | default('provider_net_ipv6_only') }}
    credentials:
      filename: clouds.yaml
      profile: ci-rhos
```
* Export the provider specific credential environmental variables that Linchpin/Ansible Support

* Provide Teflo the provider credentials in the `teflo.cfg` and reference that particular 
section using Teflo's `credential` parameter. In most cases Teflo will take the credential
information export the appropriate Ansible credential environmental variables for you. 
  ```ini
  #Example credentials for Azure provider in teflo.cfg
  
  [credentials:az-creds]
  subscription_id=123-456
  tenant=ccit
  ad_user=test-user
  ad_password=changeMe
  ```
  ```yaml
  #Example teflo scenario referencing the credential in the teflo.cfg
  
   provision:
    - name: db2_dummy
      provisioner: linchpin-wrapper
      groups: example
      credential: az-creds
      resource_group_type: azure
      resource_definitions:
        - vm_name: TestMultiVm
          count: 2
          role: azure_vm
          resource_group: ccit
          deepclean: True


  ```    
### Configuring Credentials
Below are the provider specific options that can be specified in the `teflo.cfg` 

#### OpenStack

|key| Description | Required|
|  ---  |   ----  | ---  |
|auth_url|The authentication URL of your OpenStack tenant. (identity)| True|
|tenant_name|The name of your OpenStack tenant.|True|
|username|The username of your OpenStack tenant.|True|
|password|The password of your OpenStack tenant.|True|
|region|The region of your OpenStack tenant to authenticate with.|False|
|domain_name|The name of your OpenStack domain to authenticate with. When not set teflo will use the ‘default’|False|


#### Beaker

|key| Description | Required|
|  ---  |   ----  | ---  |
|hub_url|The beaker server url.| True|
|keytab|name of the keytab file, which must be placed in the scenario workspace directory.|False|
|keytab_principal|The principal value of the keytab.|False|
|username|Beaker username.|False|
|password|Beaker username’s password.|False|
|ca_cert|Path to a trusted cert file.|False|
|realm|The kerberos domain realm to use.|False|
|service|The kerberos service prefix to use (i.e. HTTP)|False| 
|ccache|The kerberos credentials cache to reference|False|


#### AWS

|key| Description | Required|
|  ---  |   ----  | ---  |
|aws_access_key_id|The access key id that should be used to authenticate.|True|
|aws_secret_access_key|The secrete for access key id.|True|
|aws_security_token|The security token to use.|False|


#### Libvirt
You most likely won't need to do use these options but if you would like Teflo
to setup a libvirt authentication config file. Provide the following 

|key| Description | Required|
|  ---  |   ----  | ---  |
|username|The username that has the required privileges with the Libvirt daemon|True|
|password|The password of the user to be used with the Libvirt daemon.|True|


### GCE
For more information on how to generate a service account and its
associated credentials file. Refer to the following 
[documentation](https://libcloud.readthedocs.io/en/stable/compute/drivers/gce.html#service-account)

|key| Description | Required|
|  ---  |   ----  | ---  |
|project_id| The Google project to use| True|
|service_account_email|A service account user to authenticate with your project.|True|
|credentials_file|The credentials file for the service_account user.|True|


### Azure 

|key| Description | Required|
|  ---  |   ----  | ---  |
|subscription_id|The Microsoft Azure subscription id|True|
|tenant|A tenant tied to the subscription.|True|
|client_id|The service principal id to use.|False|
|secret|The service principals authentication secrete.|False|
|ad_username|An Active Directory user in the tenant.|False|
|ad_password|The Active Directory user's password.|False|


### VMware

|key| Description | Required|
|  ---  |   ----  | ---  |
|hostname|The VMware vCenter Server url.|True|
|username|A VMware user in the vCenter Domain.|True|
|password|The VMware user's password.|True|
|port|The HTTP port to connect to.|False|
|validate_certs|Whether to check validate SSL certs.|False|


### oVirt

It's recommended that you follow the Linchpin 
[documentation](https://linchpin.readthedocs.io/en/latest/ovirt.html#credentials-management) 
to setup the cloud.yml file for oVirt and pass it to Linchpin `credentials` key


### OpenShift

|key| Description | Required|
|  ---  |   ----  | ---  |
|api_url|The OpenShift endpoint to authenticate to.|True|
|api_token|The OpenShift token for the account.|False|
|kuebconfig|Path to a specific kuebconfig file other than in ~/.kube/config.|False|
|context|The specific context in the kubeconfig file to use.|False|
|cert_file|Path to a certificate used to authenticate with the API.|False|
|key_file|Path to a key file used to authenticate with the API.|False|
|ca_cert|Path to a trusted cert file.|False|
|ssl_ca_cert|Path to a CA certificate used to authenticate with the API. It must be the full chain.|False|
|verify_ssl|Whether to enable ssl certificate checking.|False| 
|username|The OpenShift account username to use if not using api_token|False|
|password|The OpenShift account username's password when not using api_token|True| 

  
## Linchpin configuration
It is recommended that every scenario that uses Linchpin provide their own `linchpin.conf` file in the Teflo
workspace. This can be used for settings like enabling/disabling credential encryption, authentication debug
logging, etc. 

Note that this plugin will override some default settings in the `linchpin.conf` for better integration 
with Teflo. Below are the settings that are overwritten

|Setting| Plugin Value|
 |  ---  |   ----      |
 |workspace | Teflo's workspace as set by the `-w` option or current directory teflo executing in |
 |rundb_conn| a linchpin folder in Teflo's results directory. `<root_data_folder>/.results/linchpin`|
 |inventory_path| Teflo's path to the master ansible inventory. `<root_data_folder>/.results/inventory/master-<unique>`|
 |default_inventories_path| Teflo's inventory directory `<root_data_folder>/.results/inventory/` or the value set for `static_inventory` in `teflo.cfg`|
 |inventories_folder| Teflo's inventory folder name `inventory`|
 |distill_data | True|
 |generate_resources | False | 
 |debug_mode| True|
 |no_monitor| True|
 |default_ssh_key_path | Teflo's key directory in the workspace `<teflo_workspace>/keys`|

## Provisioning Assets with Linchpin

Below shows all the possible Teflo DSL keys that the Linchpin plugin can use to provision assets. 

```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    pinfile: <dict_key_values>
    topology: <String>
    resource_group_type: <String>
    resource_definitions: [List of definition dictionaries]
    cfgs: <dict_key_values>
    layout: <String | dict_key_values>
    hooks: <String | dict_key_values>
    template_data: <dict_key_values>
    credentials: <dict_key_values>

```

<table class="tg">
  <tr>
    <th class="tg-7un6">Key</th>
    <th class="tg-14gg">Description</th>
    <th class="tg-14gg">Type</th>
    <th class="tg-14gg">Required</th>
  </tr>
  <tr>
    <td class="tg-8m83">pinfile</td>
    <td class="tg-8m83">a dictionary containing the following keys.<br><span style="font-style:italic">path - </span>relative path to the pinfile in the Teflo workspace. <br><span style="font-style:italic">targets -  </span>list of targets in pinfile<br></td>
    <td class="tg-8m83">Dict</td>
    <td class="tg-8m83">False, however<br>one of the following<br>must be specified<br>pinfile, topology,<br>or both resource_group_type<br>and resource_definitions</td>
  </tr>
  <tr>
    <td class="tg-14gg">topology</td>
    <td class="tg-14gg">a relative path to a Linchpin topology file in the Teflo workspace</td>
    <td class="tg-14gg">String</td>
    <td class="tg-14gg">False, however<br>one of the following<br>must be specified<br>pinfile, topology,<br>or both resource_group_type<br>and resource_definitions</td>
  </tr>
  <tr>
    <td class="tg-8m83">resource_group_type</td>
    <td class="tg-8m83">The value of the provider to provision assets from. This is used in conjunction with the <span style="font-style:italic">resource_definitions</span> key</td>
    <td class="tg-8m83">String</td>
    <td class="tg-8m83">False, however<br>one of the following<br>must be specified<br>pinfile, topology,<br>or both resource_group_type<br>and resource_definitions</td>
  </tr>
  <tr>
    <td class="tg-14gg">resource_definitions</td>
    <td class="tg-14gg">a list of dictionaries that contain supported Linchpin provider key/values. This is used in conjunction with the <span style="font-style:italic">resource_group_type</span> key</td>
    <td class="tg-14gg">List</td>
    <td class="tg-14gg">False</td>
  </tr>
  <tr>
    <td class="tg-8m83">cfgs</td>
    <td class="tg-8m83">a dictionary to provide linchpin with a set of variables that can be used in the inventory layouts</td>
    <td class="tg-8m83">Dict</td>
    <td class="tg-8m83">False</td>
  </tr>
  <tr>
    <td class="tg-14gg">layouts</td>
    <td class="tg-14gg">This can be a relative path to a Linchpin layout file in the Teflo workspace or a dictionary of Linchpin layout key/values</td>
    <td class="tg-eiwr">String | Dict</td>
    <td class="tg-14gg">False</td>
  </tr>
  <tr>
    <td class="tg-8m83">hooks</td>
    <td class="tg-8m83">This can be a relative path to a Linchpin hooks file in the Teflo workspace or a dictionary of Linchpin hooks key/values</td>
    <td class="tg-q9yg">String | Dict<br></td>
    <td class="tg-8m83">False</td>
  </tr>
  <tr>
    <td class="tg-14gg">credentials</td>
    <td class="tg-14gg">A dictionary containing the Linchpin credential key/values</td>
    <td class="tg-14gg">Dict</td>
    <td class="tg-14gg">False</td>
  </tr>
  <tr>
    <td class="tg-8m83">template_data</td>
    <td class="tg-8m83">a dictionary containing the key/values to template jinja data against Linchpin PiinFiles, Topology, Layout, and/or Hooks files:<br><span style="font-style:italic">vars</span> - a dictionary of key/values that should be templated<br><span style="font-style:italic">file</span> - a relative path to a yaml file that contains the vars to template<br></td>
    <td class="tg-8m83">Dict</td>
    <td class="tg-8m83">False</td>
  </tr>
</table>

For the full list of Linchpin provider specific keys you can use in conjuction with the `resource_group_type`
and `resource_definitions` keys directly in the scenario file or in external PinFile/Topology files, 
we refer to the 
[provider](https://linchpin.readthedocs.io/en/latest/providers.html) documentation. 

Now that you know what keys are available to you in Teflo DSL. Let's go over some examples. 

### Examples 

For those that come from using Linchpin directly and are looking to leverage Teflo, 
you can still leverage the work you have put into developing PinFiles, Topology, Layout, and Hooks 
without having to re-write them. Suppose you have a Linchpin workspace like so

```bash
openstack-simple
├── layouts
│   └── simple-layout.yml
├── hooks
│   └── ansible
│       └── ex_hook
│           ├── ex1.yaml
│           └── ex2.yaml
|── credentials
├── PinFile
└── topologies
    └── simple-topo.yml

```
You can move this workspace into the Teflo workspace and in your scenario.yml you can refer to this in various ways.
Refer to the first 10 examples below. 

If you're already a Teflo user and looking to leverage Linchpin more as a pure provisioner, refer to examples 11-13. 

#### Example 1
This first example uses the PinFile. The PinFile is loaded, as well as the referenced layout, 
and passed directly to Linchpin.
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    pinfile:
      path: openstack-simple/PinFile

```

#### Example 2
Using the same PinFile lets assume you only want to provision specific targets and layout would be applied.
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    pinfile:
      path: openstack-simple/PinFile
      targets:
        - openstack-stage
        - openstack-dev

```

#### Example 3
Using the same PinFile lets assume you only want to provision specific targets and pass in variable template data.
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    pinfile:
      path: openstack-simple/PinFile
      targets:
        - openstack-stage
    template_data:
      vars:
        flavor: RHEL-8.1
        keypair: stage-key
```

#### Example 4
Using the same PinFile lets assume you only want to provision specific targets but pass in using a variable file.
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    pinfile:
      path: openstack-simple/PinFile
      targets:
        - openstack-stage
    template_data:
      file: os_template_data.yml
```

#### Example 5
Let's assume you want to treat Teflo scenario.yml like a PinFile and you just want to run the topology.
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    topology: openstack-simple/topologies/simple-topo.yml
    template_data:
      file: os_template_data.yml
```

#### Example 6
Let's assume you want to treat Teflo scenario.yml like a PinFile and you just want to run the topology and layout file 
with some config variables.
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    topology: openstack-simple/topologies/simple-topo.yml
    layout: openstack-simple/layouts/simple-layout.yml
    cfgs:
      openstack:
        __id__: id
```

#### Example 7
Let's assume you want to treat Teflo scenario.yml like a PinFile and you want to run the topology/layout files 
with some config variables and hooks. 
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    topology: openstack-simple/topologies/simple-topo.yml
    layout: openstack-simple/layouts/simple-layout.yml
    hooks:
        postup:
          - name: ex_hook
            type: ansible
            src:
              type: git
              url: https://github.com/14rcole/sample-hook
            context: True
            actions:
              - playbook: ex1.yaml
              - playbook: ex2.yaml
    cfgs:
      openstack:
        __id__: id
```

#### Example 8
Let's assume you want to treat Teflo scenario.yml like a PinFile but you want to input the layout directly rather
than using a file and still use some config variables and hooks. 
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    topology: openstack-simple/topologies/simple-topo.yml
    layout:
      inventory_layout:
        vars:
          hostname: __IP__
          id: __id__
          ansible_ssh_private_key_file: {{ keypath | default('keys/test-key') }}
          ansible_user: cloud-user
        hosts:
          example-node:
            count: 1
            host_groups:
              - example
    hooks:
        postup:
          - name: ex_hook
            type: ansible
            src:
              type: git
              url: https://github.com/14rcole/sample-hook
            context: True
            actions:
              - playbook: ex1.yaml
              - playbook: ex2.yaml
    cfgs:
      openstack:
        __id__: id
```

#### Example 9
Let's assume you want to treat Teflo scenario.yml like a PinFile and input everything from topology to hooks. 
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    resource_group_type: openstack
    resource_definitions:
      - name: {{ instance | default('database') }}
        role: os_server
        flavor: {{ flavor | default('m1.small') }}
        image:  rhel-7.5-server-x86_64-released
        count: 2
        keypair: {{ keypair | default('db2-test') }}
        networks:
          - {{ networks | default('provider_net_ipv6_only') }}
    credentials:
      filename: clouds.yml
      profile: ci-rhos
    layout:
      inventory_layout:
        vars:
          hostname: __IP__
          id: __id__
          ansible_ssh_private_key_file: {{ keypath | default('keys/test-key') }}
          ansible_user: cloud-user
        hosts:
          example-node:
            count: 2
            host_groups:
              - example
    hooks:
        postup:
          - name: ex_hook
            type: ansible
            src:
              type: git
              url: https://github.com/14rcole/sample-hook
            context: True
            actions:
              - playbook: ex1.yaml
              - playbook: ex2.yaml
    cfgs:
      openstack:
        __id__: id
```

#### Example 10
Let's assume you want to treat Teflo scenario.yml like a PinFile and input topology data but 
still use a layout file. 
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    resource_group_type: openstack
    resource_definitions:
      - name: {{ instance | default('database') }}
        role: os_server
        flavor: {{ flavor | default('m1.small') }}
        image:  rhel-7.5-server-x86_64-released
        count: 2
        keypair: {{ keypair | default('db2-test') }}
        networks:
          - {{ networks | default('provider_net_ipv6_only') }}
    layout: openstack-simple/layouts/simple-layout.yml
    cfgs:
      openstack:
        __id__: id
```

#### Example 11
Let's assume you want to treat Teflo scenario.yml like normal but leverage Linchpin as a pure provisioner
using no credentials. 
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    groups:
      - example
    resource_group_type: openstack
    resource_definitions:
      - name: {{ instance | default('database') }}
        role: os_server
        flavor: {{ flavor | default('m1.small') }}
        image:  rhel-7.5-server-x86_64-released
        count: 2
        keypair: {{ keypair | default('db2-test') }}
        networks:
          - {{ networks | default('provider_net_ipv6_only') }}
    ansible_params:
      ansible_user: cloud-user
      ansible_ssh_private_key_file: keys/{{ OS_KEYPAIR }}

```

#### Example 12
Let's assume you want to treat Teflo scenario.yml like normal but leverage Linchpin as a pure provisioner
using teflo credentials in teflo.cfg. 
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    credential: osp-creds
    groups:
      - example
    resource_group_type: openstack
    resource_definitions:
      - name: {{ instance | default('database') }}
        role: os_server
        flavor: {{ flavor | default('m1.small') }}
        image:  rhel-7.5-server-x86_64-released
        count: 2
        keypair: {{ keypair | default('db2-test') }}
        networks:
          - {{ networks | default('provider_net_ipv6_only') }}
    ansible_params:
      ansible_user: cloud-user
      ansible_ssh_private_key_file: keys/{{ OS_KEYPAIR }}

```

#### Example 13
Let's assume you want to treat Teflo scenario.yml like normal but leverage Linchpin as a pure provisioner
using predefined cloud credentials file from Linchpin workspace. 
```yaml
provision:
  - name: db2_dummy
    provisioner: linchpin-wrapper
    groups:
      - example
    resource_group_type: openstack
    resource_definitions:
      - name: {{ instance | default('database') }}
        role: os_server
        flavor: {{ flavor | default('m1.small') }}
        image:  rhel-7.5-server-x86_64-released
        count: 2
        keypair: {{ keypair | default('db2-test') }}
        networks:
          - {{ networks | default('provider_net_ipv6_only') }}
    credentials:
      filename: clouds.yml
      profile: ci-rhos
    ansible_params:
      ansible_user: cloud-user
      ansible_ssh_private_key_file: keys/{{ OS_KEYPAIR }}

```

### Generating Ansible Inventory

Both Teflo and Linchpin have the capability to generate Ansible inventory file but do so in different
ways. We've tried to be as flexible as possible. Here are some general guidelines

* To have Linchpin generate the inventory you must do the following (Refer to examples 1-10):
    * Do specify the Linchpin `layout` or `pinfile` key (the pinfile must already be using the `layout` key)
    * Do not specify the Teflo `groups` and `ansible_params` keys


* To have Teflo generate the inventory you must do the following (Refer to example 11-13):
    * Do specify the Teflo `groups` and `ansible_params` keys
    * Do not specify the Linchpin `layout` or `pinfile` key
    
### Using Linchpin hooks vs Teflo Orchestrate

We believe there is room for both operations. A benefit are Linchpin's `preup` and `postdestroy` hooks
since Teflo does not have similar functionality. Where we suggest users should start to consider moving
away from Linchpin hooks is if any `postup` hooks have been configured. That is where thos scripts/playbooks
can be moved over and configured in Teflo's 
[Orchestrate](https://teflo.readthedocs.io/en/latest/users/definitions/orchestrate.html) section. It can help 
structure and organize this activity better.
