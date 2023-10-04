from django.urls import path
from . import views

app_name='elo_app'
urlpatterns = [
    path('', views.index, name='index'),
    path('<int:player_id>/', views.player_detail, name='player_detail'),
    path('game/submit', views.submit_game, name='submit_game')
]
