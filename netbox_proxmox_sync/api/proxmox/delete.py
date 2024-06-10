from netbox_proxmox_sync.api.errors import APIError, ValidationError
from .extract import fetch_cluster_and_nodes
from .config import NETBOX_API


def all():
    # Fetch all data (for proper output)
    cluster, _ = fetch_cluster_and_nodes()
    netbox_clusters = list(NETBOX_API.virtualization.clusters.filter(
        name=cluster['name']
    ))
    if len(netbox_clusters) == 0:
        raise ValidationError(f'Cluster "{cluster["name"]}" does not exist!')
    netbox_cluster = dict(netbox_clusters[0])
    try:
        netbox_interfaces = [dict(i) for i in NETBOX_API.virtualization.interfaces.all()]
        netbox_vms = [dict(i) for i in NETBOX_API.virtualization.virtual_machines.filter(
            cluster_id=netbox_cluster['id'],
        )]
        netbox_tags = [dict(f) for f in NETBOX_API.extras.tags.filter(
            content_types=['virtualization.virtualmachines'],
        )]
        netbox_custom_fields = [dict(f) for f in NETBOX_API.extras.custom_fields.filter(
            content_types=['virtualization.virtualmachine'],
        )]
    except Exception:
        raise APIError(f'Failed to fetch all "{cluster["name"]}" cluster information!')
    # Actually delete stuff
    si = NETBOX_API.virtualization.interfaces.delete([
        interface['id'] for interface in netbox_interfaces
    ])
    sv = NETBOX_API.virtualization.virtual_machines.delete([
        vm['id'] for vm in netbox_vms
    ])
    st = NETBOX_API.extras.tags.delete([
        tag['id'] for tag in netbox_tags
    ])
    sf = NETBOX_API.extras.custom_fields.delete([
        custom_field['id'] for custom_field in netbox_custom_fields
    ])
    sc = NETBOX_API.virtualization.clusters.delete([netbox_cluster['id']])
    if not (si and sv and st and sf and sc):
        raise APIError(f'Failed to delete all "{cluster["name"]}" cluster information!')

    return {
        'cluster': netbox_cluster,
        'tags': netbox_tags,
        'custom_fields': netbox_custom_fields,
        # 'nodes': netbox_nodes,
        'virtual_machines': netbox_vms,
        'interfaces': netbox_interfaces
    }
