from netbox_proxmox_sync.api.errors import APIError
from ..proxmox.config import (
    PROXMOX_API,
    NETBOX_SITE_ID,
    NETBOX_CLUSTER_DESCRIPTION,
    NETBOX_CLUSTER_TYPE_ID,
    NETBOX_DEFAULT_TAG_COLOR,
)


def fetch_cluster_and_nodes():
    try:
        proxmox_cluster_info = PROXMOX_API.cluster.status.get()
    except Exception:
        raise APIError('Failed to connect to Proxmox Cluster!')
    cluster = {
        'name': proxmox_cluster_info[0]['name'],
        'type': NETBOX_CLUSTER_TYPE_ID,
        'description': NETBOX_CLUSTER_DESCRIPTION,
        'site': NETBOX_SITE_ID,
    }
    return cluster, proxmox_cluster_info[1:]


def fetch_tags():
    try:
        proxmox_tag_info = PROXMOX_API.cluster.options.get()
    except Exception:
        raise APIError('Failed to connect to Proxmox Cluster!')
    allowed_tags = proxmox_tag_info['allowed-tags']
    tag_colormap = proxmox_tag_info['tag-style']['color-map'].split(';')
    tags = []
    # Create tags with no color defined
    for tag_name in allowed_tags:
        tag_slug = tag_name.lower().replace(' ', '-').replace('.', '_')
        tag_color = NETBOX_DEFAULT_TAG_COLOR.lower()
        tags.append({
            'name': tag_name,
            'slug': tag_slug,
            'color': tag_color,
            'object_types': ['virtualization.virtualmachine']
        })
    # Remap defined tag colors
    for tag_info in tag_colormap:
        tag_name = tag_info.split(':')[0]
        tag_slug = tag_name.lower().replace(' ', '-').replace('.', '_')
        tag_color = tag_info.split(':')[1].lower()
        found = False
        # Find existing tag and update its color
        for tag in tags:
            if tag['name'] == tag_name:
                found = True
                tag['color'] = tag_color
                break
        # ???
        if not found:
            tags.append({
                'name': tag_name,
                'slug': tag_slug,
                'color': tag_color,
                'object_types': ['virtualization.virtualmachine']
            })
    return tags


def fetch_virtual_machines_and_interfaces():
    try:
        cluster_status = PROXMOX_API.cluster.status.get()
    except Exception:
        raise APIError('Failed to connect to Proxmox Cluster!')
    cluster_name = cluster_status[0]['name']
    proxmox_nodes = [node['name'] for node in cluster_status[1:]]
    # List, because node information is stored in the VMs themselves
    virtual_machines = []
    interfaces = []
    for node_name in proxmox_nodes:
        try:
            node_vms = PROXMOX_API.nodes(node_name).qemu.get()
        except Exception:
            raise APIError('Failed to connect to Proxmox Cluster!')
        for vm_status in node_vms:
            new_vm, new_interface = extract_vm_data(cluster_name, node_name, vm_status)
            virtual_machines.append(new_vm)
            interfaces.extend(new_interface)
    return virtual_machines, interfaces


def extract_vm_data(cluster_name, node_name, vm_status):
    try:
        vm_config = PROXMOX_API.nodes(node_name).qemu(vm_status['vmid']).config.get()
    except Exception:
        raise APIError('Failed to connect to Proxmox Cluster!')
    # Get full VM info for creation
    # (specially "maxdisk" is unreliable in the original API call)
    # plus we need the VM's interfaces
    vm_data = {
        'name': vm_status['name'],
        'status': 'active' if vm_status['status'] == 'running' else 'offline',
        'device': {'name': node_name},
        'cluster': {'name': cluster_name},
        'vcpus': vm_status['cpus'],
        'memory': vm_status['maxmem'] / 2**10,
        'tags': [{'name': tag} for tag in vm_config['tags'].split(';')],
        'custom_fields': {'vmid': vm_status['vmid']}
    }
    interfaces_data = extract_vm_interfaces(vm_config)
    # Some VMs either have no disk or their disk isn't explicitly set as the bootdisk
    if vm_status.get('maxdisk') is not None and vm_status['maxdisk'] > 0:
        vm_data['disk'] = int(vm_status['maxdisk'] / 2**30)
    if vm_config.get('description') is not None:
        # NetBox only allows 200 char description, but our VMs have more
        # so we store the description in the "comments" instead
        vm_data['comments'] = vm_config['description']
    return vm_data, interfaces_data


def extract_vm_interfaces(proxmox_vm_config):
    interfaces = []
    for interface_name in [key for key in proxmox_vm_config if key.startswith('net')]:
        interface_info = proxmox_vm_config[interface_name]
        # net[0-9]+: 'virtio=00:00:00:00:00:00,bridge=vmbr<VID>'
        mac = interface_info.split('virtio=')[1].split(',')[0]
        vlan_id = int(interface_info.split('bridge=vmbr')[1].split(',firewall')[0])
        interfaces.append({
            'name': interface_name,
            'virtual_machine': {'name': proxmox_vm_config['name']},
            'mac_address': mac.upper(),  # NetBox saves uppercase anyways
            'mode': 'access',
            'untagged_vlan': {'vid': vlan_id},
            # 'bridge': bridge
        })
    return interfaces
