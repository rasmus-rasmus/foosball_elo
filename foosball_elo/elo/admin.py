from django.contrib import admin
from .models import Game, Player, PlayerRating

admin.site.site_header="Elo Administration"

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('player_name', 'id')
    search_fields = ('player_name',)
    
class GameAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Players', {'fields': ('team_1_defense', 'team_1_attack', 'team_2_defense', 'team_2_attack')}),
         ('Data', {'fields': ('team_1_score', 'team_2_score', 'date_played')}),
         ('Status', {'fields': ('updates_performed',)})
    ]
    list_display = ['date_played', 'team_1_defense', 'team_1_attack', 'team_2_defense', 'team_2_attack', 'updates_performed', 'submitted_by']
    search_fields = ['team_1_defense', 'team_1_attack', 'team_2_defense', 'team_2_attack']
    list_filter = ['date_played']
    
class PlayerRatingAdmin(admin.ModelAdmin):
    list_display = ['player', 'timestamp', 'rating']
    search_fields = ['player']
    list_filter = ['player']
    

# Register your models here.
admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(PlayerRating, PlayerRatingAdmin)