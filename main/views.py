# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Activity, Media
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

def activity_list(request):
    q = request.GET.get('q', '')

    if q:
        activities = Activity.objects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).order_by('-created_at')
    else:
        activities = Activity.objects.order_by('-created_at')

    return render(request, 'main/activity_list.html', {
        'activities': activities,
        'query': q
    })

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
from .forms import ActivityForm, MediaForm


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

@login_required
def activity_detail(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    media_items = Media.objects.filter(activity=activity).order_by('-created_at')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'You must log in to upload media.')
            return redirect('login')

        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.activity = activity
            media.created_by = request.user
            media.save()
            messages.success(request, 'Media uploaded successfully!')
            return redirect('activity_detail', pk=activity.pk)
    else:
        form = MediaForm()

    return render(request, 'main/activity_detail.html', {
        'activity': activity,
        'media_items': media_items,
        'form': form
    })

def search_suggest(request):
    q = request.GET.get('q', '')
    results = []

    if q:
        activities = Activity.objects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )[:5]

        for a in activities:
            results.append({"id": a.pk, "title": a.title})

    return JsonResponse({"results": results})

