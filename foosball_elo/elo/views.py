from django.shortcuts import render
from django.http import HttpResponse, HttpRequest

# Create your views here.
def index(request: HttpRequest):
    #TODO: Implement
    return HttpResponse("<h2>Welcome to the foosball elo rating app!</h2>")

def submit_game(request: HttpRequest):
    #TODO: Implement
    return HttpResponse("<h2>You just submitted a game</h2>")

def player_detail(request: HttpRequest, player_id: int):
    #TODO: Implement
    return HttpResponse("<h2>You are looking at details for player {}".format(player_id))

