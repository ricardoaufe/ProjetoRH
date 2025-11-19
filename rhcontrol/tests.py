from django.test import TestCase
from django.urls import reverse

class RhcontrolTests(TestCase):
    def test_rh_dashboard_url_is_corret(self):
        dashboard_url = reverse('rhcontrol:rh_home')
        self.assertEqual(dashboard_url, '/')

        