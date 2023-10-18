from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from elo.models import Player, PlayerRating

from datetime import timedelta

def create_player(name : str, rating : int = 400):
    user = User.objects.create_user(username=name, email="player@player.com", password=name[::-1])
    return Player.objects.create(player_name=name, elo_rating=rating, user=user)

class SubmitFormPlayerTest(TestCase):
    def test_submit_player_form(self):
        response = self.client.get(reverse('registration:submit_form_player'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign up!")
        self.assertContains(response, "Back to home page")


class SubmitPlayerTest(TestCase):
    def test_submit_player_get_method(self):
        response = self.client.get(reverse('registration:submit_player'))
        self.assertEqual(response.status_code, 405)
    

    def test_submit_player_username_field_blank(self):
        response = self.client.post(reverse('registration:submit_player'), data={'player_name': ''})
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 
                                 'Please provide a non-empty username using only upper case, lower case, numbers and underscore.')
        

    def test_submit_player_invalid_character(self):
        response1 = self.client.post(reverse('registration:submit_player'), data={'player_name': '@lexander'})
        response2 = self.client.post(reverse('registration:submit_player'), data={'player_name': 'l&mpersand'})
        response3 = self.client.post(reverse('registration:submit_player'), data={'player_name': '$uperhero'})
        for response in (response1, response2, response3):
            self.assertEqual(response.status_code, 200)
            self.assertQuerySetEqual(response.context['error_message'], 
                                 'Please provide a non-empty username using only upper case, lower case, numbers and underscore.')
        

    def test_submit_player_username_already_in_use(self):
        create_player('player1')
        form_data = {'player_name': 'player1', 'email': 'player1@player1.com', 'password': '1reyalp'}
        response = self.client.post(reverse('registration:submit_player'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Username already in use.') 
        

    def test_submit_player_no_context(self):
        response = self.client.post(reverse('registration:submit_player'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Please fill out all fields')
        
        
    def test_submit_player_player_in_db(self):
        form_data = {'player_name': 'player1', 'email': 'player1@player1.com', 'password': '1reyalp'}
        response = self.client.post(reverse('registration:submit_player'), data=form_data)          
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Player.objects.all()), 1)
        player=Player.objects.get(player_name='player1')
        self.assertEqual(player.elo_rating, 400)
        self.assertEqual(player.opponent_average_rating, 0)
        self.assertEqual(player.number_of_games_played, 0)
        

    def test_submit_initial_playerrating_in_db(self):
        form_data = {'player_name': 'player1', 'email': 'player1@player1.com', 'password': '1reyalp'}
        response = self.client.post(reverse('registration:submit_player'), data=form_data)        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(PlayerRating.objects.all()), 1)
        player=Player.objects.get(player_name='player1')
        rating = PlayerRating.objects.get(player=player)
        last_sunday = timezone.now().date()
        while last_sunday.weekday() != 6:
            last_sunday -= timedelta(days=1)
        self.assertEqual(rating.player.player_name, 'player1')
        self.assertEqual(rating.timestamp, last_sunday)
        self.assertEqual(rating.rating, 400)
        
    #TODO: Test invalid e-mail
    #TODO: Test e-mail already in use
    


