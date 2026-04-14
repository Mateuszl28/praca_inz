from django.urls import path
from . import views

app_name = 'groby'

urlpatterns = [
    path('', views.home, name='home'),
    path('szukaj/', views.szukaj, name='szukaj'),
    path('mapa/', views.mapa, name='mapa'),
    path('sektory/', views.sektory_list, name='sektory_list'),
    path('sektor/<int:pk>/', views.sektor_detail, name='sektor_detail'),
    path('grob/<int:pk>/', views.grob_detail, name='grob_detail'),
    path('osoba/<int:pk>/', views.osoba_detail, name='osoba_detail'),
]
