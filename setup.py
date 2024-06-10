from setuptools import find_packages, setup

setup(
    name='netbox-proxmox-sync',
    version='0.1',
    description='Import Proxmox cluster info into NetBox.',
    install_requires=['pynetbox', 'proxmoxer'],
    include_package_data=True,
    package_data={
        "": ['*','*/*','*/*/*'],
    },
    packages=find_packages(),
    zip_safe=False,
)
