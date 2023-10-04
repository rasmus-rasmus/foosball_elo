from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class Player(models.Model):
    player_name = models.CharField(max_length=50, unique=True)
    elo_rating = models.IntegerField(default=400)
    opponent_average_rating = models.DecimalField(default=-1, max_digits=10, decimal_places=2)
    number_of_games_played = models.IntegerField(default=0)
    
    def __str__(self):
        return self.player_name

    
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
        if self.team_1_score == 10 and self.team_2_score < 10:
            return 1
        elif self.team_2_score == 10 and self.team_1_score < 10:
            return 2
        return 0
    class Meta:
        # For ordering most recent to last
        ordering = ['-date_played']
