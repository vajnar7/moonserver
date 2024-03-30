from django.test import TestCase
from rest_framework.test import APIClient

from telescope.status_state_machine import StatusStateMachine


class StateMachineTestCase(TestCase):
    sm = StatusStateMachine()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_state_machine(self):
        self.sm.start()


class ControlApiTestCase(TestCase):
    def setUp(self):
        self.api_client = APIClient()

    def test_get_status(self):
        # self.assertTrue(self.api_client.login(username="moon", password="moon"), "Cannot log in")
       response = self.api_client.get('/rest/open_door/', {}, format='json')


