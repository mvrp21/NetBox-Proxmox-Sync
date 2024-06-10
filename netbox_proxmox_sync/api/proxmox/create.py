from netbox_proxmox_sync.api.errors import APIError, ValidationError
from .extract import fetch_cluster_and_nodes, fetch_tags, fetch_virtual_machines_and_interfaces
from .config import NETBOX_API


def assert_cluster_does_not_exist(cluster_name):
    netbox_cluster_list = NETBOX_API.virtualization.clusters.filter(name=cluster_name)
    if len(netbox_cluster_list) != 0:
        raise ValidationError(f'Virtualization cluster "{cluster_name}" already exists!')


def assert_nodes_exist(proxmox_nodes):
    node_names = set([node['name'] for node in proxmox_nodes])
    existing_names = set([
        node.name for node in NETBOX_API.dcim.devices.filter(name=node_names)
    ])
    missing_nodes = list(node_names - existing_names)
    if len(missing_nodes) > 0:
        missing = [f'Node "{node_name}" is missing!' for node_name in missing_nodes]
        raise ValidationError('Not all cluster nodes registered in NetBox!', missing)


def create_cluster(proxmox_cluster, proxmox_nodes):
    try:
        # Already formatted the data for this :)
        netbox_cluster = NETBOX_API.virtualization.clusters.create(**proxmox_cluster)
        node_names = [node['name'] for node in proxmox_nodes]
        # Update nodes' cluster
        netbox_nodes = list(NETBOX_API.dcim.devices.filter(name=[node_names]))
        for node in netbox_nodes:
            node.cluster = {'name': proxmox_cluster['name']}
        # In case of error "rollback"
        if not NETBOX_API.dcim.devices.update(netbox_nodes):
            netbox_cluster.delete()
            raise APIError('Failed to set Nodes\' cluster!')
    except Exception as e:
        raise APIError(e)
    # Return JSON serializable dict :)
    return dict(netbox_cluster)


def create_tags_and_custom_fields(proxmox_tags):
    try:
        existing_tags = NETBOX_API.extras.tags.filter(content_types=[
            'virtualization.virtualmachines',
        ])
    except Exception as e:
        raise APIError(e)
    # If tags for VMs already exist complain
    if len(existing_tags) > 0:
        names = [tag.name for tag in existing_tags]
        errors = [f'Tag "{name}" should not exist!' for name in names]
        raise ValidationError('Some VM tags already exist!', errors)
    # If vmid custom field already exist complain
    custom_field_exists = len(NETBOX_API.extras.custom_fields.filter(name='vmid')) > 0
    if custom_field_exists:
        raise ValidationError('Custom field "vmid" already exists!')
    custom_fields = [{
        'name': 'vmid',
        'label': 'VMID',
        'description': '[Proxmox] VM/CT ID',
        'ui_editable': 'no',
        'ui_visible': 'always',
        'filter_logic': 'exact',
        'type': 'integer',
        'content_types': ['virtualization.virtualmachine']
    }]
    # Create stuff :)
    try:
        netbox_tags = NETBOX_API.extras.tags.create(proxmox_tags)
        netbox_custom_fields = NETBOX_API.extras.custom_fields.create(custom_fields)
    except Exception as e:
        raise APIError(e)
    # Return JSON serializable lists :)
    return [dict(x) for x in netbox_tags], [dict(x) for x in netbox_custom_fields]


def create_virtual_machines(proxmox_vms, proxmox_interfaces):
    # Just create stuff :)
    try:
        netbox_vms = NETBOX_API.virtualization.virtual_machines.create(proxmox_vms)
        netbox_interfaces = NETBOX_API.virtualization.interfaces.create(proxmox_interfaces)
    except Exception as e:
        raise APIError(e)
    # Return JSON serializable lists :)
    return [dict(x) for x in netbox_vms], [dict(x) for x in netbox_interfaces]


# FIXME: should try a full rollback in case of any error
def all():
    cluster, nodes = fetch_cluster_and_nodes()
    tags = fetch_tags()
    vms, interfaces = fetch_virtual_machines_and_interfaces()
    # Assert some stuff first
    assert_cluster_does_not_exist(cluster['name'])
    assert_nodes_exist(nodes)
    # Create basic info
    netbox_cluster = create_cluster(cluster, nodes)
    netbox_tags, netbox_custom_fields = create_tags_and_custom_fields(tags)
    # Do the first "sync" (creates VMs and their respective interfaces)
    netbox_vms, netbox_interfaces = create_virtual_machines(vms, interfaces)
    return {
        'cluster': netbox_cluster,
        'tags': netbox_tags,
        'custom_fields': netbox_custom_fields,
        # 'nodes': netbox_nodes,
        'virtual_machines': netbox_vms,
        'interfaces': netbox_interfaces
    }
