from django.test import TestCase
from django.urls import reverse

# Create your tests here.
class IndexTest(TestCase):
    def test_index_view(self):
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        

class DetailTest(TestCase):
    def test_detail_view(self):
        response = self.client.get(reverse('elo_app:player_detail', args=(1,)))
        self.assertEqual(response.status_code, 200)
        

class SubmitGameTest(TestCase):
    def test_submit_game(self):
        response = self.client.get(reverse('elo_app:submit_game'))
        self.assertEqual(response.status_code, 200)