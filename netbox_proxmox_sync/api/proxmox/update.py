from netbox_proxmox_sync.api.errors import APIError, ValidationError
from .extract import fetch_cluster_and_nodes, fetch_tags, fetch_virtual_machines_and_interfaces
from .config import NETBOX_API


def assert_cluster_and_nodes_exist(proxmox_cluster, proxmox_nodes):
    cluster_name = proxmox_cluster['name']
    netbox_cluster_list = NETBOX_API.virtualization.clusters.filter(name=cluster_name)
    if len(netbox_cluster_list) != 1:
        raise ValidationError(
            f'A single "{cluster_name}" virtualization cluster should exist!'
        )
    node_names = set([node['name'] for node in proxmox_nodes])
    existing_names = set([
        node.name for node in NETBOX_API.dcim.devices.filter(name=node_names)
    ])
    missing_nodes = list(node_names - existing_names)
    if len(missing_nodes) > 0:
        missing = [f'Node "{node_name}" is missing!' for node_name in missing_nodes]
        raise ValidationError('Not all cluster nodes registered in NetBox!', missing)
    return list(netbox_cluster_list)[0].id


def update_tags(proxmox_tags):
    try:
        netbox_tags = [dict(tag) for tag in NETBOX_API.extras.tags.filter(
            content_types=['virtualization.virtualmachines'],
        )]
    except Exception:
        raise APIError('Failed to connect to NetBox Cluster!')
    new_tags = {tag['name']: tag for tag in proxmox_tags}
    old_tags = {tag['name']: tag for tag in netbox_tags}

    deleted = [tag for tag in netbox_tags if tag['name'] not in new_tags]
    to_create = [tag for tag in proxmox_tags if tag['name'] not in old_tags]
    updated = []
    for name in new_tags:
        # if it already exists in netbox but something changed: it's updated
        # (only thing that can really change is the color)
        if name in old_tags and new_tags[name]['color'] != old_tags[name]['color']:
            # Better to update the new dict
            old_tags[name]['color'] = new_tags[name]['color']
            updated.append(old_tags[name])
    try:
        created = [dict(x) for x in NETBOX_API.extras.tags.create(to_create)]
    except Exception:
        raise APIError('Error updating tags!')
    deleted_ids = [tag['id'] for tag in deleted]
    result_update = len(updated) == 0 or NETBOX_API.extras.tags.update(updated)
    result_delete = len(deleted) == 0 or NETBOX_API.extras.tags.delete(deleted_ids)
    if not result_update or not result_delete:
        raise APIError('Error updating tags!')

    return created, updated, deleted


def update_old_vms(old_vms, new_vms):
    updated = []
    for name in new_vms:
        # if it already exists in netbox but something changed: we need to update it
        if name not in old_vms:
            continue
        something_changed = False
        # Without this the update is messed, because it's a dict, same for all the "del"s
        # below these ifs (long story, just believe me here)
        del old_vms[name]['site']
        # Iterate over properties, set new stuff
        for key in new_vms[name]:
            # Edge cases... 4 of them...
            if key == 'maxdisk' or key == 'description':
                # These two keys may be None sometimes, which is annoying
                # If it's None now, delete key
                if new_vms[name].get(key) is None and old_vms[name].get(key) is not None:
                    del old_vms[name][key]
                    something_changed = True
                # If it was None and isn't anymore, set key
                if new_vms[name].get(key) is not None and old_vms[name].get(key) is None:
                    old_vms[name][key] = new_vms[name][key]
                    something_changed = True
            elif key == 'status':
                # Netbox returns status via 'value' key... (WHY????)
                if old_vms[name][key]['value'] != new_vms[name][key]:
                    old_vms[name][key] = new_vms[name][key]
                    something_changed = True
                else:
                    del old_vms[name][key]
            elif key == 'device' or key == 'cluster':
                # Device & cluster are set by name
                # (i don't think I made a cluster name change possible... but whatever)
                if old_vms[name][key]['name'] != new_vms[name][key]['name']:
                    old_vms[name][key]['name'] = new_vms[name][key]['name']
                    something_changed = True
                else:
                    del old_vms[name][key]
            elif key == 'tags':
                # Tags is tecnically a list, so we update the whole thing
                old_tags = set([tag['name'] for tag in old_vms[name][key]])
                new_tags = set([tag['name'] for tag in new_vms[name][key]])
                # Reattribute tags
                if old_tags != new_tags:
                    old_vms[name][key] = new_vms[name][key]
                    something_changed = True
            # General case: value for key is different means it changed
            elif old_vms[name][key] != new_vms[name][key]:
                old_vms[name][key] = new_vms[name][key]
                something_changed = True
        if something_changed:
            updated.append(old_vms[name])
    return updated


def update_old_interfaces(proxmox_interfaces, netbox_interfaces):
    created = []
    updated = []
    deleted = []
    # check something changed: create/update/delete interface
    # Note: interfaces is a list for each VM
    # for each proxmox_interface not in deleted, search for it in netbox
    for pi in proxmox_interfaces:
        found = False
        # if found: update/do nothing
        for ni in netbox_interfaces:
            updated_interface = False
            # same VM, same interface name, see if it's necessary to update
            if ni.virtual_machine.name == pi['virtual_machine']['name']:
                if ni.name == pi['name']:
                    found = True
                    updated_interface = ni.untagged_vlan.vid != pi['untagged_vlan']['vid'] or \
                        ni.mac_address.upper() != pi['mac_address'].upper()
                    ni.mac_address = pi['mac_address'].upper()
                    ni.untagged_vlan = pi['untagged_vlan']
                    if updated_interface:
                        updated.append(ni)
                    break
        # if not found: create
        if not found:
            created.append(pi)
    for ni in netbox_interfaces:
        found = False
        # if not found in proxmox: delete (seem simple?)
        for pi in proxmox_interfaces:
            if ni.virtual_machine.name == pi['virtual_machine']['name']:
                if ni.name == pi['name']:
                    found = True
                    break
        if not found:
            deleted.append(dict(ni))
    return created, updated, deleted


def update_virtual_machines(cluster_id, proxmox_vms, proxmox_interfaces):
    try:
        netbox_vms = list(NETBOX_API.virtualization.virtual_machines.filter(
            cluster_id=cluster_id
        ))
        netbox_interfaces = list(NETBOX_API.virtualization.interfaces.all())
    except Exception:
        raise APIError('Failed to connect to NetBox Cluster!')
    # TODO: redo this with vmid, which is more stable, name may change more
    new_vms = {vm['name']: vm for vm in proxmox_vms}
    old_vms = {vm.name: dict(vm) for vm in netbox_vms}
    # Find out which ones to delete, which to create and which to update
    deleted = [dict(vm) for vm in netbox_vms if vm.name not in new_vms]
    to_create = [vm for vm in proxmox_vms if vm['name'] not in old_vms]
    updated = update_old_vms(old_vms, new_vms)

    to_create_i, updated_i, deleted_i = update_old_interfaces(
        proxmox_interfaces, netbox_interfaces
    )

    # First create
    try:
        created = [
            dict(v) for v in NETBOX_API.virtualization.virtual_machines.create(to_create)
        ]
        created_i = [
            dict(i) for i in NETBOX_API.virtualization.interfaces.create(to_create_i)
        ]
    except Exception:
        raise APIError('Error creating VMs & interfaces!')
    # Then delete (interfaces first)
    deleted_ids = [vm['id'] for vm in deleted]
    deleted_i_ids = [i['id'] for i in deleted_i]
    result_delete_i = len(deleted_i) == 0 or NETBOX_API.virtualization.interfaces.delete(deleted_i_ids)
    result_delete = len(deleted) == 0 or NETBOX_API.virtualization.virtual_machines.delete(deleted_ids)
    if not result_delete or not result_delete_i:
        raise APIError('Error deleting VMs & interfaces!')
    # Then update (whatever order)
    result_update = len(updated) == 0 or NETBOX_API.virtualization.virtual_machines.update(updated)
    result_update_i = len(updated_i) == 0 or NETBOX_API.virtualization.interfaces.update(updated_i)
    if not result_update or not result_update_i:
        raise APIError('Error updating VMs & interfaces!')
    return created, updated, deleted, created_i, updated_i, deleted_i
    # return to_create, updated, deleted, to_create_i, updated_i, deleted_i


def all():
    cluster, nodes = fetch_cluster_and_nodes()
    tags = fetch_tags()
    vms, interfaces = fetch_virtual_machines_and_interfaces()
    # Assert some stuff first
    cluster_id = assert_cluster_and_nodes_exist(cluster, nodes)
    # In case tags have changed
    created_tags, updated_tags, deleted_tags = update_tags(tags)
    # Do the first "sync" (creates VMs and their respective interfaces)
    created_vms, updated_vms, deleted_vms, \
        created_interfaces, updated_interfaces, deleted_interfaces = \
        update_virtual_machines(cluster_id, vms, interfaces)
    return {
        'tags': {
            'created': created_tags,
            'updated': updated_tags,
            'deleted': deleted_tags,
        },
        'virtual_machines': {
            'created': created_vms,
            'updated': updated_vms,
            'deleted': deleted_vms,
        },
        'interfaces': {
            'created': created_interfaces,
            'updated': updated_interfaces,
            'deleted': deleted_interfaces,
        }
    }
