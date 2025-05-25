from django.contrib import admin
from django.urls import path, include
from django.urls import resolve
from user import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),

    path('login/', user_views.login_view, name='login'),
    path('login_sso', user_views.login_sso, name='login_sso'),
    path('login_sso/callback', user_views.login_sso_callback, name='login_sso_callback'),
    path('logout_sso', user_views.logout_sso, name='logout_sso'),

    path('usuarios/', include('user.urls')),
    
    path('financeira/', include('financeira.urls', namespace='financeira')),
]
