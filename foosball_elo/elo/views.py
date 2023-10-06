import decimal
from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.views import generic
from .models import Player, Game

def update_player_stats(player : Player, opponent_rating : float, rating_diff : int = 0):
    player.opponent_average_rating *= player.number_of_games_played
    player.opponent_average_rating += decimal.Decimal(opponent_rating)
    player.number_of_games_played += 1
    player.opponent_average_rating /= player.number_of_games_played
    player.elo_rating += rating_diff
    player.save()
    
def compute_rating_diff(team_rating : int, 
                        opponent_rating : int, 
                        victory : bool, 
                        scaling_factor : int = 400, 
                        adaption_step : int = 64):
    expected_outcome = 1 / (1 + 10**((opponent_rating - team_rating) / scaling_factor))
    print("expected outcome: ", expected_outcome)
    return adaption_step * (int(victory) - expected_outcome)

# Create your views here.
class IndexView(generic.ListView):
    template_name = 'elo/index.html'
    context_object_name = 'top_5_list'
    
    def get_queryset(self) -> QuerySet[Player]:
        return Player.objects.order_by('-elo_rating')[:5]
    
class AllView(generic.ListView):
    model = Player
    
    def get_queryset(self) -> QuerySet[Player]:
        return Player.objects.order_by('-elo_rating')
    
class SubmitFormView(generic.ListView):
    template_name = 'elo/submit_form.html'
    context_object_name = 'all_players_list'
    
    def get_queryset(self):
        return Player.objects.order_by('player_name')
    

def submit_game(request: HttpRequest):
    data = request.POST
    try:
        team_1_defense = Player.objects.get(pk=data['team_1_defense'])
        team_1_attack = Player.objects.get(pk=data['team_1_attack'])
        team_2_defense = Player.objects.get(pk=data['team_2_defense'])
        team_2_attack = Player.objects.get(pk=data['team_2_attack'])
        team_1_score = data['team_1_score']
        team_2_score = data['team_2_score']
        date = data['date']
    except (KeyError, Player.DoesNotExist):
        return render(request, 'elo/submit_form.html', {
            'all_players_list': Player.objects.order_by('player_name'),
            'error_message': 'Please fill out all game data'
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
    return HttpResponse("<h2>You just submitted a game</h2>")

def player_detail(request: HttpRequest, player_id: int):
    #TODO: Implement
    return HttpResponse("<h2>You are looking at details for player {}".format(player_id))

