# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Activity, Media, Registration, UserHistory
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone

def activity_list(request):
    q = request.GET.get('q', '')

    if q:
        activities = Activity.objects.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q)
        ).order_by('-created_at')
    else:
        activities = Activity.objects.order_by('-created_at')

    session_visit_count = request.session.get('main_page_visits', 0) + 1
    request.session['main_page_visits'] = session_visit_count

    raw_total = request.COOKIES.get('total_visits', '0')
    try:
        total_visits = int(raw_total) + 1
    except ValueError:
        total_visits = 1

    last_visit = request.COOKIES.get('last_visit')

    registered_ids = set()
    if request.user.is_authenticated:
        registered_ids = set(
            Registration.objects.filter(
                user=request.user,
                status='joined'
            ).values_list('joined_activity_id', flat=True)
        )

    context = {
        'activities': activities,
        'query': q,
        'registered_ids': registered_ids,
        'session_visit_count': session_visit_count,
        'cookie_total_visits': total_visits,
        'cookie_last_visit': last_visit,
    }

    response = render(request, 'main/activity_list.html', context)

    max_age = 30 * 24 * 60 * 60  # 30 days in seconds
    response.set_cookie('total_visits', total_visits, max_age=max_age)
    response.set_cookie('last_visit', timezone.now().isoformat(), max_age=max_age)

    # Optional: also log DB history
    if request.user.is_authenticated:
        UserHistory.objects.create(
            user=request.user,
            action="Visited main page"
        )

    return response

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

    activity_visits = request.session.get('activity_visits', {})
    key = str(activity.pk)
    activity_visits[key] = activity_visits.get(key, 0) + 1
    request.session['activity_visits'] = activity_visits

    # DB history (optional, but you already wanted this)
    if request.user.is_authenticated:
        UserHistory.objects.create(
            user=request.user,
            action=f"Visited activity: {activity.title}"
        )

    media_items = activity.media.all().order_by('-created_at')

    return render(request, 'main/activity_detail.html', {
        'activity': activity,
        'media_items': media_items,
        'session_activity_visits': activity_visits.get(key, 1),
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


@login_required
def register_activity(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        reg, created = Registration.objects.get_or_create(
            user=request.user,
            joined_activity=activity,
            defaults={'status': 'joined'},
        )
        if not created and reg.status != 'joined':
            reg.status = 'joined'
            reg.save()

        UserHistory.objects.create(
            user=request.user,
            action=f"Registered for activity: {activity.title}"
        )

        messages.success(request, f"You registered for: {activity.title}")
    return redirect('activity_list')


@login_required
def cancel_registration(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        try:
            reg = Registration.objects.get(user=request.user, joined_activity=activity)
            reg.status = 'cancelled'
            reg.save()

            UserHistory.objects.create(
                user=request.user,
                action=f"Cancelled registration for activity: {activity.title}"
            )
            messages.info(request, f"You cancelled: {activity.title}")
        except Registration.DoesNotExist:
            pass
    return redirect('activity_list')

@login_required
def user_history(request):
    history_items = UserHistory.objects.filter(
        user=request.user
    ).order_by('-timestamp')

    # session data
    session_main_visits = request.session.get('main_page_visits', 0)
    session_activity_visits = request.session.get('activity_visits', {})

    # cookie data
    cookie_total_visits = request.COOKIES.get('total_visits')
    cookie_last_visit = request.COOKIES.get('last_visit')

    # optional: map activity IDs to titles for nicer display
    activity_title_map = {}
    if session_activity_visits:
        activities = Activity.objects.filter(id__in=session_activity_visits.keys())
        for a in activities:
            activity_title_map[str(a.id)] = a.title

    return render(request, 'main/user_history.html', {
        'history_items': history_items,
        'session_main_visits': session_main_visits,
        'session_activity_visits': session_activity_visits,
        'activity_title_map': activity_title_map,
        'cookie_total_visits': cookie_total_visits,
        'cookie_last_visit': cookie_last_visit,
    })



def log_user_history(user, action):
    if user.is_authenticated:
        UserHistory.objects.create(
            user=user,
            action=action
        )

