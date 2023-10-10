from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class Player(models.Model):
    player_name = models.CharField(max_length=50, unique=True)
    elo_rating = models.IntegerField(default=400)
    opponent_average_rating = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    number_of_games_played = models.IntegerField(default=0)
    
    def update_rating(self):
        self.elo_rating = self.playerrating_set.all[0]
        return self.elo_rating
    
    def __str__(self):
        return self.player_name
    
    class Meta:
        ordering = ['player_name']
    

    
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
        team_1_rating = (self.team_1_defense.elo_rating + self.team_1_attack.elo_rating) * .5
        team_2_rating = (self.team_2_defense.elo_rating + self.team_2_attack.elo_rating) * .5
        
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
    
    class Meta:
        ordering = ['player', '-timestamp']
