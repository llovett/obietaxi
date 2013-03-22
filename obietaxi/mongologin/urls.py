from django.conf.urls import patterns, include, url
import views
from taxi import views as taxi_views

urlpatterns = patterns(
    '',
    url( r'^login/$', views.login_view, name="login" ),
    url( r'^google/success/$', views.google_login_success, name="google_login_success" ),
    url( r'^google/register/$', views.google_register, name="google_register" ),
    url( r'^profile/(?P<user_id>[a-z0-9]+)/$', taxi_views.userprofile_show, name="user_home" ),
    url( r'^home/$', taxi_views.user_landing, name="user_landing" ),

    url( r'^logout/$', views.user_logout, name="logout" ),
    url( r'^register/$', views.register, name="register" ),
    url( r'^activate/$', views.activate, name="activate" ),
    url( r'^password/forget/$', views.forgot_password, name="forgot_password" ),
    url( r'^password/reset/$', views.reset_password, name="reset_password" ),
)
