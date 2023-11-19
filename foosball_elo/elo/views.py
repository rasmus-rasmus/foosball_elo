from django.db.models import Max
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
     
    
def compute_player_statistics(games : set[Game],
                              player: Player) -> tuple[int]:
    """ Returns (highest_opponent_rating, average_opponent_rating, games_won, games_lost, eggs_dealt_count, eggs_collected_count)
    """
    highest_opponent_rating = 0
    average_opponent_rating = 0
    games_won = 0
    games_lost = 0
    eggs_dealt_count = 0
    eggs_collected_count = 0
    
    for game in games:
        player_is_team_1 = player in [game.team_1_defense, game.team_1_attack]
        
        opponent_defense_rating = \
            (game.team_2_defense if player_is_team_1 else game.team_1_defense).get_rating(game.date_played)
            
        opponent_attack_rating = \
            (game.team_2_attack if player_is_team_1 else game.team_1_attack).get_rating(game.date_played)
            
        opponent_rating = .5 * (opponent_defense_rating + opponent_attack_rating)
        average_opponent_rating += opponent_rating
        highest_opponent_rating = max(highest_opponent_rating, opponent_rating)
        
        if game.winner() == 2-int(player_is_team_1):
            games_won += 1
        else:
            games_lost += 1
        
        eggs_dealt_count += int((game.team_2_score if player_is_team_1 else game.team_1_score) == 0)
        eggs_collected_count += int((game.team_1_score if player_is_team_1 else game.team_2_score) == 0)
    
    average_opponent_rating /= len(games) if len(games) > 0 else 1
    
    return highest_opponent_rating, average_opponent_rating, games_won, games_lost, eggs_dealt_count, eggs_collected_count

def get_player_statistics(player: Player) -> dict[str, int]:
    # Use sets to avoid one-player-teams (i.e., attack=defense) to
    # be counted twice. Get ready for some good old discrete measure theory
    # a.k.a. 'the pleasures of counting'.
    games_as_team_1_defense = set(Game.objects.filter(team_1_defense=player))
    games_as_team_1_attack = set(Game.objects.filter(team_1_attack=player))
    games_as_team_1 = games_as_team_1_defense.union(games_as_team_1_attack)

    defense_games_count = len(games_as_team_1_defense)
    attack_games_count = len(games_as_team_1_attack)   
    single_games_count = defense_games_count + attack_games_count - len(games_as_team_1)
    defense_games_count -= single_games_count
    attack_games_count -= single_games_count
    
    games_as_team_2_defense = set(Game.objects.filter(team_2_defense=player))
    games_as_team_2_attack = set(Game.objects.filter(team_2_attack=player))
    games_as_team_2 = games_as_team_2_defense.union(games_as_team_2_attack)
    
    defense_games_count += len(games_as_team_2_defense)
    attack_games_count += len(games_as_team_2_attack)
    single_games_team_2 = len(games_as_team_2_defense) + len(games_as_team_2_attack) - len(games_as_team_2)
    single_games_count += single_games_team_2
    defense_games_count -= single_games_team_2
    attack_games_count -= single_games_team_2
    
    highest_opponent_rating, average_opponent_rating, games_won, games_lost, eggs_dealt_count, eggs_collected_count \
    = compute_player_statistics(games_as_team_1.union(games_as_team_2),
                                player)
        
    out = {}
    out['game_count'] = defense_games_count + attack_games_count + single_games_count
    out['highest_opponent_rating'] = highest_opponent_rating
    out['average_opponent_rating'] = average_opponent_rating
    out['defense_games_count'] = defense_games_count
    out['attack_games_count'] = attack_games_count
    out['single_games_count'] = single_games_count
    out['games_won'] = games_won
    out['games_lost'] = games_lost
    out['eggs_dealt_count'] = eggs_dealt_count
    out['eggs_collected_count'] = eggs_collected_count
    
    return out
    

def get_all_rating_diffs(save_games: bool = False, penalize_inactivity: bool = False):
    all_players = sorted(Player.objects.all(), key=lambda a: -a.get_rating())
    diff_dict = dict(
        zip(list(Player.objects.all()), 
            [(None if penalize_inactivity else 0) for x in range(Player.objects.count())]
        )
    )
    
    unrecorded_games = Game.objects.filter(updates_performed=False)
    for game in unrecorded_games:
        team_1_diff, team_2_diff = game.compute_rating_diffs()
        
        for idx, player in enumerate([game.team_1_defense, 
                                      game.team_1_attack, 
                                      game.team_2_defense, 
                                      game.team_2_attack]):
            curr_diff = round(team_1_diff*.5) if idx < 2 else round(team_2_diff*.5)
            if diff_dict[player]:
                diff_dict[player] += curr_diff
            else:
                diff_dict[player] = curr_diff
            
        if save_games:
            game.updates_performed = True
            game.save()
    
    if not penalize_inactivity:
        return diff_dict
    
    for idx, player in enumerate(all_players):
        # If player has been inactive since last update, i.e., diff_dict[player] == None,
        # player loses 1 point for each active player ranking below them (but no more than 25 though),
        # and each such player gains 1 point, to keep the total number of points in the league unchanged.
        if not diff_dict[player]:
            penalty_diff = 0
            for other_idx in range(idx+1, len(all_players)):
                if penalty_diff <= -25:
                    break
                if diff_dict[all_players[other_idx]]:
                    diff_dict[all_players[other_idx]] += 1
                    penalty_diff -= 1
            diff_dict[player] = penalty_diff
            
    return diff_dict
           
    
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
        context['recent_games'] = Game.objects.filter(updates_performed=False).order_by('-date_played')
        return context
    
    def get_queryset(self) -> QuerySet[Player]:
        players = sorted(Player.objects.all(), key=lambda a: -a.get_rating())[:5]
        rating_diffs = get_all_rating_diffs()
        return list(zip(players, [rating_diffs[p] for p in players]))
    
    
class AllView(generic.ListView):
    template_name = 'elo/player_list.html'
    context_object_name = 'player_list'
    
    
    
    def get_queryset(self) -> QuerySet[Player]:
        players = sorted(Player.objects.all(), key=lambda a: -a.get_rating())
        rating_diffs = get_all_rating_diffs()
        return list(zip(players, [rating_diffs[p] for p in players]))
    
class SubmitGameView(generic.ListView):
    template_name = 'elo/submit_game_form.html'
    context_object_name = 'all_players_list'
    
    def get_queryset(self):
        return Player.objects.all()
    
    
class PlayerDetailView(generic.DetailView):
    model = Player
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx['high_score'] = self.object.playerrating_set.aggregate(Max('rating'))['rating__max']
        player_stats = get_player_statistics(self.object)
        for key in player_stats:
            ctx[key] = round(player_stats[key], 2)
        return ctx


@user_passes_test(lambda u:u.is_authenticated, login_url=reverse_lazy('registration:login'))
def submit_game(request: HttpRequest):
    if not request.method == 'POST':
        return render(request, 'elo/submit_game_form.html', {
            'all_players_list': Player.objects.order_by('player_name'),
            'error_message': 'Something went wrong. Please try again'
        })
    data = request.POST
    try:
        team_1_defense = Player.objects.get(pk=data['winning_team_defense'])
        team_1_attack = Player.objects.get(pk=data['winning_team_attack'])
        team_2_defense = Player.objects.get(pk=data['losing_team_defense'])
        team_2_attack = Player.objects.get(pk=data['losing_team_attack'])
        team_1_score = 10
        team_2_score = int(data['losing_team_score'])
        date = data['date']
        user = request.user
        
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
                               date_played=date,
                               submitted_by=user)
    
    return HttpResponseRedirect(reverse('elo_app:index'))

@user_passes_test(lambda u:u.is_staff, login_url=reverse_lazy('registration:login'))
def update_ratings(request: HttpRequest):
    if not request.method == 'POST':
        return HttpResponseRedirect(reverse('elo_app:index'))
    
    diff_dict = get_all_rating_diffs(save_games=True, penalize_inactivity=True)
        
    for player, total_diff in diff_dict.items():
        new_elo_rating = max(player.get_rating() + total_diff, 100)
        PlayerRating.objects.create(player=player, timestamp=timezone.now().date(), rating=new_elo_rating)
        
    return HttpResponseRedirect(reverse('elo_app:index'))
