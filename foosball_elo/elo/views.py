from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.views import generic
from .models import Player, Game

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
    Game.objects.create(team_1_defense=team_1_defense,
                        team_1_attack=team_1_attack,
                        team_2_defense=team_2_defense,
                        team_2_attack=team_2_attack,
                        team_1_score=team_1_score,
                        team_2_score=team_2_score,
                        date_played=date)
    #TODO: Implement updating player statistics
    return HttpResponse("<h2>You just submitted a game</h2>")

def player_detail(request: HttpRequest, player_id: int):
    #TODO: Implement
    return HttpResponse("<h2>You are looking at details for player {}".format(player_id))

