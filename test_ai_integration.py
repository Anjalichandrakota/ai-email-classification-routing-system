import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_classifier.settings')
django.setup()

from django.test import Client
from unittest.mock import patch, MagicMock
from emails.models import EmailClassification
from emails.ai_service import classify_email_with_ai

client = Client()

print("=== TEST 1: Fallback Classification (No API Key) ===")
# Ensure no AI keys
with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'GROQ_API_KEY': '', 'GEMINI_API_KEY': '', 'AI_API_KEY': ''}, clear=True):
    res_fb = classify_email_with_ai(
        'test@user.com',
        'Emergency: Production server down and 500 internal server error',
        'Backend crashed completely and checkout API is failing'
    )
    assert res_fb['category'] == 'Technical Support', f"Expected Technical Support, got {res_fb['category']}"
    assert res_fb['department'] == 'Technical Support Team'
    assert res_fb['priority'] == 'High'
    assert 'Rule-Based Fallback' in res_fb['engine']
    print("Fallback classification logic verified successfully.")

print("\n=== TEST 2: Email Submission with Fallback via HTTP POST ===")
initial_count = EmailClassification.objects.count()
post_resp = client.post('/analyze/', {
    'sender_email': 'billing.user@client.com',
    'subject': 'Double charged on invoice #INV-4921 refund request',
    'body': 'Please refund the unauthorized charge on our credit card account.'
})
assert post_resp.status_code == 200
html = post_resp.content.decode()
assert 'Saved to Database' in html
assert 'Billing' in html
assert 'Finance/Billing Team' in html
assert 'Rule-Based Fallback' in html
assert EmailClassification.objects.count() == initial_count + 1
print("Email submission with fallback saved to DB and rendered correctly.")

print("\n=== TEST 3: AI Classification with Structured JSON Response ===")
mock_openai_response = MagicMock()
mock_choice = MagicMock()
mock_choice.message.content = '''{
  "category": "Sales",
  "priority": "Low",
  "sentiment": "Positive",
  "confidence": 94.2,
  "department": "Sales Team",
  "reason": "Inbound prospect inquiring about enterprise annual licensing with great enthusiasm."
}'''
mock_openai_response.choices = [mock_choice]

with patch('openai.OpenAI') as MockOpenAI:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    MockOpenAI.return_value = mock_client
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-mock-key-12345'}):
        ai_resp = classify_email_with_ai(
            'prospective@partner.com',
            'Excited to purchase enterprise solution for our company',
            'We love your product and would like to buy 100 enterprise seats!'
        )
        assert ai_resp['category'] == 'Sales'
        assert ai_resp['department'] == 'Sales Team'
        assert ai_resp['priority'] == 'Low'
        assert ai_resp['sentiment'] == 'Positive'
        assert ai_resp['confidence'] == 94.2
        assert 'AI (OpenAI' in ai_resp['engine']
        print("AI classification with structured JSON parsed and verified successfully.")

print("\n=== TEST 4: Email Submission with AI via HTTP POST ===")
with patch('openai.OpenAI') as MockOpenAI:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    MockOpenAI.return_value = mock_client
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-mock-key-12345'}):
        post_ai = client.post('/analyze/', {
            'sender_email': 'prospective@partner.com',
            'subject': 'Excited to purchase enterprise solution for our company',
            'body': 'We love your product and would like to buy 100 enterprise seats!'
        })
        assert post_ai.status_code == 200
        ai_html = post_ai.content.decode()
        assert 'Saved to Database' in ai_html
        assert 'Sales' in ai_html
        assert 'Sales Team' in ai_html
        assert 'AI (OpenAI' in ai_html
        
        latest = EmailClassification.objects.first()
        assert latest.category == 'Sales'
        assert latest.department == 'Sales Team'
        assert 'AI (OpenAI' in latest.engine
        print("AI classification saved to DB and rendered with AI badge correctly.")

print("\n=== TEST 5: AI API Error / Invalid Response -> Graceful Fallback ===")
# Test that an unexpected network error or invalid JSON does NOT crash the site, but triggers fallback
with patch('openai.OpenAI') as MockOpenAI:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception('Connection timeout: 504 Gateway Timeout')
    MockOpenAI.return_value = mock_client
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-mock-key-12345'}):
        fallback_call = classify_email_with_ai(
            'customer@angry.com',
            'Unacceptable service - speaking to legal counsel',
            'You charged me for services never rendered and your support is rude.'
        )
        assert fallback_call['category'] == 'Complaint'
        assert fallback_call['department'] == 'Customer Relations Team'
        assert 'Rule-Based Fallback' in fallback_call['engine']
        print("Network error gracefully handled and routed via Rule-Based Fallback.")

print("\n=== TEST 6: AI Model wrapping JSON in markdown fences ===")
mock_fenced_response = MagicMock()
mock_fenced_choice = MagicMock()
mock_fenced_choice.message.content = '''```json
{
  "category": "Account & Access",
  "priority": "Medium",
  "sentiment": "Neutral",
  "confidence": 91.5,
  "department": "Account Support Team",
  "reason": "Customer requesting 2FA authenticator reset after being locked out."
}
```'''
mock_fenced_response.choices = [mock_fenced_choice]

with patch('openai.OpenAI') as MockOpenAI:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_fenced_response
    MockOpenAI.return_value = mock_client
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-mock-key-12345'}):
        fenced_resp = classify_email_with_ai(
            'staff@company.org',
            '2FA authenticator reset request',
            'I cannot log in because my 2FA app was wiped.'
        )
        assert fenced_resp['category'] == 'Account & Access'
        assert fenced_resp['department'] == 'Account Support Team'
        assert fenced_resp['confidence'] == 91.5
        print("Markdown-wrapped JSON response handled and normalized successfully.")

print("\nALL 6 VERIFICATION TESTS PASSED SUCCESSFULLY!")
