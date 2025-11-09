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
from .forms import CustomSignupForm, ContactMessageForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

class ActivityListView(ListView):
    model = Activity
    template_name = "main/activity_list.html"
    context_object_name = "activities"

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        category_filter = self.request.GET.get('category', '')
        
        queryset = Activity.objects.all()
        
        # Apply keyword search filter
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(location__icontains=q)
            )
        
        # Apply category dropdown filter
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        q = request.GET.get('q', '')
        category_filter = request.GET.get('category', '')

        # session
        session_visit_count = request.session.get('main_page_visits', 0) + 1
        request.session['main_page_visits'] = session_visit_count

        # cookies
        raw_total = request.COOKIES.get('total_visits', '0')
        try:
            total_visits = int(raw_total) + 1
        except ValueError:
            total_visits = 1

        last_visit = request.COOKIES.get('last_visit')

        # user registrations
        registered_ids = set()
        if request.user.is_authenticated:
            registered_ids = set(
                Registration.objects.filter(
                    user=request.user,
                    status='joined'
                ).values_list('joined_activity_id', flat=True)
            )

        # Get category choices for dropdown
        from .models import Activity
        category_choices = Activity.CATEGORY_CHOICES

        # Add to context
        context.update({
            'query': q,
            'category_filter': category_filter,
            'category_choices': category_choices,
            'registered_ids': registered_ids,
            'session_visit_count': session_visit_count,
            'cookie_total_visits': total_visits,
            'cookie_last_visit': last_visit,
        })

        return context

    def render_to_response(self, context, **response_kwargs):
        """Attach cookies to the response."""
        response = super().render_to_response(context, **response_kwargs)

        max_age = 30 * 24 * 60 * 60
        response.set_cookie('total_visits', context['cookie_total_visits'], max_age=max_age)
        response.set_cookie('last_visit', timezone.now().isoformat(), max_age=max_age)

        # DB logging
        if self.request.user.is_authenticated:
            UserHistory.objects.create(
                user=self.request.user,
                action="Visited main page"
            )

        return response

def signup(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('activity_list')
    else:
        form = CustomSignupForm()
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

class ActivityDetailView(DetailView):
    model = Activity
    template_name = "main/activity_detail.html"
    context_object_name = "activity"

    def get_object(self):
        """Always load the object so GET and POST work correctly."""
        return super().get_object()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # session visits
        activity_visits = request.session.get('activity_visits', {})
        key = str(self.object.pk)
        activity_visits[key] = activity_visits.get(key, 0) + 1
        request.session['activity_visits'] = activity_visits

        # DB history
        if request.user.is_authenticated:
            UserHistory.objects.create(
                user=request.user,
                action=f"Visited activity: {self.object.title}"
            )

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handle media uploads."""
        self.object = self.get_object()

        if not request.user.is_authenticated:
            return redirect('login')

        form = MediaForm(request.POST, request.FILES)

        if form.is_valid():
            media = form.save(commit=False)
            media.activity = self.object
            media.created_by = request.user
            media.save()

            UserHistory.objects.create(
                user=request.user,
                action=f"Uploaded media to: {self.object.title}"
            )

            return redirect('activity_detail', pk=self.object.pk)

        # DEBUG: Show errors so we know what’s wrong
        print("MEDIA UPLOAD ERRORS:", form.errors)

        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['media_items'] = self.object.media.all().order_by('-created_at')
        context['media_form'] = MediaForm()
        context['session_activity_visits'] = self.request.session['activity_visits'].get(
            str(self.object.pk), 1
        )
        return context


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

def contact_us(request):
    if request.method == "POST":
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            form.save()  # save to database
            messages.success(request, "Thank you! Your message has been sent.")
            return redirect('contact_us')
    else:
        form = ContactMessageForm()

    return render(request, 'main/contact_us.html', {'form': form})

def about_us(request):
    return render(request, 'main/about_us.html')
