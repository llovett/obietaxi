from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from taxi import views

urlpatterns = patterns('',
                       url( r'^$', direct_to_template, { 'template':'index.html' } ),
                       url( r'^/request/ride/new$', views.request_ride_new, name="request_ride_new" ),
                       url( r'^/request/show$', views.request_show, name="request_show" ),
)
