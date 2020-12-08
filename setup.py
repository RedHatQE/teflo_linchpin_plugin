import os
import re
import io
from setuptools import setup, find_packages


ROOT = os.path.dirname(__file__)
VERSION_RE = re.compile(r'''__version__ = ['"]([a-zA-Z0-9.]+)['"]''')


def get_version():
    init = open(os.path.join(ROOT, 'teflo_linchpin_plugin', '__init__.py')).read()
    return VERSION_RE.search(init).group(1)

# reading description from README.rst
with io.open(os.path.join(ROOT, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()



setup(
    name='teflo_linchpin_plugin',
    version=get_version(),
    license='GPLv3',
    description="Linchpin provisioner plugin for Teflo",
    long_description="""# teflo_linchpin_plugin\n\n* A provisioner plugin for Teflo to provision resources using Linchpin\n""",
    long_description_content_type='text/markdown',
    author="Red Hat Inc",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'linchpin>=1.9.2'
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
    ],
    entry_points={
        'provisioner_plugins': 'linchpin_wrapper_plugin = teflo_linchpin_plugin:LinchpinWrapperProvisionerPlugin',
    }
)
