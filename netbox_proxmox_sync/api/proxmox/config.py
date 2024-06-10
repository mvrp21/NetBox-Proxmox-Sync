from proxmoxer import ProxmoxAPI
from pynetbox import api as NetboxAPI
from netbox.settings import PLUGINS_CONFIG


# Set default values
NETBOX_DEFAULT_CONFIG = {
    'domain': 'localhost',
    'port': 8001,
    'token': 'this should be set',
    'ssl': True,
    'settings': {
        'vm_role_id': 0,
        'site_id': 0,
        'cluster_type_id': 0,
        'cluster_description': 'A Proxmox Cluster.',
        'default_tag_color_hex': 'ffffff',
    },
}
PROXMOX_DEFAULT_CONFIG = {
    'domain': 'this should be set',
    'port': 8006,
    'user': 'this should be set',
    'token': {
        'name': 'this should be set',
        'value': 'this should be set',
    },
    'ssl': True,
}

USER_PLUGINS_CONFIG = PLUGINS_CONFIG.get('netbox_proxmox_sync', {})
PROXMOX_CONFIG = USER_PLUGINS_CONFIG.get('proxmox', {})
NETBOX_CONFIG = USER_PLUGINS_CONFIG.get('netbox', {})

# TODO: throw errors for missing required fields (like token/user/etc)
#       -> honestly... every field is required here (except maybe ssl)
# PROXMOX
# - Main
PROXMOX_DOMAIN = PROXMOX_CONFIG.get('domain', PROXMOX_DEFAULT_CONFIG['domain'])
PROXMOX_PORT = PROXMOX_CONFIG.get('port', PROXMOX_DEFAULT_CONFIG['port'])
PROXMOX_USER = PROXMOX_CONFIG.get('user', PROXMOX_DEFAULT_CONFIG['user'])
PROXMOX_SSL = PROXMOX_CONFIG.get('ssl', PROXMOX_DEFAULT_CONFIG['ssl'])
# - Token
PROXMOX_TOKEN = PROXMOX_CONFIG.get('token', PROXMOX_DEFAULT_CONFIG['token'])
PROXMOX_TOKEN_NAME = PROXMOX_TOKEN.get('name', PROXMOX_DEFAULT_CONFIG['token']['name'])
PROXMOX_TOKEN_VALUE = PROXMOX_TOKEN.get('value', PROXMOX_DEFAULT_CONFIG['token']['value'])

# NETBOX
# - Main
NETBOX_DOMAIN = NETBOX_CONFIG.get('domain', NETBOX_DEFAULT_CONFIG['domain'])
NETBOX_PORT = NETBOX_CONFIG.get('port', NETBOX_DEFAULT_CONFIG['port'])
NETBOX_TOKEN = NETBOX_CONFIG.get('token', NETBOX_DEFAULT_CONFIG['token'])
NETBOX_SSL = NETBOX_CONFIG.get('ssl', NETBOX_DEFAULT_CONFIG['ssl'])
# - Settings
NETBOX_SETTINGS = NETBOX_CONFIG.get('settings', NETBOX_DEFAULT_CONFIG['settings'])
NETBOX_CLUSTER_TYPE_ID = NETBOX_SETTINGS.get('cluster_type_id', NETBOX_DEFAULT_CONFIG['settings']['cluster_type_id'])
NETBOX_CLUSTER_DESCRIPTION = NETBOX_SETTINGS.get('cluster_description', NETBOX_DEFAULT_CONFIG['settings']['cluster_description'])
NETBOX_VM_ROLE_ID = NETBOX_SETTINGS.get('vm_role_id', NETBOX_DEFAULT_CONFIG['settings']['vm_role_id'])
NETBOX_SITE_ID = NETBOX_SETTINGS.get('site_id', NETBOX_DEFAULT_CONFIG['settings']['site_id'])
NETBOX_DEFAULT_TAG_COLOR = NETBOX_SETTINGS.get('default_tag_color_hex', NETBOX_DEFAULT_CONFIG['settings']['default_tag_color_hex'])

# Create connections
# TODO: more descriptive errors
try:
    PROXMOX_API = ProxmoxAPI(
        PROXMOX_DOMAIN,
        user=PROXMOX_USER,
        port=PROXMOX_PORT,
        token_name=PROXMOX_TOKEN_NAME,
        token_value=PROXMOX_TOKEN_VALUE,
        verify_ssl=PROXMOX_SSL,
    )
except Exception:
    raise RuntimeError('Could not connect to Proxmox Cluster! Verify your credentials!')

try:
    # TODO: allow to change default base path?
    if NETBOX_SSL:
        url = f'https://{NETBOX_DOMAIN}:{NETBOX_PORT}'
    else:
        url = f'http://{NETBOX_DOMAIN}:{NETBOX_PORT}'
    NETBOX_API = NetboxAPI(
        url,
        token=NETBOX_TOKEN,
        threading=True,
    )
except Exception:
    raise RuntimeError('Could not connect to NetBox! Verify your credentials!')
