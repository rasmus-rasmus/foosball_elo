from django.test import TestCase
from django.urls import reverse
from .models import Player, Game
import datetime
from django.utils import timezone


#############
## HELPERS ##
#############

def create_player(name : str, rating : int = 400):
    return Player.objects.create(player_name=name, elo_rating=rating)

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
        response = self.client.get(reverse('elo_app:submit_game'))
        self.assertEqual(response.status_code, 405)
    
    def test_submit_game_no_players(self):
        response = self.client.post(reverse('elo_app:submit_game'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Please fill out all fields')
        self.assertContains(response, 'Please fill out all fields')
        
    def test_submit_game_two_players(self):
        player1 = create_player("player1")
        player2 = create_player("player2")
        context = {'team_1_defense': player1.id, 'team_2_defense': player2.id}
        response = self.client.post(reverse('elo_app:submit_game'), context)        
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Please fill out all fields')
        
    def test_submit_game_valid_team_no_date(self):
        context = create_team()[1]
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 'Please fill out all fields')
        
    def test_submit_game_valid_team_invalid_score(self):
        context = create_team()[1]
        context['date'] = timezone.now().date()
        context['team_1_score'] = 5
        context['team_2_score'] = 7
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], "Indecisive scores: ({}, {}).".format(5, 7))
        
    def test_submit_game_invalid_team(self):
        context = create_team()[1]
        context['date'] = timezone.now()
        context['team_1_score'] = 7
        context['team_2_score'] = 10
        #Making teams invalid
        context['team_1_defense'] = context['team_2_defense']
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 
                                 "Invalid teams: {} plays on both teams".format(Player.objects.get(pk=context['team_1_defense'])))
        
    def test_submit_game_invalid_team_v2(self):
        context = create_team()[1]
        context['date'] = timezone.now()
        context['team_1_score'] = 7
        context['team_2_score'] = 10
        #Making teams invalid
        context['team_1_defense'] = context['team_2_attack']
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 
                                 "Invalid teams: {} plays on both teams".format(Player.objects.get(pk=context['team_1_defense'])))
        
    def test_submit_valid_game(self):
        context = create_team()[1]
        context['date'] = timezone.now().date()
        context['team_1_score'] = 5
        context['team_2_score'] = 10
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 302)
        
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
        
    def test_submit_game_db_update_players_equal_elos(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        self.client.post(reverse('elo_app:submit_game'), context)
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            self.assertEqual(player.number_of_games_played, 1)
            self.assertEqual(player.opponent_average_rating, 400)
            self.assertEqual(player.elo_rating,
                             400+16 if i%2==0 else 400-16)
        
        
        

        