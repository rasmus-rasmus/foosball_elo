from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib import admin
from django.contrib.auth.models import User

from datetime import datetime

# Create your models here.
class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=50, unique=True)
    
    """
    Returns player's rating at the time given by date, or latest rating if date isn't specified.
    """
    def get_rating(self, date: datetime.date = None) -> int:
        player_ratings = self.playerrating_set.all()
        
        if len(player_ratings) == 0:
            # Can only happen if player was added through admin interface.
            return 0
        if date == None:
            # QuerySets don't support negative indexing :'(
            return player_ratings[len(player_ratings) - 1].rating
        if len(player_ratings) == 1:
            return player_ratings[0].rating
        elif date <= player_ratings[0].timestamp:
            # Can only happen in case game_date was at some point moved back in time
            # by a user with admin privileges.
            return player_ratings[0].rating
        elif date > player_ratings[len(player_ratings)-1].timestamp:
            return player_ratings[len(player_ratings)-1].rating
        
        # Bisection search for player's rating at the desired time.
        idx = 0
        while not (player_ratings[idx].timestamp < date and date <= player_ratings[idx+1].timestamp):
            if player_ratings[idx].timestamp >= date:
                idx = int(idx/2)
            elif date > player_ratings[idx+1].timestamp:
                idx += int((len(player_ratings) - 1 - idx) / 2)
            else:
                raise RuntimeError("This shouldn't happen!")
            
        return player_ratings[idx].rating   
    
    def __str__(self):
        return self.player_name
    
    class Meta:
        ordering = [models.functions.Upper('player_name')]    

    
class Game(models.Model):
    team_1_defense = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='team_1_defense')
    team_1_attack = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='team_1_attack')
    team_2_defense = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='team_2_defense')
    team_2_attack = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='team_2_attack')
    
    team_1_score = models.SmallIntegerField(validators=[MinValueValidator(0), 
                                                        MaxValueValidator(10)])
    team_2_score = models.SmallIntegerField(validators=[MinValueValidator(0),
                                                        MaxValueValidator(10)])
    
    date_played = models.DateField('date played')
    
    # Records whether the players in this game have had their rating updated based on its result
    updates_performed = models.BooleanField('player ratings updated?', default=False)
    
    def winner(self) -> int:
        if int(self.team_1_score) == 10 and int(self.team_2_score) < 10:
            return 1
        elif int(self.team_2_score) == 10 and int(self.team_1_score) < 10:
            return 2
        return 0
    
    """
    Computes the ratings diffs of both teams based on the outcome of the game.
    Returns a tuple containing rating diffs for team_1 and team_2 in that order.
    NB: How the rating diff is shared between the two players, should be determined
    by the caller of this method. 
    """
    def compute_rating_diffs(self, 
                             scaling_factor : int = 400, 
                             adaption_step : int = 64) -> tuple[int]:
        team_1_rating = (self.team_1_defense.get_rating() + self.team_1_attack.get_rating()) * .5
        team_2_rating = (self.team_2_defense.get_rating() + self.team_2_attack.get_rating()) * .5
        
        team_1_expected_outcome = 1 / (1 + 10**((team_2_rating - team_1_rating) / scaling_factor))
        team_2_expected_outcome = 1 / (1 + 10**((team_1_rating - team_2_rating) / scaling_factor))
        winner = self.winner()
        if winner == 0:
            raise ValueError("Winner of game {} could not be determined.".format(self.id))
        team_1_diff = adaption_step * (int(winner==1) - team_1_expected_outcome)
        team_2_diff = adaption_step * (int(winner==2) - team_2_expected_outcome)
        return team_1_diff, team_2_diff
    
    class Meta:
        # For ordering most recent to last
        ordering = ['-date_played']
        

class PlayerRating(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    timestamp = models.DateField('date')
    rating = models.IntegerField('elo rating')
    
    def get_player_name(self):
        return self.player.player_name
    
    class Meta:
        ordering = ['player_id', 'timestamp']
