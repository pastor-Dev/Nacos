from django.urls import path
from . import views

urlpatterns = [
    # Payment pages
    path('payment/', views.payment_page, name='payment_page'),
    path('payment/initialize/', views.initialize_payment, name='initialize_payment'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    path('payment/history/', views.payment_history, name='payment_history'),
    
    # Webhook
    path('payment/webhook/', views.paystack_webhook, name='paystack_webhook'),
]