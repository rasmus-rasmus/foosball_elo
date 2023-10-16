from django.db import models
from django.db.models.query import QuerySet
from django.db.utils import IntegrityError
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseNotAllowed
from django.views import View, generic
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test

from .models import Player, Game, PlayerRating

import decimal
from typing import Any
import datetime

#############
## HELPERS ##
#############

def update_player_stats(player : Player, opponent_rating : float):
    player.opponent_average_rating *= player.number_of_games_played
    player.opponent_average_rating += decimal.Decimal(opponent_rating)
    player.number_of_games_played += 1
    player.opponent_average_rating /= player.number_of_games_played
    player.save()

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
    
class InvalidDateEror(Exception):
    def __str__(self):
        return "Game cannot be in the future."


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
    
# class SubmitPlayerView(generic.TemplateView):
#     template_name = 'elo/submit_player_form.html'
    
class PlayerDetailView(generic.DetailView):
    model = Player

    def get_queryset(self) -> QuerySet[Player]:
        return Player.objects.all()

@user_passes_test(lambda u:u.is_authenticated, login_url=reverse_lazy('registration:login'))
def submit_game(request: HttpRequest):
    if not request.method == 'POST':
        return render(request, 'elo/submit_game_form.html', {
            'all_players_list': Player.objects.order_by('player_name'),
            'error_message': 'Something went wrong. Please try again'
        })
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
        
        if datetime.datetime.strptime(date, "%Y-%m-%d").date() > timezone.now().date():
            raise InvalidDateEror
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
    except InvalidDateEror as error:
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
    
    update_player_stats(team_1_defense, team_2_av_rating)
    update_player_stats(team_1_attack, team_2_av_rating)
    update_player_stats(team_2_defense, team_1_av_rating)
    update_player_stats(team_2_attack, team_1_av_rating)
    
    return HttpResponseRedirect(reverse('elo_app:index'))

@user_passes_test(lambda u:u.is_staff, login_url=reverse_lazy('registration:login'))
def update_ratings(request: HttpRequest):
    if not request.method == 'POST':
        return HttpResponseRedirect(reverse('elo_app:index'))
    unrecorded_games = Game.objects.filter(updates_performed=False)
    diff_dict = {}
    for game in unrecorded_games:
        team_1_diff, team_2_diff = game.compute_rating_diffs()
        looper_counter = 0
        for player in (game.team_1_defense, 
                       game.team_1_attack, 
                       game.team_2_defense, 
                       game.team_2_attack):
            if player.id in diff_dict.keys():
                diff_dict[player.id] += round(team_1_diff*.5) if looper_counter < 2 else round(team_2_diff*.5)
            else:
                diff_dict[player.id] = round(team_1_diff*.5) if looper_counter < 2 else round(team_2_diff*.5)
            looper_counter += 1
        game.updates_performed = True
        game.save()
        
    for player_id, total_diff in diff_dict.items():
        player = Player.objects.get(pk=player_id)
        player.elo_rating = max(player.elo_rating + total_diff, 100)
        player.save()
        PlayerRating.objects.create(player=player, timestamp=timezone.now().date(), rating=player.elo_rating)
        
    return HttpResponseRedirect(reverse('elo_app:index'))
