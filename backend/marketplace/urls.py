from django.urls import path
from . import views

urlpatterns = [
    path('', views.marketplace_home, name='marketplace_home'),
    path('item/<uuid:item_id>/', views.item_detail, name='item_detail'),
    path('item/add/', views.add_item, name='add_item'),
    path('item/<uuid:item_id>/edit/', views.edit_item, name='edit_item'),
    path('item/<uuid:item_id>/delete/', views.delete_item, name='delete_item'),
    path('my-items/', views.my_items, name='my_items'),
    
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<uuid:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<uuid:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<uuid:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<uuid:order_id>/', views.payment, name='payment'),
    path('payment/success/<uuid:order_id>/', views.payment_success, name='payment_success'),
    path('order/confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('sold-items/', views.sold_items, name='sold_items'),
    path('order/<uuid:order_id>/delete/', views.delete_order, name='delete_order'),
]