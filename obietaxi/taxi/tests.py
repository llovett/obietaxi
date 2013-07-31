"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from mongorunner import TestCase
from mongoengine.django.auth import User
from django.test.client import RequestFactory, Client
from taxi import views
from taxi import models
from datetime import datetime, timedelta

# Some users to play with
#       fname           lname           email                   phone
joe =   ("Joe",         "Schmo",        "jschm@obietaxi.com",   "1231231234")
alex =  ("Alex",        "Tarzen",       "atz@obietaxi.com",     "2342342345")
bud =   ("Buddy",       "Jody",         "bjod@obietaxi.com",    "3453453456")

# Some locations
#       name                            lat                     lng
iga =   ("IGA",                         41.293209,              -82.20551899999998)
walmart = ("Walmart",                   41.266583,              -82.223344)
cvs =   ("CVS Pharmacy",                41.2847,                -82.21809999999999)
airport = ("Cleveland Airport",         41.410339,              -81.83616699999999)

def create_user(user_tup):
    '''Boilerplate for making a new user with a profile'''
    user = User.create_user(user_tup[2], "password")
    user.first_name = user_tup[0]
    user.last_name = user_tup[1]
    user.is_active = True
    user.save()
    profile = models.UserProfile.objects.create(phone_number=user_tup[3], user=user)
    return user, profile

def delete_user(user, profile):
    user.delete()
    profile.delete()

def create_location(loc_tup):
    '''Boilerplace for creating a Location'''
    return models.Location(position=(loc_tup[1], loc_tup[2]), title=loc_tup[0])

def create_request(from_place, to_place, requester, **kwargs):
    '''Boilerplace for a creating a riderequest'''
    u = User.objects.get(username=requester[2])
    p = models.UserProfile.objects.get(user=u)
    l1 = create_location(from_place)
    l2 = create_location(to_place)
    msg = "I would like a ride from %s to %s, please."%(str(l1), str(l2))
    if 'message' in kwargs:
        msg = kwargs.get('message')
        del kwargs['message']
    date = datetime.now() + timedelta(days=1)
    if 'date' in kwargs:
        date = kwargs.get('date')
        del kwargs['date']
    req = models.RideRequest.objects.create(passenger=p, start=l1, end=l2, message=msg, date=date)
    p.requests.append(req)
    p.save()
    return req

def create_offer(from_place, to_place, offerer, **kwargs):
    '''Boilerplace for a creating a rideoffer'''
    u = User.objects.get(username=offerer[2])
    p = models.UserProfile.objects.get(user=u)
    l1 = create_location(from_place)
    l2 = create_location(to_place)
    msg = "I am offering a ride from %s to %s. Any takers?"%(str(l1), str(l2))
    if 'message' in kwargs:
        msg = kwargs.get('message')
        del kwargs['message']
    date = datetime.now() + timedelta(days=1)
    if 'date' in kwargs:
        date = kwargs.get('date')
        del kwargs['date']
    off = models.RideOffer.objects.create(driver=p, start=l1, end=l2, message=msg, date=date, **kwargs)
    p.offers.append(off)
    p.save()
    return off

class BrowseAllTest(TestCase):
    '''Tests for browse page functionality'''

    def setUp(self):
        self.client = Client()
        self.fixtures = []
        for user in (joe, alex, bud):
            user, profile = create_user(user)
            self.fixtures.extend([user, profile])

    def tearDown(self):
        for f in self.fixtures:
            f.delete()

    def test_all_listings(self):
        '''Tests that all offers and requests show up'''
        response = self.client.get("/browse/")
        test_listings = set(list(response.context["ride_requests"]) + list(response.context["ride_offers"]))
        self.assertEqual(len(test_listings), 0)

        self.fixtures.append(create_request(iga, walmart, joe))
        self.fixtures.append(create_request(cvs, airport, joe))
        self.fixtures.append(create_request(airport, iga, bud))
        self.fixtures.append(create_request(walmart, airport, alex))
        self.fixtures.append(create_offer(walmart, iga, alex))
        self.fixtures.append(create_offer(walmart, cvs, bud))

        response = self.client.get("/browse/")
        test_listings = set(list(response.context["ride_requests"]) + list(response.context["ride_offers"]))
        self.assertEqual(len(response.context["ride_requests"]), 4)
        self.assertEqual(len(response.context["ride_offers"]), 2)

class SearchTest(TestCase):
    '''Tests search functionalities'''

    def setUp(self):
        self.client = Client()
        self.fixtures = []
        for user in (joe, alex, bud):
            user, profile = create_user(user)
            self.fixtures.extend([user, profile])

    def tearDown(self):
        for f in self.fixtures:
            f.delete()

    def test_search_offer(self):
        tomorrow = datetime.now() + timedelta(days=1)
        offer = create_offer(walmart, iga, alex, date=tomorrow)
        postdata = {'start_lat':walmart[1], 'start_lng':walmart[2],
                    'start_location':walmart[0],
                    'end_lat':iga[1], 'end_lng':iga[2],
                    'end_location':iga[0],
                    'date_0':tomorrow.strftime("%m/%d/%Y"),
                    'date_1':tomorrow.strftime("%I:%M %p"),
                    'fuzziness':'anytime'}
        response = self.client.post("/offer/search/browse/", postdata)

        self.assertEqual(len(response.context["ride_offers"]), 1, msg="Did not find an offer result")
        self.assertEqual(response.context["ride_offers"][0], offer, msg="Offer result did not match")
