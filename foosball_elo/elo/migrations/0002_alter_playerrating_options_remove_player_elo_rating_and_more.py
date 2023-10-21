# Generated by Django 4.2.6 on 2023-10-20 12:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('elo', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='playerrating',
            options={'ordering': ['player', 'timestamp']},
        ),
        migrations.RemoveField(
            model_name='player',
            name='elo_rating',
        ),
        migrations.RemoveField(
            model_name='player',
            name='number_of_games_played',
        ),
        migrations.RemoveField(
            model_name='player',
            name='opponent_average_rating',
        ),
    ]