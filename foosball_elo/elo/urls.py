from django.urls import path
from . import views

app_name='elo_app'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('all/', views.AllView.as_view(), name='all'),
    path('<int:player_id>/', views.player_detail, name='player_detail'),
    path('game/submit_form/game', views.SubmitGameView.as_view(), name='submit_form_game'),
    path('game/submit_form/player', views.SubmitPlayerView.as_view(), name='submit_form_player'),
    path('game/submit/game', views.submit_game, name='submit_game'),
]
