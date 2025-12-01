# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from .models import Activity, Media, Registration, UserHistory, Rating
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import CustomSignupForm, ContactMessageForm, RatingForm
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
        
        if date_filter == 'past':
            queryset = queryset.filter(date__lt=now).order_by('-date')
        else:
            queryset = queryset.filter(date__gte=now).order_by('date')
        
        if official_filter == 'true':
            queryset = queryset.filter(created_by__profile__is_organizer=True, date__gte=now)
        
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(location__icontains=q)
            )
        
        if category_filter:
            valid_categories = [choice[0] for choice in Activity.CATEGORY_CHOICES]
            if category_filter in valid_categories:
                queryset = queryset.filter(category=category_filter)
            else:
                category_filter = ''
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        q = request.GET.get('q', '')
        category_filter = request.GET.get('category', '')
        date_filter = request.GET.get('date_filter', 'upcoming')
        official_filter = request.GET.get('official', '')
        
        if category_filter:
            from .models import Activity
            valid_categories = [choice[0] for choice in Activity.CATEGORY_CHOICES]
            if category_filter not in valid_categories:
                category_filter = ''
        
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
        now = timezone.now()
        context.update({
            'query': q,
            'category_filter': category_filter,
            'date_filter': date_filter,
            'official_filter': official_filter,
            'category_choices': category_choices,
            'registered_ids': registered_ids,
            'now': now,
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
        media_form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user  # link to current user
            activity.save()
            
            # Handle media upload during creation (only one file allowed)
            if media_form.is_valid() and 'file' in request.FILES:
                media = media_form.save(commit=False)
                media.activity = activity
                media.created_by = request.user
                media.save()
            
            UserHistory.objects.create(
                user=request.user,
                action=f"Created activity: {activity.title}"
            )
            
            return redirect('activity_detail', pk=activity.pk)
    else:
        form = ActivityForm()
        media_form = MediaForm()
    return render(request, 'main/activity_form.html', {'form': form, 'media_form': media_form})

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
        """Handle media uploads - only allowed after event date if user is registered."""
        self.object = self.get_object()

        if not request.user.is_authenticated:
            return redirect('login')

        # Check if user can upload: event must have passed AND user must be registered
        now = timezone.now()
        event_passed = self.object.date < now
        is_registered = Registration.objects.filter(
            user=request.user,
            joined_activity=self.object,
            status='joined'
        ).exists()
        
        can_upload = event_passed and is_registered
        
        if not can_upload:
            if not event_passed:
                messages.error(request, "You can upload media if you registered and the event has passed.")
            elif not is_registered:
                messages.error(request, "You can upload media if you registered and the event has passed.")
            return redirect('activity_detail', pk=self.object.pk)

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
            
            messages.success(request, "Media uploaded successfully!")

            return redirect('activity_detail', pk=self.object.pk)

        # DEBUG: Show errors so we know what's wrong
        print("MEDIA UPLOAD ERRORS:", form.errors)
        messages.error(request, "Error uploading media. Please try again.")

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
        
        # Check if user can upload media (after event date AND registered)
        now = timezone.now()
        context['event_passed'] = self.object.date < now
        context['can_upload_media'] = context['event_passed'] and context['is_registered'] and self.request.user.is_authenticated
        
        # Get ratings and comments
        context['ratings'] = self.object.ratings.all().order_by('-created_at')
        context['rating_form'] = RatingForm()
        
        # Check if user has already rated
        if self.request.user.is_authenticated:
            context['user_rating'] = Rating.objects.filter(
                activity=self.object,
                user=self.request.user
            ).first()
        else:
            context['user_rating'] = None
        
        # Calculate average rating
        ratings_list = self.object.ratings.all()
        if ratings_list:
            context['average_rating'] = sum(r.rating for r in ratings_list) / len(ratings_list)
            context['total_ratings'] = len(ratings_list)
        else:
            context['average_rating'] = 0
            context['total_ratings'] = 0
        
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
    now = timezone.now()

    if activity.date < now:
        messages.error(request, "You cannot register for events that have already passed.")
        return redirect('activity_detail', pk=pk)

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
    return redirect('activity_detail', pk=pk)


@login_required
def cancel_registration(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    now = timezone.now()

    if activity.date < now:
        messages.error(request, "You cannot cancel registration for events that have already passed.")
        return redirect('activity_detail', pk=pk)

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
    return redirect('activity_detail', pk=pk)


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
def activity_delete(request, pk):
    """Delete an activity - only admin/superuser or creator can delete"""
    activity = get_object_or_404(Activity, pk=pk)
    
    # Check permissions: staff/superuser can delete any, creator can delete their own
    can_delete = request.user.is_staff or request.user.is_superuser or activity.created_by == request.user
    
    if not can_delete:
        messages.error(request, "You don't have permission to delete this activity.")
        return redirect('activity_detail', pk=pk)
    
    if request.method == 'POST':
        activity_title = activity.title
        activity.delete()
        
        UserHistory.objects.create(
            user=request.user,
            action=f"Deleted activity: {activity_title}"
        )
        
        messages.success(request, f"Activity '{activity_title}' has been deleted successfully.")
        return redirect('activity_list')
    
    # GET request - show confirmation (handled by modal in template)
    return redirect('activity_detail', pk=pk)

@login_required
def user_dashboard(request):
    """User dashboard with profile, statistics, and activities"""
    user = request.user
    now = timezone.now()
    
    # Get user profile
    profile = None
    try:
        profile = user.profile
    except:
        pass
    
    # Statistics
    activities_created = Activity.objects.filter(created_by=user).count()
    activities_registered = Registration.objects.filter(
        user=user, 
        status='joined',
        joined_activity__date__gte=now
    ).count()
    total_registrations = Registration.objects.filter(user=user, status='joined').count()
    
    # Recent activities created by user (last 5)
    my_activities = Activity.objects.filter(created_by=user).order_by('-created_at')[:5]
    
    # Upcoming activities user is registered for (next 5)
    upcoming_registered = Activity.objects.filter(
        registrations__user=user,
        registrations__status='joined',
        date__gte=now
    ).order_by('date')[:5]
    
    # Recent history - filter for registration and activity views only (exclude "Visited activities page")
    recent_history = UserHistory.objects.filter(
        user=user
    ).exclude(
        action='Visited activities page'
    ).filter(
        Q(action__startswith='Registered for activity:') | 
        Q(action__startswith='Visited activity:')
    ).order_by('-timestamp')[:10]
    
    # Get activity objects for clickable links - create a list with history and activity pairs
    recent_history_with_activities = []
    for history in recent_history:
        activity = None
        if 'Visited activity:' in history.action:
            activity_title = history.action.replace('Visited activity: ', '')
            activity = Activity.objects.filter(title=activity_title).first()
        elif 'Registered for activity:' in history.action:
            activity_title = history.action.replace('Registered for activity: ', '')
            activity = Activity.objects.filter(title=activity_title).first()
        recent_history_with_activities.append({
            'history': history,
            'activity': activity
        })
    
    # Set last visit cookie
    from django.http import HttpResponse
    from datetime import datetime
    response = render(request, 'main/user_dashboard.html', {
        'profile': profile,
        'activities_created': activities_created,
        'activities_registered': activities_registered,
        'total_registrations': total_registrations,
        'my_activities': my_activities,
        'upcoming_registered': upcoming_registered,
        'recent_history_with_activities': recent_history_with_activities,
        'now': now,
    })
    # Set cookie with formatted date/time
    last_visit_str = timezone.now().strftime("%B %d, %Y at %I:%M %p")
    response.set_cookie('last_visit', last_visit_str, max_age=31536000)  # 1 year expiry
    return response


@login_required
def user_history(request):
    # Exclude "Visited activities page" entries as they're noise
    all_history_items = UserHistory.objects.filter(
        user=request.user
    ).exclude(
        action='Visited activities page'
    ).order_by('-timestamp')
    
    # Pagination - get page number from request
    page = int(request.GET.get('page', 1))
    items_per_page = 10
    start = (page - 1) * items_per_page
    end = start + items_per_page
    
    # Get items for current page
    history_items = all_history_items[start:end]
    total_count = all_history_items.count()
    has_more = end < total_count
    remaining_count = total_count - end if has_more else 0

    # session data - get latest 5 activity views
    session_activity_visits = request.session.get('activity_visits', {})
    
    # Get latest 5 activities viewed (convert to list of tuples and sort by count, then take top 5)
    latest_activity_visits = []
    if session_activity_visits:
        # Get activities and their view counts
        activity_ids = list(session_activity_visits.keys())[:5]  # Get latest 5
        activities = Activity.objects.filter(id__in=activity_ids)
        for activity in activities:
            count = session_activity_visits.get(str(activity.id), 0)
            latest_activity_visits.append((activity, count))

    # cookie data - only last visit
    cookie_last_visit = request.COOKIES.get('last_visit')
    
    # Check if this is an AJAX request (for loading more)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return only the new items as HTML
        from django.template.loader import render_to_string
        html = render_to_string('main/user_history_items.html', {
            'history_items': history_items,
            'page': page,
            'has_more': has_more,
            'remaining_count': remaining_count,
        })
        return JsonResponse({'html': html, 'has_more': has_more, 'remaining_count': remaining_count})
    
    # Set last visit cookie
    response = render(request, 'main/user_history.html', {
        'history_items': history_items,
        'latest_activity_visits': latest_activity_visits,
        'cookie_last_visit': cookie_last_visit,
        'has_more': has_more,
        'total_count': total_count,
        'remaining_count': remaining_count,
        'page': page,
    })
    # Update cookie with current visit
    last_visit_str = timezone.now().strftime("%B %d, %Y at %I:%M %p")
    response.set_cookie('last_visit', last_visit_str, max_age=31536000)  # 1 year expiry
    return response



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


@login_required
def submit_rating(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating, created = Rating.objects.get_or_create(
                activity=activity,
                user=request.user,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'comment': form.cleaned_data.get('comment', '')
                }
            )
            if not created:
                rating.rating = form.cleaned_data['rating']
                rating.comment = form.cleaned_data.get('comment', '')
                rating.save()
                messages.success(request, "Your rating has been updated!")
            else:
                messages.success(request, "Thank you for rating this event!")
            
            UserHistory.objects.create(
                user=request.user,
                action=f"Rated activity: {activity.title}"
            )
            
            return redirect('activity_detail', pk=pk)
        else:
            messages.error(request, "Please select a rating.")
            return redirect('activity_detail', pk=pk)
    
    return redirect('activity_detail', pk=pk)


@login_required
def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    
    try:
        profile = profile_user.profile
    except:
        profile = None
    
    activities_created = Activity.objects.filter(created_by=profile_user).count()
    activities_registered = Registration.objects.filter(
        user=profile_user,
        status='joined'
    ).count()
    
    recent_activities = Activity.objects.filter(created_by=profile_user).order_by('-created_at')[:5]
    recent_ratings = Rating.objects.filter(user=profile_user).order_by('-created_at')[:5]
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'activities_created': activities_created,
        'activities_registered': activities_registered,
        'recent_activities': recent_activities,
        'recent_ratings': recent_ratings,
    }
    
    return render(request, 'main/user_profile.html', context)

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
    
    # Set last visit cookie
    response = render(request, 'main/home.html', context)
    # Set cookie with formatted date/time (only for authenticated users)
    if request.user.is_authenticated:
        last_visit_str = timezone.now().strftime("%B %d, %Y at %I:%M %p")
        response.set_cookie('last_visit', last_visit_str, max_age=31536000)  # 1 year expiry
    return response
