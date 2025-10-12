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
    path('elearning/', views.elearning_home, name='elearning_home'),
    path('elearning/schedule/', views.class_schedule, name='class_schedule'),
    path('elearning/class/<int:class_id>/join/', views.join_class, name='join_class'),
    path('elearning/resources/', views.resource_library, name='resource_library'),
    path('elearning/resource/<int:resource_id>/', views.resource_detail, name='resource_detail'),
    path('elearning/resource/<int:resource_id>/download/', views.download_resource, name='download_resource'),
    path('elearning/my-downloads/', views.my_downloads, name='my_downloads'),
    path('elearning/course/<int:course_id>/', views.course_resources, name='course_resources'),

]
