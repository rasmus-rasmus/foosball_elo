from django.urls import path
from . import views

app_name='elo_app'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('all/', views.AllView.as_view(), name='all'),
    path('<int:pk>/', views.PlayerDetailView.as_view(), name='player_detail'),
    path('game/submit_form/', views.SubmitGameView.as_view(), name='submit_form_game'),
    path('player/submit_form/', views.SubmitPlayerView.as_view(), name='submit_form_player'),
    path('game/submit/', views.submit_game, name='submit_game'),
    path('player/submit/', views.submit_player, name='submit_player')
]
