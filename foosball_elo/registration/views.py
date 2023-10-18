from django.shortcuts import render
from django.views import generic
from django.http import HttpRequest, HttpResponseRedirect, HttpResponseNotAllowed
from django.db.utils import IntegrityError
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User

from elo.models import Player, PlayerRating
from datetime import timedelta

# Create your views here.

class SubmitPlayerView(generic.TemplateView):
    template_name = 'registration/submit_player_form.html'
    
    
def submit_player(request: HttpRequest):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        if len(request.POST['player_name']) == 0:
            raise ValueError
        
        accepted_characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        accepted_characters += accepted_characters.lower()
        accepted_characters += "1234567890_"
        for character in request.POST['player_name']:
            if not character in accepted_characters:
                raise ValueError
        
        user = User.objects.create_user(username=request.POST['player_name'],
                                        email=request.POST['email'],
                                        password=request.POST['password'])
        player = Player.objects.create(player_name=request.POST["player_name"], user=user)
        
        # Ratings will be updates on sundays, so first rating has its timestamp set
        # to last sunday from today's date.
        date = timezone.now().date()
        while (date.weekday() != 6):
            date -= timedelta(days=1)
        PlayerRating.objects.create(player=player, timestamp=date, rating=400)
    except IntegrityError:
        return render(request, 
                      'registration/submit_player_form.html', 
                      {'error_message': 'Username already in use.'})
    except ValueError:
        return render(request, 
                      'registration/submit_player_form.html', 
                      {'error_message': 'Please provide a non-empty username using only upper case, lower case, numbers and underscore.'})
    except KeyError:
        return render(request,
                      'registration/submit_player_form.html',
                      {'error_message': 'Something went wrong, please try again.'})
    
    return HttpResponseRedirect(reverse('elo_app:player_detail', args=(player.id,)),
                                {'ratings': player.playerrating_set.all()})