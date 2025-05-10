from django.urls import path
from . import views

urlpatterns = [
    path('account/', views.account, name='account'),
    path('authenticate', views.login, name='userLogin'),
    path("login", views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
]