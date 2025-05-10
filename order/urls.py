# urls.pys
from django.urls import path
from . import views

# Set the custom 404 handler at the module level
handler404 = views.custom_404

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('orders/create', views.view_create_orders, name='view_create_orders'),
    path('orders/create-order', views.create_order, name='create_order'),
    path('orders/track', views.view_track_orders, name='view_track_orders'),
    path('orders/track/<int:id>/', views.view_track_order_detail, name='view_track_order_detail'),
    path('orders/track/<int:shipment_id>/change_status/', views.change_shipment_status, name='change_shipment_status'),
    path('orders/track/<int:shipment_id>/submit_missing/', views.submit_missing_items, name='submit_missing_items'),
    path('shipment/<int:shipment_id>/report/', views.generate_shipment_report, name='generate_shipment_report'),
]
