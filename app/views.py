from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)

# As rotas de login foram movidas para user/views.py

@login_required(login_url='/login')
def home(request):
    return render(request, 'home/index.html')