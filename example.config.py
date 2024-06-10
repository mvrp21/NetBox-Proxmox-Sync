PLUGINS = ['netbox_proxmox_sync']

PLUGINS_CONFIG = {
  'netbox_proxmox_sync': {
    'netbox': {
        'domain': 'proxbox.c3sl.ufpr.br',
        'port': 443,
        'token': 'tokennnnnnnnnnnnn-aaaaaaaaaaa',
        'ssl': True,
        'settings': {
            'vm_role_id': 0,
            'site_id': 0,
            'cluster_type_id': 0,
            'cluster_description': 'C3SL\'s Proxmox Cluster.',
            'default_tag_color_hex': 'ffffff',
        },
    },
    'proxmox': {
        'domain': 'proxmox.c3sl.ufpr.br',
        'port': 443,
        'user': 'netbox@pve',
        'token': {
            'name': 'also-this',
            'value': 'should-be-secret-hmmmmmm',
        },
        'ssl': True,
    },
  }
}
