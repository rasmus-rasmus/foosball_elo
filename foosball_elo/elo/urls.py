from django.urls import path
from . import views

app_name='elo'
urlpatterns = [
    path('', views.index, name='index')
]
