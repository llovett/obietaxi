from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from taxi import views

urlpatterns = patterns(
    '',
    url( r'^$', views.request_or_offer_ride, name="main_page" ),

    url( r'^offer/new/$', views.offer_new, name="offer_ride_new" ),
    url( r'^offer/search/$', views.offer_search, name="offer_search" ),
    url( r'^offer/search/browse/$', views.offer_search_and_display, name="offer_search_and_display" ),
    url( r'^offer/show/(?P<offer_id>[a-z0-9]+)/$', views.offer_show, name="offer_show" ),
    url( r'^offer/propose/$', views.ask_for_ride, name="ask_for_ride" ),
    url( r'^offer/proposal/$', views.process_ask_for_ride, name="process_ask_for_ride" ),
    url( r'^offer/options/(?P<offer_id>[a-z0-9]+)/$', views.process_offer_update, name="offer_options" ),
    url( r'^offer/cancel/(?P<ride_id>[a-z0-9]+)/$', views.cancel_ride, name="cancel_offer"),
    url( r'^offer/feedback/$', views.driver_feedback, name="driver_feedback" ),

    url( r'^request/cancel/(?P<ride_id>[a-z0-9]+)/$', views.cancel_ride, name="cancel_request"),
    url( r'^request/options/(?P<request_id>[a-z0-9]+)/$', views.process_request_update, name="request_options" ),
    url( r'^request/propose/$', views.offer_ride, name="offer_ride" ),
    url( r'^request/proposal/$', views.process_offer_ride, name="process_offer_ride" ),
    url( r'^request/new/$', views.request_new, name="request_ride_new" ),
    url( r'^request/search/$', views.request_search, name="request_search" ),
    url( r'^request/search/browse/$', views.request_search_and_display, name="request_search_and_display" ),
    url( r'^request/show/(?P<request_id>[a-z0-9]+)/$', views.request_show, name="request_show" ),
    url( r'^request/feedback/(?P<request_id>[a-z0-9]+)/$', views.rider_feedback, name="ride_feedback" ),

    url( r'^browse/$', views.browse, name="browse" ),
    url( r'^accounts/', include( 'mongologin.urls' ) ),
)
