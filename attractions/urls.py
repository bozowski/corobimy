from django.urls import path
from attractions import views

urlpatterns = [
    path('', views.attraction_list, name='attraction-list'),
    path('attractions/<int:pk>/save/', views.save_attraction, name='attraction-save'),
]
