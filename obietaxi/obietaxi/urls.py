from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from taxi import views

urlpatterns = patterns('',
                       url( r'^$', direct_to_template, { 'template':'index.html' } ),
                       url( r'^/trip/new/$', views.new_trip, name="trip_new" ),
                       url( r'^/browse/$', views.list_trips, name="trip_list" ),
)
