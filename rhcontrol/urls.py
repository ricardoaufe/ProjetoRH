from django.urls import path

from . import views

app_name = 'rhcontrol'
urlpatterns = [
    path(' ', views.dashboard, name='dashboard'),
]