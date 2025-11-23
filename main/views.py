# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from .models import Activity, Media, Registration, UserHistory
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import CustomSignupForm, ContactMessageForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView as DjangoLoginView

class ActivityListView(ListView):
    model = Activity
    template_name = "main/activity_list.html"
    context_object_name = "activities"

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        category_filter = self.request.GET.get('category', '')
        date_filter = self.request.GET.get('date_filter', 'upcoming')
        official_filter = self.request.GET.get('official', '')
        
        now = timezone.now()
        
        queryset = Activity.objects.all()
        
        # Filter by date (upcoming vs past)
        if date_filter == 'past':
            queryset = queryset.filter(date__lt=now).order_by('-date')
        else:  # default to 'upcoming'
            queryset = queryset.filter(date__gte=now).order_by('date')
        
        # Filter by official events (organizer events) - only for upcoming
        if official_filter == 'true':
            queryset = queryset.filter(created_by__profile__is_organizer=True)
        
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
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        q = request.GET.get('q', '')
        category_filter = request.GET.get('category', '')
        date_filter = request.GET.get('date_filter', 'upcoming')
        official_filter = request.GET.get('official', '')
        
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

        # Add current time for relative date calculations
        from django.utils import timezone
        context.update({
            'query': q,
            'category_filter': category_filter,
            'date_filter': date_filter,
            'official_filter': official_filter,
            'category_choices': category_choices,
            'registered_ids': registered_ids,
            'now': timezone.now(),
        })

        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)

        if self.request.user.is_authenticated:
            UserHistory.objects.create(
                user=self.request.user,
                action="Visited activities page"
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
        # Check if user is registered
        context['is_registered'] = False
        if self.request.user.is_authenticated:
            context['is_registered'] = Registration.objects.filter(
                user=self.request.user,
                joined_activity=self.object,
                status='joined'
            ).exists()
        # Get participant count
        context['participant_count'] = self.object.registrations.filter(status='joined').count()
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
def toggle_featured(request, pk):
    """Toggle featured status of an activity (staff only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('activity_detail', pk=pk)
    
    activity = get_object_or_404(Activity, pk=pk)
    
    if request.method == 'POST':
        activity.is_featured = not activity.is_featured
        activity.save()
        
        status = "featured" if activity.is_featured else "unfeatured"
        messages.success(request, f"Activity '{activity.title}' has been {status}.")
        
        UserHistory.objects.create(
            user=request.user,
            action=f"Marked activity '{activity.title}' as {status}"
        )
    
    return redirect('activity_detail', pk=pk)

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

class CustomLoginView(DjangoLoginView):
    template_name = 'registration/login.html'
    
    def get(self, request, *args, **kwargs):
        failed_attempts = request.session.get('failed_login_attempts', 0)
        context = self.get_context_data()
        context['failed_attempts'] = failed_attempts
        return self.render_to_response(context)
    
    def form_valid(self, form):
        if 'failed_login_attempts' in self.request.session:
            del self.request.session['failed_login_attempts']
        
        response = super().form_valid(form)
        
        if self.request.user.is_authenticated:
            UserHistory.objects.create(
                user=self.request.user,
                action="Logged in"
            )
        
        return response
    
    def form_invalid(self, form):
        failed_attempts = self.request.session.get('failed_login_attempts', 0) + 1
        self.request.session['failed_login_attempts'] = failed_attempts
        
        context = self.get_context_data(form=form)
        context['failed_attempts'] = failed_attempts
        return self.render_to_response(context)

def home(request):
    """Homepage view with hero section and statistics"""
    from django.db.models import Count
    from datetime import timedelta
    
    # Calculate statistics
    total_activities = Activity.objects.count()
    total_participants = Registration.objects.filter(status='joined').count()
    
    # Upcoming activities (next 30 days)
    today = timezone.now()
    next_month = today + timedelta(days=30)
    upcoming_count = Activity.objects.filter(date__gte=today, date__lte=next_month).count()
    
    # Activities by category
    category_counts = Activity.objects.values('category').annotate(count=Count('id'))
    categories_available = len(category_counts)
    
    # Featured upcoming activities (random 4 from featured upcoming activities)
    featured_upcoming = Activity.objects.filter(date__gte=today, is_featured=True)
    if featured_upcoming.exists():
        import random
        featured_list = list(featured_upcoming)
        if len(featured_list) > 4:
            featured_activities = random.sample(featured_list, 4)
        else:
            featured_activities = featured_list
    else:
        featured_activities = Activity.objects.filter(date__gte=today).order_by('date')[:4]
    
    # Get all categories for highlights
    all_categories = Activity.CATEGORY_CHOICES
    
    # Session tracking for homepage
    session_visit_count = request.session.get('home_visits', 0) + 1
    request.session['home_visits'] = session_visit_count
    
    context = {
        'total_activities': total_activities,
        'total_participants': total_participants,
        'upcoming_count': upcoming_count,
        'categories_available': categories_available,
        'category_counts': category_counts,
        'featured_activities': featured_activities,
        'all_categories': all_categories,
        'session_visit_count': session_visit_count,
    }
    
    return render(request, 'main/home.html', context)
