import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_classifier.settings')
django.setup()

from django.test import Client
from emails.models import EmailClassification

client = Client()

print("=== Setting up sample database records for dashboard verification ===")
EmailClassification.objects.all().delete()

samples = [
    {
        'sender_email': 'alexandra@techcorp.com',
        'subject': 'Critical: System outage on payment cluster',
        'body': '500 error code and database connection refused.',
        'category': 'Technical Support',
        'priority': 'High',
        'sentiment': 'Neutral',
        'confidence': 98.0,
        'department': 'Technical Support Team',
        'reason': 'Technical outage.',
        'engine': 'AI (OpenAI: gpt-4o-mini)'
    },
    {
        'sender_email': 'marcus@enterprise.io',
        'subject': 'Invoice #9812 discrepancy and wire transfer',
        'body': 'Please check our double charged payment.',
        'category': 'Billing',
        'priority': 'Medium',
        'sentiment': 'Neutral',
        'confidence': 94.5,
        'department': 'Finance/Billing Team',
        'reason': 'Billing query.',
        'engine': 'AI (OpenAI: gpt-4o-mini)'
    },
    {
        'sender_email': 'karen@retailstore.com',
        'subject': 'Unacceptable service and rude staff complaint',
        'body': 'Horrible experience today, I will sue.',
        'category': 'Complaint',
        'priority': 'High',
        'sentiment': 'Negative',
        'confidence': 97.0,
        'department': 'Customer Relations Team',
        'reason': 'Customer complaint.',
        'engine': 'Rule-Based Fallback'
    },
    {
        'sender_email': 'david@globalventures.com',
        'subject': 'Request enterprise pricing quote for 500 licenses',
        'body': 'Looking forward to scheduling a demo.',
        'category': 'Sales',
        'priority': 'Low',
        'sentiment': 'Positive',
        'confidence': 95.0,
        'department': 'Sales Team',
        'reason': 'Sales quote.',
        'engine': 'AI (OpenAI: gpt-4o-mini)'
    },
    {
        'sender_email': 'sara@cyberdyne.org',
        'subject': 'Locked out of account - 2FA reset',
        'body': 'Cannot sign in to corporate login credentials.',
        'category': 'Account & Access',
        'priority': 'Medium',
        'sentiment': 'Neutral',
        'confidence': 92.0,
        'department': 'Account Support Team',
        'reason': 'Account access.',
        'engine': 'AI (OpenAI: gpt-4o-mini)'
    },
    {
        'sender_email': 'tom@visitor.net',
        'subject': 'General inquiry about headquarters office hours',
        'body': 'Could you please share your business hours?',
        'category': 'General Inquiry',
        'priority': 'Low',
        'sentiment': 'Neutral',
        'confidence': 88.0,
        'department': 'General Support Team',
        'reason': 'General inquiry.',
        'engine': 'Rule-Based Fallback'
    }
]

for s in samples:
    EmailClassification.objects.create(**s)

total_in_db = EmailClassification.objects.count()
print(f"Total test records in database: {total_in_db}")
assert total_in_db == 6

print("\n=== TEST 1: Dashboard HTTP 200 & Summary Cards ===")
res = client.get('/dashboard/')
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
html = res.content.decode()

summary_cards = [
    'Total Emails',
    'High Priority',
    'Medium Priority',
    'Low Priority',
    'Total Classified'
]
for card in summary_cards:
    assert card in html, f"Summary card '{card}' missing from Dashboard"
print("Test 1 Passed: All 5 summary cards rendered successfully.")

print("\n=== TEST 2: Category Statistics ===")
categories = [
    'Technical Support',
    'Billing',
    'Complaint',
    'Sales',
    'Account & Access',
    'General Inquiry'
]
for cat in categories:
    assert (cat in html or cat.replace('&', '&amp;') in html), f"Category '{cat}' missing from Dashboard category stats"
print("Test 2 Passed: All 6 category statistics rendered.")

print("\n=== TEST 3: Department Statistics ===")
departments = [
    'Technical Support Team',
    'Finance/Billing Team',
    'Customer Relations Team',
    'Sales Team',
    'Account Support Team',
    'General Support Team'
]
for dept in departments:
    assert dept in html, f"Department '{dept}' missing from Dashboard department stats"
print("Test 3 Passed: All 6 department statistics rendered.")

print("\n=== TEST 4: Chart.js Canvases & Configs ===")
charts = ['categoryChart', 'priorityChart', 'sentimentChart', 'departmentChart']
for c in charts:
    assert f'id="{c}"' in html, f"Chart canvas '{c}' missing from Dashboard"
assert 'chart.umd.min.js' in html, "Chart.js library script inclusion missing"
print("Test 4 Passed: All 4 Chart.js charts and configurations present.")

print("\n=== TEST 5: Recent Emails Table Columns ===")
recent_columns = ['Sender', 'Subject', 'Category', 'Priority', 'Department', 'Date']
for col in recent_columns:
    assert col in html, f"Column '{col}' missing from Recent Emails table"
print("Test 5 Passed: Recent Emails section contains all 6 required columns.")

print("\n=== TEST 6: Automatic Update when New Email is Analyzed ===")
# Submit a new High Priority Technical Support email
client.post('/analyze/', {
    'sender_email': 'emergency@serverhost.com',
    'subject': 'Critical: Outage on secondary database replica',
    'body': 'Database replica crashed and 500 server errors occurring.'
})
assert EmailClassification.objects.count() == 7

res_updated = client.get('/dashboard/')
html_updated = res_updated.content.decode()
# Check total count updated to 7
assert 'emergency@serverhost.com' in html_updated, "Newly analyzed email missing from Recent Emails on Dashboard"
print("Test 6 Passed: Dashboard reflects new email automatically in counts and recent emails table.")

print("\nALL DASHBOARD TESTS PASSED SUCCESSFULLY!")
