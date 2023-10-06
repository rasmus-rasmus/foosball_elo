from django.urls import path
from . import views

app_name='elo_app'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('all/', views.AllView.as_view(), name='all'),
    path('<int:player_id>/', views.player_detail, name='player_detail'),
    path('game/submit_form', views.SubmitFormView.as_view(), name='submit_form'),
    path('game/submit', views.submit_game, name='submit_game')
]
