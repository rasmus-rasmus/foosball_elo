from django.db import models
from tastypie.resources import ModelResource
from tastypie.resources import fields
from elo.models import Game

class GameResource(ModelResource):
    rating_diff = fields.FloatField(readonly=True, attribute='get_rating_diff_abs')
    team_1_defense = fields.CharField(readonly=True, attribute='team_1_defense__player_name')
    team_1_attack = fields.CharField(readonly=True, attribute='team_1_attack__player_name')
    team_2_defense = fields.CharField(readonly=True, attribute='team_2_defense__player_name')
    team_2_attack = fields.CharField(readonly=True, attribute='team_2_attack__player_name')
    
    class Meta:
        queryset = Game.objects.all()
        resource_name = 'games'
