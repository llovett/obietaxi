from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from taxi import views

urlpatterns = patterns('',
                       url( r'^$', views.request_or_offer_ride, name="main_page" ),
                       url( r'^offer/new/$', views.offer_new, name="offer_ride_new" ),
                       url( r'^offer/show/$', views.offer_show, name="offer_show" ),
                       url( r'^request/propose/$', views.request_propose, name="request_propose" ),
                       url( r'^request/proposal/$', views.process_request_proposal, name="request_proposal" ),
                       url( r'^request/new/$', views.request_new, name="request_ride_new" ),
                       url( r'^request/search/$', views.request_search, name="request_search" ),
                       url( r'^request/show/$', views.request_show, name="request_show" ),
                       url( r'^offer/propose/$', views.offer_propose, name="offer_propose" ),
                       url( r'^offer/proposal/$', views.process_offer_proposal, name="process_offer_proposal" ),
                       url( r'^browse/$', views.browse, name="browse" ),
                       url( r'^accounts/', include( 'mongologin.urls' ) ),
)
