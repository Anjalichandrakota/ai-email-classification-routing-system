from django.urls import path
from . import views

app_name = 'emails'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('analyze/', views.analyze, name='analyze'),
    path('history/', views.history, name='history'),
    path('history/<int:email_id>/', views.email_detail, name='email_detail'),
]
