"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from mongorunner import TestCase
from django.test.client import RequestFactory, Client
from taxi import views
from taxi import models
from datetime import datetime

class BrowseTest(TestCase):
    def _fixture_setup(self):
        pass
    def _fixture_teardown(self):
        pass

    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def test_all_listings(self):
        ride_requests = list(models.RideRequest.objects.filter( date__gte=datetime.now(), ride_offer=None ))
        ride_offers = list(models.RideOffer.objects.filter( date__gte=datetime.now() ))
        all_listings = set(ride_requests + ride_offers)
        response = self.client.get("/browse/")
        test_listings = set(list(response.context["ride_requests"]) + list(response.context["ride_requests"]))
        self.assertEqual(test_listings, all_listings)
