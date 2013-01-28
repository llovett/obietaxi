from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from taxi import views

urlpatterns = patterns('',
                       url( r'^$', views.request_or_offer_ride, name="main_page" ),

                       url( r'^offer/new/$', views.offer_new, name="offer_ride_new" ),
                       url( r'^offer/search/$', views.offer_search, name="offer_search" ),
                       url( r'^offer/show/$', views.offer_show, name="offer_show" ),
                       url( r'^offer/propose/$', views.offer_propose, name="offer_propose" ),
                       url( r'^offer/proposal/$', views.process_offer_proposal, name="process_offer_proposal" ),
                       url( r'^offer/options/(?P<offer_id>[a-z0-9]+)/$', views.process_offer_update, name="offer_options" ),

                       url( r'^request/options/(?P<request_id>[a-z0-9]+)/$', views.process_request_update, name="request_options" ),
                       url( r'^request/propose/$', views.request_propose, name="request_propose" ),
                       url( r'^request/proposal/$', views.process_request_proposal, name="process_request_proposal" ),
                       url( r'^request/new/$', views.request_new, name="request_ride_new" ),
                       url( r'^request/search/$', views.request_search, name="request_search" ),
                       url( r'^request/show/$', views.request_show, name="request_show" ),

                       url( r'^browse/$', views.browse, name="browse" ),
                       url( r'^accounts/', include( 'mongologin.urls' ) ),
)

