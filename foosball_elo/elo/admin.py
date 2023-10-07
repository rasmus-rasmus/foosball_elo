from django.contrib import admin
from .models import Game, Player

admin.site.site_header="Elo Administration"

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('player_name', 'id', 'elo_rating')
    search_fields = ('player_name',)
    
class GameAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Players', {'fields': ('team_1_defense', 'team_1_attack', 'team_2_defense', 'team_2_attack')}),
         ('Data', {'fields': ('team_1_score', 'team_2_score', 'date_played')})
    ]
    list_display = ['date_played', 'team_1_defense', 'team_1_attack', 'team_2_defense', 'team_2_attack', 'winner']
    search_fields = ['team_1_defense', 'team_1_attack', 'team_2_defense', 'team_2_attack']
    list_filter = ['date_played']

# Register your models here.
admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)