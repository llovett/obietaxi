from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from taxi import views

urlpatterns = patterns('',
                       url( r'^$', views.request_or_offer_ride, name="main_page" ),
                       url( r'^offer/new/$', views.offer_new, name="offer_ride_new" ),
                       url( r'^request/new/$', views.request_new, name="request_ride_new" ),
                       url( r'^request/search/$', views.request_search, name="request_search" ),
                       url( r'^request/show/$', views.request_show, name="request_show" ),
                       url( r'^browse/$', views.browse, name="browse" ),
                       url( r'^accounts/', include( 'mongologin.urls' ) ),
)
