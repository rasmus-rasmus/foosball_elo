"""
URL configuration for foosball_elo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, reverse_lazy
from django.contrib.auth.views import LoginView

from . import views

app_name='registration'
urlpatterns = [
    path("", LoginView.as_view(template_name='registration/login.html', next_page=reverse_lazy('elo_app:index')), name="login"),
    path('player/submit_form/', views.SubmitPlayerView.as_view(), name='submit_form_player'), 
    path('player/submit/', views.submit_player, name='submit_player'),
]
