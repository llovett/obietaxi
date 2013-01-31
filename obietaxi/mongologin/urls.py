from django.conf.urls import patterns, include, url
import views
from taxi import views as taxi_views

urlpatterns = patterns('',
                       url( r'^login/$', views.login_view, name="login" ),
                       url( r'^google/success/$', views.google_login_success, name="google_login_success" ),
                       url( r'^profile/$', taxi_views.userprofile_show, name="user_home" ),
                       url( r'^logout/$', views.user_logout, name="logout" ),
                       url( r'^register/$', views.register, name="register" ),
                       url( r'^activate/$', views.activate, name="activate" ),
)
