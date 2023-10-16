from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from .models import Player, Game, PlayerRating
from .views import InvalidTeamsError, InvalidScoreError, InvalidDateEror

import datetime


#############
## HELPERS ##
#############

def create_player(name : str, rating : int = 400):
    user = User.objects.create_user(username=name, email="player@player.com", password=name[::-1])
    return Player.objects.create(player_name=name, elo_rating=rating, user=user)

def create_team() -> (list[Player], dict[str, int]):
    players = []
    context = {}
    for i in range(4):
            players.append(create_player("player"+str(i+1)))
            context['team_'+str(i%2+1)+'_'+('defense' if i<2 else 'attack')] = players[-1].id
    return players, context
    

def create_game(winner_team : int,
                player_1 : Player = None,
                player_2 : Player = None,
                player_3 : Player = None,
                player_4 : Player = None,
                date : datetime.date = timezone.now().date()):
    return Game.objects.create(team_1_defense=player_1 if player_1!=None else create_player("player_1"),
                               team_1_attack=player_2 if player_2!=None else create_player("player_2"),
                               team_2_defense=player_3 if player_3!=None else create_player("player_3"),
                               team_2_attack=player_4 if player_4!=None else create_player("player_4"),
                               team_1_score = 10 if winner_team==1 else 0,
                               team_2_score = 10 if winner_team==0 else 10,
                               date_played=date)
    
def create_and_login_user(client) -> User:
    user = User.objects.create_user(username='user', email='user@user.com', password='resu')
    client.login(username='user', password='resu')
    return user

def login_user(client, user: User) -> bool:
    return client.login(username=user.username, password=user.username[::-1])

def create_and_login_superuser(client) -> User:
    user = User.objects.create_superuser(username='admin', email='admin@admin.com', password='nimda')
    client.login(username='admin', password='nimda')
    return user


###########
## TESTS ##
###########
class IndexTest(TestCase):
        
    def test_one_player(self):
        player = create_player("player")
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, player.player_name)
        
        
    def test_two_players(self):
        player1 = create_player("player1")
        player2= create_player("player2", 200)
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['top_5_list'], [player1, player2])
        self.assertContains(response, player1.player_name)
        self.assertContains(response, player2.player_name)
        
        
    def test_more_than_five_players(self):
        players = []
        for i in range(10):
            players.append(create_player(name="player"+str(i), rating=i*100))
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['top_5_list'],
                                 [players[i] for i in range(9, 4, -1)])
        
        
class AllViewTest(TestCase):
    
    def test_one_player(self):
        player = create_player("player")
        response = self.client.get(reverse('elo_app:all'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, player.player_name)
        
        
    def test_two_players(self):
        player2= create_player("player2", 200)
        player1 = create_player("player1")
        response = self.client.get(reverse('elo_app:all'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['player_list'], [player1, player2])
        self.assertContains(response, player1.player_name)
        self.assertContains(response, player2.player_name)
        
        
    def test_ten_players(self):
        players = []
        character_postfixes = "ABCDEFGHIJ"[::-1]
        for i in range(10):
            players.append(create_player(name="player"+character_postfixes[i], rating=i*100))
        response = self.client.get(reverse('elo_app:all'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['player_list'],
                                 players[::-1])


class DetailTest(TestCase):

    def test_detail_view_no_player(self):
        response = self.client.get(reverse('elo_app:player_detail', args=(1,)))
        self.assertEqual(response.status_code, 404)
        

class SubmitFormGameTest(TestCase):

    def test_submit_form_no_players(self):
        response = self.client.get(reverse('elo_app:submit_form_game'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team 1")
        self.assertContains(response, "Team 2")
        self.assertQuerySetEqual(response.context['all_players_list'], [])
    
        
    def test_submit_form_two_players(self):
        playerB = create_player("playerB")
        playerA = create_player("playerA")
        response = self.client.get(reverse('elo_app:submit_form_game'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['all_players_list'], [playerA, playerB])
        

class SubmitGameTest(TestCase):

    def test_submit_game_get_method(self):
        create_and_login_user(self.client)
        response = self.client.get(reverse('elo_app:submit_game'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['error_message'], 'Something went wrong. Please try again')
    

    def test_submit_game_no_players(self):
        user = create_and_login_user(self.client)
        response = self.client.post(reverse('elo_app:submit_game'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Please fill out all fields')
        self.assertContains(response, 'Please fill out all fields')
        

    def test_submit_game_two_players(self):
        player1 = create_player("player1")
        player2 = create_player("player2")
        context = {'team_1_defense': player1.id, 'team_2_defense': player2.id}
        login_user(self.client, User.objects.all()[0])
        response = self.client.post(reverse('elo_app:submit_game'), context)        
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Please fill out all fields')
        

    def test_submit_game_valid_team_no_date(self):
        context = create_team()[1]
        login_user(self.client, User.objects.all()[0])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Please fill out all fields')
        

    def test_submit_game_valid_team_invalid_score(self):
        context = create_team()[1]
        context['date'] = timezone.now().date()
        context['team_1_score'] = 5
        context['team_2_score'] = 7
        login_user(self.client, User.objects.all()[0])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], str(InvalidScoreError(5, 7)))
    

    def test_submit_game_future_date(self):
        context = create_team()[1]
        context['date'] = timezone.now().date() + datetime.timedelta(days=1)
        context['team_1_score'] = 5
        context['team_2_score'] = 10
        login_user(self.client, User.objects.all()[0])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], str(InvalidDateEror()))
        

    def test_submit_game_invalid_team(self):
        context = create_team()[1]
        context['date'] = timezone.now()
        context['team_1_score'] = 7
        context['team_2_score'] = 10
        #Making teams invalid
        context['team_1_defense'] = context['team_2_defense']
        login_user(self.client, User.objects.all()[3])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 
                                 str(InvalidTeamsError(Player.objects.get(pk=context['team_1_defense']).player_name)))
        

    def test_submit_game_invalid_team_v2(self):
        context = create_team()[1]
        context['date'] = timezone.now()
        context['team_1_score'] = 7
        context['team_2_score'] = 10
        #Making teams invalid
        context['team_1_defense'] = context['team_2_attack']
        login_user(self.client, User.objects.all()[3])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 
                                 str(InvalidTeamsError(Player.objects.get(pk=context['team_1_defense']).player_name)))
        
    
    def test_submit_invalid_game_no_login(self):
        context = create_team()[1]
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 302)
        loc = response.get('Location')
        self.assertEqual(loc, reverse('registration:login') + '?next=' + reverse('elo_app:submit_game'))
        
        
    def test_submit_valid_game_no_login(self):
        context = create_team()[1]
        context['date'] = timezone.now().date()
        context['team_1_score'] = 5
        context['team_2_score'] = 10
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 302)
        loc = response.get('Location')
        self.assertEqual(loc, reverse('registration:login') + '?next=' + reverse('elo_app:submit_game'))


    def test_submit_valid_game(self):
        context = create_team()[1]
        context['date'] = timezone.now().date()
        context['team_1_score'] = 5
        context['team_2_score'] = 10
        login_user(self.client, User.objects.all()[0])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 302)
        loc = response.get('Location')
        self.assertEqual(loc, reverse('elo_app:index'))
        

    def test_submit_valid_game_reverse_score(self):
        context = create_team()[1]
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 302)
        

    def test_submit_game_db_create_game(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        login_user(self.client, User.objects.all()[0])
        self.client.post(reverse('elo_app:submit_game'), context)
        
        game = Game.objects.all()[0]
        self.assertEqual(game.winner(), 1)
        self.assertEqual(game.team_1_defense, players[0])
        self.assertEqual(game.team_2_defense, players[1])
        self.assertEqual(game.team_1_attack, players[2])
        self.assertEqual(game.team_2_attack, players[3])
        self.assertEqual(game.team_1_score, 10)
        self.assertEqual(game.team_2_score, 5)
        self.assertEqual(game.date_played, timezone.now().date())
        
    
    

        
class TestUpdateScores(TestCase):
    
    def test_submit_game_no_update(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        
        admin = create_and_login_superuser(self.client)
        self.client.post(reverse('elo_app:submit_game'), context)

        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            player_ratings = player.playerrating_set.all()
            self.assertEqual(len(player_ratings), 0)
            self.assertEqual(player.number_of_games_played, 1)
            self.assertEqual(player.opponent_average_rating, 400)
            self.assertEqual(player.elo_rating, 400)
            
            
    def test_submit_game_update_ratings_no_superuser(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 302)
        games = Game.objects.all()
        self.assertEqual(len(games), 0)
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            self.assertEqual(player.number_of_games_played, 0)
            self.assertEqual(player.opponent_average_rating, 0)
            self.assertEqual(player.elo_rating, 400)
            
    
    def test_submit_game_and_update_ratings_equal_elos(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        admin = create_and_login_superuser(self.client)
        
        self.client.post(reverse('elo_app:submit_game'), context)
        self.client.post(reverse('elo_app:update_ratings'))
        
        
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            player_ratings = player.playerrating_set.all()
            
            self.assertEqual(len(player_ratings), 1)
            self.assertEqual(player_ratings[0].player, player)
            self.assertEqual(player_ratings[0].timestamp, timezone.now().date())
            self.assertEqual(player_ratings[0].rating, 
                             400+16 if i%2==0 else 400-16)
            
            self.assertEqual(player.number_of_games_played, 1)
            self.assertEqual(player.opponent_average_rating, 400)
            self.assertEqual(player.elo_rating,
                             400+16 if i%2==0 else 400-16)
            
            
    def test_submit_game_and_update_players_different_elos(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        players[0].elo_rating = 250
        players[1].elo_rating = 300
        players[2].elo_rating = 350
        for i in range(3):
            players[i].save()
        admin = create_and_login_superuser(self.client)
        
        self.client.post(reverse('elo_app:submit_game'), context)
        self.client.post(reverse('elo_app:update_ratings'))
        
        expected_ratings = [268, 282, 368, 382]
        expected_av_ratings = [350, 300, 350, 300]
        
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            player_ratings = player.playerrating_set.all()
            
            self.assertEqual(len(player_ratings), 1)
            self.assertEqual(player_ratings[0].player, player)
            self.assertEqual(player_ratings[0].timestamp, timezone.now().date())
            self.assertEqual(player_ratings[0].rating, expected_ratings[i])
            
            self.assertEqual(player.number_of_games_played, 1)
            self.assertEqual(player.opponent_average_rating, expected_av_ratings[i])
            self.assertEqual(player.elo_rating, expected_ratings[i])
            
        
    def test_player_rating_cannot_drop_below_100(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        for i in range(4):
            players[i].elo_rating = 100
            players[i].save()
        admin = create_and_login_superuser(self.client)
        
        self.client.post(reverse('elo_app:submit_game'), context)
        self.client.post(reverse('elo_app:update_ratings'))
        
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            player_ratings = player.playerrating_set.all()
            self.assertEqual(len(player_ratings), 1)
            self.assertGreaterEqual(player.elo_rating, 100)
