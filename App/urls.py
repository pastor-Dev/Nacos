from django.urls import path
from . import views

urlpatterns = [
    path('', views.signin_view, name='signin'),           # Landing page (login)
    path('signup/', views.signup_view, name='signup'),    # Registration
    path('dashboard/', views.dashboard, name='dashboard'),# Dashboard
    path('logout/', views.logout_view, name='logout'),
    path('payment_page/', views.payment_view, name='payment_page'),
    path('dashboard/', views.dashboard, name='dashboard'),  # example
    path('logout/', views.logout_view, name='logout'),

]
