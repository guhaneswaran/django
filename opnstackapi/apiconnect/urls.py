from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('createvm', views.createvm, name='createvm')
]
