from django.conf.urls import patterns, include, url
import views

urlpatterns = patterns('',
                       url( r'^$', views.user_show, name="main_page" ),
                       url( r'^login/$', views.login_view, name="login" ),
                       url( r'^google/success/$', views.google_login_success, name="google_login_success" ),
                       url( r'^profile/$', views.user_show, name="login_success" ),
                       url( r'^logout/$', views.user_logout, name="logout" ),
                       url( r'^register/$', views.register, name="register" ),
                       url( r'^activate/$', views.activate, name="activate" ),
)
