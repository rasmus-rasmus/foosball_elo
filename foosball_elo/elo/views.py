import decimal
from typing import Any
from django.db import models
from django.db.models.query import QuerySet
from django.db.utils import IntegrityError
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseNotAllowed
from django.views import View, generic
from django.urls import reverse
from django.utils import timezone
from .models import Player, Game, PlayerRating


#############
## HELPERS ##
#############

def update_player_stats(player : Player, opponent_rating : float, rating_diff : int = 0):
    player.opponent_average_rating *= player.number_of_games_played
    player.opponent_average_rating += decimal.Decimal(opponent_rating)
    player.number_of_games_played += 1
    player.opponent_average_rating /= player.number_of_games_played
    player.elo_rating = max(100, round(player.elo_rating + rating_diff))
    player.save()
    
def compute_rating_diff(team_rating : int, 
                        opponent_rating : int, 
                        victory : bool, 
                        scaling_factor : int = 400, 
                        adaption_step : int = 64) -> int:
    expected_outcome = 1 / (1 + 10**((opponent_rating - team_rating) / scaling_factor))
    return adaption_step * (int(victory) - expected_outcome)

def is_valid_score(score1 : int, score2 : int) -> bool:
    return (score1 == 10 and score2 < 10) or (score2 == 10 and score1 < 10)

def are_valid_teams(team_1_defense : Player, 
                    team_1_attack : Player, 
                    team_2_defense : Player, 
                    team_2_attack : Player, 
                    invalid_team_member : list[str]):
    if team_1_defense.player_name == team_2_defense.player_name \
        or team_1_defense.player_name == team_2_attack.player_name:
        invalid_team_member.append(team_1_defense.player_name)
        return False
    elif team_1_attack.player_name == team_2_defense.player_name \
        or team_1_attack.player_name == team_2_attack.player_name:
        invalid_team_member.append(team_1_attack.player_name)
        return False
    return True
    
class InvalidScoreError(Exception):
    def __init__(self, score1, score2):
        self.value = (score1, score2)
    
    def __str__(self):
        return "Indecisive scores: ({}, {}).".format(self.value[0], self.value[1])
                  
class InvalidTeamsError(Exception):
    def __init__(self, player_name : str):
        self.value = player_name
        
    def __str__(self):
        return "Invalid teams: {} plays on both teams".format(self.value)    


###########
## VIEWS ##
###########
class IndexView(generic.ListView):
    template_name = 'elo/index.html'
    context_object_name = 'top_5_list'
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['recent_games'] = Game.objects.order_by('-date_played')[:5]
        return context
    
    def get_queryset(self) -> QuerySet[Player]:
        return Player.objects.order_by('-elo_rating')[:5]
    
class AllView(generic.ListView):
    model = Player
    
    def get_queryset(self) -> QuerySet[Player]:
        return Player.objects.order_by('-elo_rating')
    
class SubmitGameView(generic.ListView):
    template_name = 'elo/submit_game_form.html'
    context_object_name = 'all_players_list'
    
    def get_queryset(self):
        return Player.objects.order_by('player_name')
    
class SubmitPlayerView(generic.TemplateView):
    template_name = 'elo/submit_player_form.html'
    
class PlayerDetailView(generic.DetailView):
    model = Player

    def get_queryset(self) -> QuerySet[Player]:
        return Player.objects.all()

def submit_game(request: HttpRequest):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    data = request.POST
    try:
        team_1_defense = Player.objects.get(pk=data['team_1_defense'])
        team_1_attack = Player.objects.get(pk=data['team_1_attack'])
        team_2_defense = Player.objects.get(pk=data['team_2_defense'])
        team_2_attack = Player.objects.get(pk=data['team_2_attack'])
        team_1_score = int(data['team_1_score'])
        team_2_score = int(data['team_2_score'])
        date = data['date']
        if not is_valid_score(team_1_score, team_2_score):
            raise InvalidScoreError(team_1_score, team_2_score)
        invalid_team_member = []
        if not are_valid_teams(team_1_defense, team_1_attack, team_2_defense, team_2_attack, invalid_team_member):
            raise InvalidTeamsError(invalid_team_member[0])
    except KeyError:
        return render(request, 'elo/submit_game_form.html', {
            'all_players_list': Player.objects.order_by('player_name'),
            'error_message': 'Please fill out all fields'
        })
    except InvalidScoreError as error:
        return render(request, 'elo/submit_game_form.html', {
            'all_players_list': Player.objects.order_by('player_name'),
            'error_message': str(error)
        })
    except InvalidTeamsError as error:
        return render(request, 'elo/submit_game_form.html', {
            'all_players_list': Player.objects.order_by('player_name'),
            'error_message': str(error)
        })
            
    game = Game.objects.create(team_1_defense=team_1_defense,
                               team_1_attack=team_1_attack,
                               team_2_defense=team_2_defense,
                               team_2_attack=team_2_attack,
                               team_1_score=team_1_score,
                               team_2_score=team_2_score,
                               date_played=date)
    
    team_1_av_rating = (team_1_defense.elo_rating + team_1_attack.elo_rating) / 2
    team_2_av_rating = (team_2_defense.elo_rating + team_2_attack.elo_rating) / 2
    
    team_1_rating_diff = compute_rating_diff(team_1_av_rating, 
                                             team_2_av_rating, 
                                             game.winner() == 1)
    team_2_rating_diff = compute_rating_diff(team_2_av_rating,
                                             team_1_av_rating,
                                             game.winner() == 2)
    
    update_player_stats(team_1_defense, team_2_av_rating, team_1_rating_diff / 2)
    update_player_stats(team_1_attack, team_2_av_rating, team_1_rating_diff / 2)
    update_player_stats(team_2_defense, team_1_av_rating, team_2_rating_diff / 2)
    update_player_stats(team_2_attack, team_1_av_rating, team_2_rating_diff / 2)
    
    return HttpResponseRedirect(reverse('elo_app:index'))

def submit_player(request: HttpRequest):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        if len(request.POST['player_name']) == 0:
            raise ValueError
        accepted_characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        accepted_characters += accepted_characters.lower()
        accepted_characters += "1234567890_"
        for character in request.POST['player_name']:
            if not character in accepted_characters:
                raise ValueError
        player = Player.objects.create(player_name=request.POST["player_name"])
        player_rating = PlayerRating.objects.create(player=player, timestamp=timezone.now().date(), rating=400)
    except IntegrityError:
        return render(request, 
                      'elo/submit_player_form.html', 
                      {'error_message': 'Username already in use'})
    except ValueError:
        return render(request, 
                      'elo/submit_player_form.html', 
                      {'error_message': 'Please provide a non-empty username using only upper case, lower case, numbers and underscore'})
    
    return HttpResponseRedirect(reverse('elo_app:player_detail', args=(player.id,)),
                                {'ratings': player.playerrating_set.all()})

