import logging

from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import EmailClassification
from .classifier import classify_email
from .ai_service import classify_email_with_ai, has_ai_provider_configured

logger = logging.getLogger(__name__)

def home(request):
    """
    Landing page for AI Email Classification and Routing System.
    """
    total_emails = EmailClassification.objects.count()
    recent_emails = EmailClassification.objects.all()[:5]
    context = {
        'title': 'AI Email Classification and Routing System',
        'total_emails': total_emails,
        'recent_emails': recent_emails,
    }
    return render(request, 'emails/home.html', context)

def dashboard(request):
    """
    Overview dashboard showing summary cards, category stats, department stats,
    Chart.js datasets, and recent triage logs.
    """
    import json

    total_emails = EmailClassification.objects.count()
    high_prio_count = EmailClassification.objects.filter(priority='High').count()
    med_prio_count = EmailClassification.objects.filter(priority='Medium').count()
    low_prio_count = EmailClassification.objects.filter(priority='Low').count()
    total_classified = total_emails

    # Category statistics
    category_labels = [
        'Technical Support',
        'Billing',
        'Complaint',
        'Sales',
        'Account & Access',
        'General Inquiry',
    ]
    category_stats = {
        cat: EmailClassification.objects.filter(category=cat).count() for cat in category_labels
    }

    # Department statistics
    department_labels = [
        'Technical Support Team',
        'Finance/Billing Team',
        'Customer Relations Team',
        'Sales Team',
        'Account Support Team',
        'General Support Team',
    ]
    department_stats = {
        dept: EmailClassification.objects.filter(department=dept).count() for dept in department_labels
    }

    # Sentiment statistics
    sentiment_labels = ['Positive', 'Neutral', 'Negative']
    sentiment_stats = {
        sent: EmailClassification.objects.filter(sentiment=sent).count() for sent in sentiment_labels
    }

    recent_emails = EmailClassification.objects.all()[:10]

    # Chart.js JSON structures
    category_chart = {
        'labels': category_labels,
        'data': [category_stats[cat] for cat in category_labels],
    }

    priority_chart = {
        'labels': ['High', 'Medium', 'Low'],
        'data': [high_prio_count, med_prio_count, low_prio_count],
    }

    sentiment_chart = {
        'labels': sentiment_labels,
        'data': [sentiment_stats[sent] for sent in sentiment_labels],
    }

    department_chart = {
        'labels': department_labels,
        'data': [department_stats[dept] for dept in department_labels],
    }

    context = {
        'title': 'Dashboard | AI Email Classification & Routing',
        # Summary Cards
        'total_emails': total_emails,
        'high_prio_count': high_prio_count,
        'med_prio_count': med_prio_count,
        'low_prio_count': low_prio_count,
        'total_classified': total_classified,
        # Category Stats
        'category_stats': category_stats,
        # Department Stats
        'department_stats': department_stats,
        # Sentiment Stats
        'sentiment_stats': sentiment_stats,
        # Chart JSONs
        'category_chart_json': json.dumps(category_chart),
        'priority_chart_json': json.dumps(priority_chart),
        'sentiment_chart_json': json.dumps(sentiment_chart),
        'department_chart_json': json.dumps(department_chart),
        # Recent Emails
        'recent_emails': recent_emails,
    }
    return render(request, 'emails/dashboard.html', context)

def analyze(request):
    """
    Email analysis workspace where users submit an email to classify, prioritize,
    determine sentiment, map to department, explain reason, and persist to SQLite.
    """
    result = None
    form_data = {
        'sender_email': '',
        'subject': '',
        'body': '',
    }

    if request.method == 'POST':
        logger.info('Analyze Email POST received')
        sender_email = request.POST.get('sender_email', '').strip()
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()

        form_data = {
            'sender_email': sender_email,
            'subject': subject,
            'body': body,
        }

        if not sender_email or not subject or not body:
            messages.error(request, 'Please fill in all required fields: Sender Email, Subject, and Email Body.')
        else:
            # 1. Analyze email using AI model (with automatic rule-based fallback)
            classification = classify_email_with_ai(sender_email, subject, body)

            # 2. Save complete result to EmailClassification model
            record = EmailClassification.objects.create(
                sender_email=sender_email,
                subject=subject,
                body=body,
                category=classification['category'],
                priority=classification['priority'],
                sentiment=classification['sentiment'],
                confidence=classification['confidence'],
                department=classification['department'],
                reason=classification['reason'],
                engine=classification.get('engine', 'AI (LLM)'),
            )
            logger.info('Final classification saved')

            result = record
            engine_label = record.engine
            messages.success(request, f'Email analyzed via {engine_label} and routed to {record.department}!')

    has_api_key = has_ai_provider_configured()

    context = {
        'title': 'Analyze Email | AI Email Classification & Routing',
        'result': result,
        'form_data': form_data,
        'has_api_key': has_api_key,
    }
    return render(request, 'emails/analyze.html', context)

def history(request):
    """
    Email history logs listing past classified and routed emails with
    search by sender/subject and filters by category, priority, sentiment, and department.
    """
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    priority_filter = request.GET.get('priority', '').strip()
    sentiment_filter = request.GET.get('sentiment', '').strip()
    department_filter = request.GET.get('department', '').strip()

    emails = EmailClassification.objects.all()
    total_count = emails.count()

    # Apply search filter
    if search_query:
        emails = emails.filter(
            Q(sender_email__icontains=search_query) | Q(subject__icontains=search_query)
        )

    # Apply category filter
    if category_filter:
        emails = emails.filter(category=category_filter)

    # Apply priority filter
    if priority_filter:
        emails = emails.filter(priority=priority_filter)

    # Apply sentiment filter
    if sentiment_filter:
        emails = emails.filter(sentiment=sentiment_filter)

    # Apply department filter
    if department_filter:
        emails = emails.filter(department=department_filter)

    categories = [
        'Technical Support',
        'Billing',
        'Complaint',
        'Sales',
        'Account & Access',
        'General Inquiry',
    ]

    priorities = ['High', 'Medium', 'Low']
    sentiments = ['Positive', 'Neutral', 'Negative']
    departments = [
        'Technical Support Team',
        'Finance/Billing Team',
        'Customer Relations Team',
        'Sales Team',
        'Account Support Team',
        'General Support Team',
    ]

    context = {
        'title': 'Email History | AI Email Classification & Routing',
        'emails': emails,
        'total_count': total_count,
        'filtered_count': emails.count(),
        'categories': categories,
        'priorities': priorities,
        'sentiments': sentiments,
        'departments': departments,
        'filters': {
            'search': search_query,
            'category': category_filter,
            'priority': priority_filter,
            'sentiment': sentiment_filter,
            'department': department_filter,
        },
    }
    return render(request, 'emails/history.html', context)

def email_detail(request, email_id):
    """
    Detailed audit view of an individual email classification record.
    Displays sender, subject, complete email body, category, priority, sentiment,
    confidence, assigned department, AI reason, and date/time.
    """
    email = get_object_or_404(EmailClassification, id=email_id)
    context = {
        'title': f'Email #{email.id}: {email.subject} | AI Email Classifier',
        'email': email,
    }
    return render(request, 'emails/detail.html', context)
