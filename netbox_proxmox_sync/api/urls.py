from django.urls import path
from . import views

app_name = 'netbox_proxmox_sync'

urlpatterns = [
    path('create/', views.CreateCluster.as_view(), name='proxmoxsync_create'),
    path('update/', views.UpdateCluster.as_view(), name='proxmoxsync_update'),
    path('delete/', views.DeleteCluster.as_view(), name='proxmoxsync_delete'),
]
