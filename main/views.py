# main/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Activity

def activity_list(request):
    activities = Activity.objects.order_by('-created_at')  # newest first
    return render(request, 'main/activity_list.html', {'activities': activities})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # auto-login after signup (optional)
            login(request, user)
            return redirect('activity_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ActivityForm

@login_required
def activity_create(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user  # link to current user
            activity.save()
            return redirect('activity_list')
    else:
        form = ActivityForm()
    return render(request, 'main/activity_form.html', {'form': form})

