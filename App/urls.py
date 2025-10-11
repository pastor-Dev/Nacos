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
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/preferences/', views.edit_preferences, name='edit_preferences'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/delete-account/', views.delete_account, name='delete_account'),
    path('profile/activity/', views.activity_log, name='activity_log'),

]
