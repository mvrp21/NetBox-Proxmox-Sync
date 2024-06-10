from netbox.plugins import PluginConfig


class NetBoxProxmoxSyncConfig(PluginConfig):
    name = 'netbox_proxmox_sync'
    verbose_name = 'NetBox Proxmox Sync'
    description = 'Import cluster information from Proxmox into NetBox'
    version = '0.1'
    base_url = 'netbox-proxmox-sync'


config = NetBoxProxmoxSyncConfig
