import signal

from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from .models import Player, Game, PlayerRating
from .views import InvalidTeamsError, InvalidScoreError, InvalidDateEror, get_player_statistics

import datetime


#############
## HELPERS ##
#############

def create_player(name : str, rating : int = 400):
    user = User.objects.create_user(username=name, email="player@player.com", password=name[::-1])
    player = Player.objects.create(player_name=name, user=user)
    date = timezone.now() - datetime.timedelta(days=7)
    PlayerRating.objects.create(player=player, timestamp=date.date(), rating=rating)
    return player

def create_team() -> (list[Player], dict[str, int]):
    players = []
    context = {}
    for i in range(4):
            players.append(create_player("player"+str(i+1)))
            context[('winning' if i%2==0 else 'losing')+'_team'+'_'+('defense' if i<2 else 'attack')] = players[-1].id
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
                               team_2_score = 10 if winner_team==2 else 0,
                               date_played=date,
                               submitted_by=User.objects.all()[0])
    
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


class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise AssertionError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)


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
        all_players = Player.objects.all()
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['top_5_list'], [(player1, 0), (player2, 0)])
        self.assertContains(response, player1.player_name)
        self.assertContains(response, player2.player_name)
        
        
    def test_more_than_five_players(self):
        players = []
        for i in range(10):
            players.append(create_player(name="player"+str(i), rating=i*100))
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['top_5_list'],
                                 [(players[i], 0) for i in range(9, 4, -1)])
        
    def test_recent_games(self):
        # We want to only show the games that have not yet been used
        # to perform rating updates.
        
        create_game(1)
        players = Player.objects.all()
        create_game(1, *[players[i] for i in range(4)])
        game = Game.objects.get(pk=1)
        game.updates_performed = True
        game.save()
        
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['recent_games'], Game.objects.filter(pk=2))
        
    def test_pending_diff(self):
        create_game(1)
        players = Player.objects.all()
        expected_diffs = [16, 16, -16, -16]
        response = self.client.get(reverse('elo_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['top_5_list'], 
                                 [(players[i], expected_diffs[i]) for i in range(4)])
        
        
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
        self.assertQuerySetEqual(response.context['player_list'], [(player1, 0), (player2, 0)])
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
                                 list(zip(players[::-1], [0 for x in players])))
        
    def test_pending_diff(self):
        create_game(1)
        players = Player.objects.all()
        expected_diffs = [16, 16, -16, -16]
        response = self.client.get(reverse('elo_app:all'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['player_list'], 
                                 [(players[i], expected_diffs[i]) for i in range(4)])


class DetailTest(TestCase):

    def test_detail_view_no_player(self):
        response = self.client.get(reverse('elo_app:player_detail', args=(1,)))
        self.assertEqual(response.status_code, 404)
        

class SubmitFormGameTest(TestCase):

    def test_submit_form_no_players(self):
        response = self.client.get(reverse('elo_app:submit_form_game'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Winning team")
        self.assertContains(response, "Losing team")
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
        context['losing_team_score'] = 10
        login_user(self.client, User.objects.all()[0])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], str(InvalidScoreError(10, 10)))
    

    def test_submit_game_future_date(self):
        context = create_team()[1]
        context['date'] = timezone.now().date() + datetime.timedelta(days=1)
        context['losing_team_score'] = 5
        login_user(self.client, User.objects.all()[0])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], str(InvalidDateEror()))
        

    def test_submit_game_invalid_team(self):
        context = create_team()[1]
        context['date'] = timezone.now()
        context['losing_team_score'] = 7
        #Making teams invalid
        context['winning_team_defense'] = context['losing_team_defense']
        login_user(self.client, User.objects.all()[3])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 
                                 str(InvalidTeamsError(Player.objects.get(pk=context['winning_team_defense']).player_name)))
        

    def test_submit_game_invalid_team_v2(self):
        context = create_team()[1]
        context['date'] = timezone.now()
        context['losing_team_score'] = 7
        #Making teams invalid
        context['winning_team_defense'] = context['losing_team_attack']
        login_user(self.client, User.objects.all()[3])
        response = self.client.post(reverse('elo_app:submit_game'), context)
        
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['error_message'], 
                                 str(InvalidTeamsError(Player.objects.get(pk=context['winning_team_defense']).player_name)))
        
    
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
        context['losing_team_score'] = 5
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
        context['losing_team_score'] = 5
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
            self.assertEqual(len(player_ratings), 1)
            
    def test_update_ratings_no_games_played(self):
        # If a player has played no games since the last update,
        # we should still insert a rating in the PlayerRatings
        # table equal to the last rating.
        
        players, context = create_team()
        create_and_login_superuser(self.client)
        self.client.post(reverse('elo_app:update_ratings'))
        for i in range(4):
            ratings = PlayerRating.objects.filter(player=players[i])
            self.assertEqual(len(ratings), 2)
            self.assertEqual(ratings[0].rating, ratings[1].rating)
            
    def test_submit_game_and_update_ratings_no_superuser(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        response = self.client.post(reverse('elo_app:submit_game'), context)
        self.assertEqual(response.status_code, 302)
        games = Game.objects.all()
        self.assertEqual(len(games), 0)
            
    
    def test_submit_game_and_update_ratings_equal_elos(self):
        players, context = create_team()
        context['date'] = timezone.now().date()
        context['losing_team_score'] = 5
        admin = create_and_login_superuser(self.client)
        
        self.client.post(reverse('elo_app:submit_game'), context)
        self.client.post(reverse('elo_app:update_ratings'))
        
        
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            player_ratings = player.playerrating_set.all()
            
            self.assertEqual(len(player_ratings), 2)
            self.assertEqual(player_ratings[1].player, player)
            self.assertEqual(player_ratings[1].timestamp, timezone.now().date())
            self.assertEqual(player_ratings[1].rating, 
                             400+16 if i%2==0 else 400-16)
            self.assertEqual(player.get_rating(),
                             400+16 if i%2==0 else 400-16)
            
            
    def test_submit_game_and_update_players_different_elos(self):
        players, context = create_team()
        for i in range(3):
            rating = players[i].playerrating_set.all()
            self.assertEqual(len(rating), 1)
            rating[0].rating = 250 + i*50
            rating[0].save()
        
        admin = create_and_login_superuser(self.client)
        context['date'] = timezone.now().date()
        context['losing_team_score'] = 5
        self.client.post(reverse('elo_app:submit_game'), context)
        self.client.post(reverse('elo_app:update_ratings'))
        
        expected_ratings = [268, 282, 368, 382]
        
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            player_ratings = player.playerrating_set.all()
            
            self.assertEqual(len(player_ratings), 2)
            self.assertEqual(player_ratings[1].player, player)
            self.assertEqual(player_ratings[1].timestamp, timezone.now().date())
            self.assertEqual(player_ratings[1].rating, expected_ratings[i])
            
            self.assertEqual(player.get_rating(), expected_ratings[i])
            
        
    def test_player_rating_cannot_drop_below_100(self):
        players, context = create_team()
        for i in range(4):
            rating = players[i].playerrating_set.all()
            self.assertEqual(len(rating), 1)
            rating[0].rating = 100
            rating[0].save()
            
        admin = create_and_login_superuser(self.client)
        context['date'] = timezone.now().date()
        context['team_1_score'] = 10
        context['team_2_score'] = 5
        self.client.post(reverse('elo_app:submit_game'), context)
        self.client.post(reverse('elo_app:update_ratings'))
        
        for i in range(4):
            player = Player.objects.get(pk=players[i].id)
            player_ratings = player.playerrating_set.all()
            self.assertEqual(len(player_ratings), 2)
            self.assertGreaterEqual(player.get_rating(), 100)
            
    def test_inactivity_penalty(self):
        players, context = create_team()
        for i in range(3):
            player_rating_set = players[i].playerrating_set.all()
            rating = player_rating_set[0]
            rating.rating = 250 + i*50
            rating.save()
        
        create_game(1, players[0], players[0], players[1], players[1])
        
        create_and_login_superuser(self.client)
        self.client.post(reverse('elo_app:update_ratings'))
        self.assertEqual(players[0].get_rating(), 250+36+2)
        self.assertEqual(players[1].get_rating(), 300-36+2)
        self.assertEqual(players[2].get_rating(), 350-2)
        self.assertEqual(players[3].get_rating(), 400-2)
                
    def test_inactivity_penalty_cannot_exceed_neg_25(self):
        for i in range(0, 40, 4):
            players = [create_player(name=f'player_{i+j}') for j in range(4)]
            create_game(1, *players)
        inactive_player = create_player(name='inactive_player', rating=800)
        create_and_login_superuser(self.client)
        self.client.post(reverse('elo_app:update_ratings'))
        self.assertEqual(inactive_player.get_rating(), 800-25)
        

class TestDBPerformance(TestCase):
    """
    Many of the views, in particular the PlayerDetailView, appear to become very slow or completely halt 
    somewhere during execution as soon as the database contains more than a few rows.
    For example `get_player_statistics` queries all games played by some Player,
    and the default sqlite database can't appear to handle these queries as only the query for the first game
    ever resolves. This test reproduces this behaviour by creating some players and then creating games and updating
    ratings some number of weeks back in time. All parts of the code which result in some database operation(s) are run within
    a `timeout` wrapper to ensure that an AssertionError is raised if the operation(s) take too long.
    
    With num_weeks = 5 the test passes with the default sqlite database, but with num_weeks = 6 the execution times out at
    one of the `get_player_statistics` calls.
    """
    
    def test_db_performance(self):
        players = [create_player(name="player"+str(i), rating=400+i*50) for i in range(7)]
        player_idx = 0
        create_and_login_superuser(self.client)
        num_weeks = 6
        for i in range(num_weeks):
            
            for j in range(5):
                players_for_game = []
                for _ in range(4):
                    players_for_game.append(players[player_idx])
                    player_idx = (player_idx + 1) % len(players)
                with timeout(seconds=1):
                    create_game(j % 2 + 1, *players_for_game, timezone.now().date() - datetime.timedelta(weeks=num_weeks-1-i, days=j))
            
            with timeout(seconds=1):
                self.client.post(reverse('elo_app:update_ratings'))

            recent_ratings = PlayerRating.objects.filter(timestamp=timezone.now().date())
            with timeout(seconds=1):
                for rating in recent_ratings:
                    rating.timestamp -= datetime.timedelta(weeks=num_weeks-1-i)
                    rating.save()
                
        for p in players:
            with timeout(seconds=5):
                get_player_statistics(p)
            