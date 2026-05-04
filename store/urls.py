from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # --- NEW VAULT URLS ---
    path('vault/', views.vault, name='vault'),
    path('add-to-vault/', views.add_to_vault, name='add_to_vault'),

    #--- CHECKOUT URLs ---
    path('checkout/', views.checkout, name='checkout'), # <-- NEW

    # --- NEW SEARCH URL ---
    path('search/', views.search, name='search'),

    # --- NEW AI RECOMMENDER URL ---
    path('recommender/', views.recommender, name='recommender'),

    # --- NEW CLEAR CHAT URL ---
    path('clear-chat/', views.clear_chat, name='clear_chat'),

    # --- NEW MANAGER DASHBOARD URL ---
    path('manager/', views.manager_dashboard, name='manager_dashboard'),

    # --- BLIND DATE URL ---
    path('blind-date/', views.blind_date, name='blind_date'),

    # --- ATMOSPHERE GENERATOR URL ---
    path('api/atmosphere/', views.get_atmosphere, name='get_atmosphere'),
]
# The empty string '' means the root URL (e.g., yourwebsite.com/)