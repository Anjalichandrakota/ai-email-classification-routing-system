import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_classifier.settings')
django.setup()

from django.test import Client
from emails.models import EmailClassification

client = Client()

print("=== Setting up sample test records ===")
# Ensure we have representative test records in the database
EmailClassification.objects.all().delete()

rec1 = EmailClassification.objects.create(
    sender_email='sarah.connor@techcorp.io',
    subject='Critical database connection timeout in production cluster',
    body='Our cluster in US-East is failing with connection timeout exceptions. All queries are failing.',
    category='Technical Support',
    priority='High',
    sentiment='Neutral',
    confidence=96.5,
    department='Technical Support Team',
    reason='Classified as Technical Support due to production cluster failure and timeout exceptions.',
    engine='AI (OpenAI: gpt-4o-mini)'
)

rec2 = EmailClassification.objects.create(
    sender_email='kevin.bacon@enterprise.com',
    subject='Overdue invoice #INV-2026-8812 refund request',
    body='We were charged twice on our Visa card for invoice 8812. Please process a refund immediately.',
    category='Billing',
    priority='Medium',
    sentiment='Neutral',
    confidence=94.0,
    department='Finance/Billing Team',
    reason='Classified as Billing due to invoice, double charge, and refund request.',
    engine='AI (OpenAI: gpt-4o-mini)'
)

rec3 = EmailClassification.objects.create(
    sender_email='furious.customer@consumer.org',
    subject='Appalling customer service experience and rude staff',
    body='Your staff was extremely rude and unhelpful. I demand a full refund or I will escalate to legal counsel.',
    category='Complaint',
    priority='High',
    sentiment='Negative',
    confidence=98.0,
    department='Customer Relations Team',
    reason='Classified as Complaint due to angry sentiment, rude staff complaint, and legal threats.',
    engine='Rule-Based Fallback'
)

rec4 = EmailClassification.objects.create(
    sender_email='buyer@acmecorp.com',
    subject='Request enterprise quote for 500 licenses',
    body='We love your platform and want to schedule a product demo for 500 users next month.',
    category='Sales',
    priority='Low',
    sentiment='Positive',
    confidence=95.0,
    department='Sales Team',
    reason='Classified as Sales due to request for pricing quote and demo for 500 licenses.',
    engine='AI (OpenAI: gpt-4o-mini)'
)

print(f"Total test records created: {EmailClassification.objects.count()}")

print("\n=== TEST 1: Email History Page Table Columns ===")
res_hist = client.get('/history/')
assert res_hist.status_code == 200, f"Expected 200, got {res_hist.status_code}"
html_hist = res_hist.content.decode()

columns = ['Sender', 'Subject', 'Category', 'Priority', 'Sentiment', 'Department', 'Confidence', 'Date', 'Action']
for col in columns:
    assert col in html_hist, f"Column '{col}' missing from Email History table"
assert 'View Details' in html_hist, "'View Details' action missing from Email History table"
print("Test 1 Passed: Email History page renders with all 9 required columns and View Details buttons.")

print("\n=== TEST 2: Search Functionality ===")
# Search by sender
res_search_sender = client.get('/history/?search=sarah.connor')
assert res_search_sender.status_code == 200
html_s1 = res_search_sender.content.decode()
assert 'sarah.connor@techcorp.io' in html_s1
assert 'kevin.bacon@enterprise.com' not in html_s1
print("Search by sender verified.")

# Search by subject
res_search_subj = client.get('/history/?search=Appalling')
assert res_search_subj.status_code == 200
html_s2 = res_search_subj.content.decode()
assert 'Appalling customer service experience' in html_s2
assert 'Critical database connection' not in html_s2
print("Search by subject verified.")

print("\n=== TEST 3: Filters Functionality ===")
# Filter by Category
res_cat = client.get('/history/?category=Billing')
assert res_cat.status_code == 200
html_cat = res_cat.content.decode()
assert 'kevin.bacon@enterprise.com' in html_cat
assert 'sarah.connor@techcorp.io' not in html_cat
print("Filter by Category verified.")

# Filter by Priority
res_prio = client.get('/history/?priority=Low')
assert res_prio.status_code == 200
html_prio = res_prio.content.decode()
assert 'buyer@acmecorp.com' in html_prio
assert 'sarah.connor@techcorp.io' not in html_prio
print("Filter by Priority verified.")

# Filter by Sentiment
res_sent = client.get('/history/?sentiment=Negative')
assert res_sent.status_code == 200
html_sent = res_sent.content.decode()
assert 'furious.customer@consumer.org' in html_sent
assert 'buyer@acmecorp.com' not in html_sent
print("Filter by Sentiment verified.")

# Filter by Department
res_dept = client.get('/history/?department=Finance/Billing+Team')
assert res_dept.status_code == 200
html_dept = res_dept.content.decode()
assert 'kevin.bacon@enterprise.com' in html_dept
assert 'furious.customer@consumer.org' not in html_dept
print("Filter by Department verified.")

# Combined filter
res_comb = client.get('/history/?category=Technical+Support&priority=High')
assert res_comb.status_code == 200
html_comb = res_comb.content.decode()
assert 'sarah.connor@techcorp.io' in html_comb
assert 'furious.customer@consumer.org' not in html_comb
print("Combined Category + Priority filter verified.")

print("\n=== TEST 4: Email Details Page View ===")
res_detail = client.get(f'/history/{rec1.id}/')
assert res_detail.status_code == 200, f"Expected 200, got {res_detail.status_code}"
html_detail = res_detail.content.decode()

required_detail_fields = [
    ('Sender', 'sarah.connor@techcorp.io'),
    ('Subject', 'Critical database connection timeout in production cluster'),
    ('Body', 'Our cluster in US-East is failing with connection timeout exceptions'),
    ('Category', 'Technical Support'),
    ('Priority', 'High'),
    ('Sentiment', 'Neutral'),
    ('Confidence', '96.5%'),
    ('Department', 'Technical Support Team'),
    ('Reason', 'Classified as Technical Support due to production cluster failure'),
]

for label, val in required_detail_fields:
    assert val in html_detail, f"Expected detail field '{label}' with value '{val}' missing in details view"

print("Test 4 Passed: Email Details page displays all required fields with complete fidelity.")

print("\n=== TEST 5: Non-existent Email Detail View (404 check) ===")
res_404 = client.get('/history/999999/')
assert res_404.status_code == 404, f"Expected 404, got {res_404.status_code}"
print("Test 5 Passed: Non-existent email ID returns 404 as expected.")

print("\n=== TEST 6: Dashboard & Analyze regression check ===")
res_dash = client.get('/dashboard/')
assert res_dash.status_code == 200
assert 'Technical Support' in res_dash.content.decode()

res_ana = client.get('/analyze/')
assert res_ana.status_code == 200
assert 'Analyze Email' in res_ana.content.decode()

print("Test 6 Passed: Dashboard and Analyze pages remain fully functional.")

print("\nALL HISTORY & DETAILS TESTS PASSED SUCCESSFULLY!")
