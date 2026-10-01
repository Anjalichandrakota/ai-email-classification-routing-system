import json
import os
from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, TestCase

from .ai_service import _call_gemini_api, classify_email_with_ai
from .models import EmailClassification


GEMINI_CLASSIFICATION = {
	'category': 'Billing',
	'priority': 'High',
	'sentiment': 'Neutral',
	'confidence': 93.0,
	'reason': 'The customer reports a duplicate payment.',
}


class GeminiServiceTests(SimpleTestCase):
	def test_gemini_is_primary_when_multiple_providers_are_configured(self):
		gemini_result = {
			**GEMINI_CLASSIFICATION,
			'department': 'Finance/Billing Team',
			'engine': 'AI (Gemini: test-model)',
		}
		with patch.dict(os.environ, {
			'GEMINI_API_KEY': 'test-gemini-key',
			'GROQ_API_KEY': 'test-groq-key',
			'OPENAI_API_KEY': 'test-openai-key',
		}, clear=True):
			with patch('emails.ai_service._call_gemini_api', return_value=gemini_result) as gemini_call, \
				 patch('emails.ai_service._call_groq_api') as groq_call, \
				 patch('emails.ai_service._call_openai_api') as openai_call:
				result = classify_email_with_ai('sender@example.test', 'subject', 'body')

		self.assertEqual(result['engine'], 'AI (Gemini: test-model)')
		gemini_call.assert_called_once_with(
			'test-gemini-key', 'Sender: sender@example.test\nSubject: subject\n\nBody:\nbody')
		groq_call.assert_not_called()
		openai_call.assert_not_called()

	@patch('requests.post')
	def test_gemini_request_uses_environment_key_and_sends_email_fields(self, post):
		response = MagicMock()
		response.json.return_value = {
			'candidates': [{'content': {'parts': [{'text': json.dumps(GEMINI_CLASSIFICATION)}]}}]
		}
		post.return_value = response
		user_content = 'Sender: sender@example.test\nSubject: Payment charged twice\n\nBody:\nDuplicate payment.'

		with patch.dict(os.environ, {
			'GEMINI_API_KEY': 'test-gemini-key',
			'GEMINI_MODEL': 'gemini-test-model',
		}, clear=True):
			result = _call_gemini_api(os.environ['GEMINI_API_KEY'], user_content)

		request_url, request = post.call_args
		self.assertTrue(request_url[0].startswith('https://generativelanguage.googleapis.com/v1beta/models/'))
		self.assertIn('gemini-test-model:generateContent', request_url[0])
		self.assertNotIn('key=', request_url[0])
		self.assertEqual(request['headers']['x-goog-api-key'], 'test-gemini-key')
		self.assertEqual(
			request['json']['generationConfig']['responseFormat']['text']['mimeType'],
			'APPLICATION_JSON',
		)
		self.assertNotIn('temperature', request['json']['generationConfig'])
		sent_text = request['json']['contents'][0]['parts'][0]['text']
		for expected in ('sender@example.test', 'Payment charged twice', 'Duplicate payment.'):
			self.assertIn(expected, sent_text)
		self.assertEqual(result['category'], 'Billing')
		self.assertEqual(result['department'], 'Finance/Billing Team')
		self.assertEqual(result['priority'], 'High')
		self.assertEqual(result['sentiment'], 'Neutral')
		self.assertEqual(result['confidence'], 93.0)
		self.assertEqual(result['reason'], GEMINI_CLASSIFICATION['reason'])

	@patch('requests.post')
	def test_gemini_http_failure_logs_sanitized_diagnostics(self, post):
		api_key = 'diagnostic-test-key'
		response = MagicMock()
		response.status_code = 400
		response.raise_for_status.side_effect = requests.HTTPError('request rejected')
		response.json.return_value = {'error': {'message': f'API key not valid: {api_key}'}}
		post.return_value = response

		with patch.dict(os.environ, {
			'GEMINI_API_KEY': api_key,
			'GEMINI_MODEL': 'gemini-test-model',
		}, clear=True):
			with self.assertLogs('emails.ai_service', level='INFO') as captured:
				with self.assertRaises(requests.HTTPError):
					_call_gemini_api(api_key, 'harmless diagnostic request')

		logs = '\n'.join(captured.output)
		self.assertIn('Gemini request started', logs)
		self.assertIn('model=gemini-test-model', logs)
		self.assertIn('Gemini HTTP status: 400', logs)
		self.assertIn('Gemini request failed', logs)
		self.assertNotIn(api_key, logs)
		self.assertNotIn('x-goog-api-key', logs)

	@patch('requests.post')
	def test_invalid_gemini_response_falls_back_without_raising(self, post):
		response = MagicMock()
		response.json.return_value = {
			'candidates': [{'content': {'parts': [{'text': 'not valid JSON'}]}}]
		}
		post.return_value = response

		with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-gemini-key'}, clear=True):
			result = classify_email_with_ai(
				'sender@example.test',
				'Application keeps crashing',
				'The application crashes whenever I try to upload a file. Please help.',
			)

		self.assertEqual(result['engine'], 'Rule-Based Fallback')
		self.assertEqual(result['category'], 'Technical Support')
		self.assertIn('Fallback:', result['reason'])
		self.assertEqual(result['department'], 'Technical Support Team')

	def test_requested_demo_samples_match_rule_fallback_categories(self):
		samples = [
			('Unable to login to my account', 'I have tried several times but I cannot log in. Please help me access my account.', 'Account & Access'),
			('Payment charged twice', 'I was charged twice for the same order. Please check and refund the duplicate payment.', 'Billing'),
			('Application keeps crashing', 'The application crashes whenever I try to upload a file. Please help.', 'Technical Support'),
			('Very unhappy with your service', 'I have been waiting for support for several days and this experience has been very frustrating.', 'Complaint'),
		]
		department_by_category = {
			'Account & Access': 'Account Support Team',
			'Billing': 'Finance/Billing Team',
			'Technical Support': 'Technical Support Team',
			'Complaint': 'Customer Relations Team',
		}
		with patch.dict(os.environ, {}, clear=True):
			for subject, body, expected_category in samples:
				with self.subTest(subject=subject):
					result = classify_email_with_ai('sample@example.test', subject, body)
					self.assertEqual(result['category'], expected_category)
					self.assertEqual(result['engine'], 'Rule-Based Fallback')
					self.assertEqual(result['department'], department_by_category[expected_category])
					self.assertIn(result['priority'], ('High', 'Medium', 'Low'))
					self.assertIn(result['sentiment'], ('Positive', 'Neutral', 'Negative'))
					for field in ('priority', 'sentiment', 'confidence', 'department', 'reason'):
						self.assertIn(field, result)


class EmailWorkflowTests(TestCase):
	def create_email(self, **overrides):
		values = {
			'sender_email': 'sender@example.test',
			'subject': 'Account login help',
			'body': 'I cannot log in to my account.',
			'category': 'Account & Access',
			'priority': 'High',
			'sentiment': 'Negative',
			'confidence': 91.5,
			'department': 'Account Support Team',
			'reason': 'The customer cannot access the account.',
			'engine': 'Rule-Based Fallback',
		}
		values.update(overrides)
		return EmailClassification.objects.create(**values)

	@patch('requests.post')
	def test_analyze_saves_gemini_result_and_displays_it(self, post):
		response = MagicMock()
		response.json.return_value = {
			'candidates': [{'content': {'parts': [{'text': json.dumps(GEMINI_CLASSIFICATION)}]}}]
		}
		post.return_value = response
		email_body = 'I was charged twice for the same order. Please refund the duplicate payment.'

		with patch.dict(os.environ, {
			'GEMINI_API_KEY': 'test-gemini-key',
			'GEMINI_MODEL': 'gemini-test-model',
		}, clear=True):
			result = self.client.post('/analyze/', {
				'sender_email': 'billing@example.test',
				'subject': 'Payment charged twice',
				'body': email_body,
			})

		self.assertEqual(result.status_code, 200)
		self.assertContains(result, 'Google Gemini')
		self.assertContains(result, 'AI Engine')
		self.assertNotContains(result, 'test-gemini-key')
		record = EmailClassification.objects.get(sender_email='billing@example.test')
		self.assertEqual(record.subject, 'Payment charged twice')
		self.assertEqual(record.body, email_body)
		self.assertEqual(record.category, 'Billing')
		self.assertEqual(record.priority, 'High')
		self.assertEqual(record.sentiment, 'Neutral')
		self.assertEqual(record.confidence, 93.0)
		self.assertEqual(record.department, 'Finance/Billing Team')
		self.assertEqual(record.reason, GEMINI_CLASSIFICATION['reason'])
		self.assertIn('Gemini', record.engine)
		self.assertIsNotNone(record.created_at)

	def test_gemini_failure_saves_rule_fallback_result(self):
		with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-gemini-key'}, clear=True):
			with patch('emails.ai_service._call_gemini_api', side_effect=TimeoutError):
				result = self.client.post('/analyze/', {
					'sender_email': 'support@example.test',
					'subject': 'Application keeps crashing',
					'body': 'The application crashes whenever I try to upload a file. Please help.',
				})

		self.assertEqual(result.status_code, 200)
		self.assertContains(result, 'Rule-Based Fallback')
		record = EmailClassification.objects.get(sender_email='support@example.test')
		self.assertEqual(record.category, 'Technical Support')
		self.assertEqual(record.department, 'Technical Support Team')
		self.assertEqual(record.engine, 'Rule-Based Fallback')
		self.assertIn('Fallback:', record.reason)
		self.assertIsNotNone(record.created_at)

	def test_analyze_form_loads_and_rejects_missing_fields(self):
		self.assertEqual(self.client.get('/analyze/').status_code, 200)
		response = self.client.post('/analyze/', {'sender_email': '', 'subject': '', 'body': ''})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Please fill in all required fields')
		self.assertEqual(EmailClassification.objects.count(), 0)

	def test_history_search_filters_and_detail_fields(self):
		billing = self.create_email(
			sender_email='billing.person@example.test',
			subject='Payment charged twice',
			body='Please refund my duplicate payment.',
			category='Billing',
			priority='Medium',
			sentiment='Neutral',
			confidence=94.0,
			department='Finance/Billing Team',
			reason='Duplicate charge request.',
		)
		self.create_email(
			sender_email='upset.person@example.test',
			subject='Very unhappy with support',
			body='I have waited several days and this is frustrating.',
			category='Complaint',
		)

		all_history = self.client.get('/history/')
		self.assertContains(all_history, 'billing.person@example.test')
		self.assertContains(all_history, 'upset.person@example.test')
		self.assertContains(all_history, f'href="/history/{billing.id}/"')

		filters = (
			('search=billing.person', 'billing.person@example.test', 'upset.person@example.test'),
			('search=Payment+charged', 'Payment charged twice', 'Very unhappy with support'),
			('category=Billing', 'billing.person@example.test', 'upset.person@example.test'),
			('priority=High', 'upset.person@example.test', 'billing.person@example.test'),
			('sentiment=Neutral', 'billing.person@example.test', 'upset.person@example.test'),
			('department=Finance%2FBilling+Team', 'billing.person@example.test', 'upset.person@example.test'),
		)
		for query, expected, excluded in filters:
			with self.subTest(query=query):
				response = self.client.get(f'/history/?{query}')
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, expected)
				self.assertNotContains(response, excluded)

		detail = self.client.get(f'/history/{billing.id}/')
		self.assertEqual(detail.status_code, 200)
		for expected in (
			billing.sender_email, billing.subject, billing.body, billing.category,
			billing.priority, billing.sentiment, '94.0%', billing.department,
			billing.reason, billing.created_at.strftime('%B'), billing.created_at.strftime('%Y'),
			billing.created_at.strftime('%p'),
		):
			self.assertContains(detail, expected)

	def test_dashboard_counts_and_charts_use_database_records(self):
		self.create_email(category='Billing', priority='High', sentiment='Negative', department='Finance/Billing Team')
		self.create_email(category='Complaint', priority='Medium', sentiment='Neutral', department='Customer Relations Team')
		self.create_email(category='Technical Support', priority='Low', sentiment='Positive', department='Technical Support Team')

		response = self.client.get('/dashboard/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['total_emails'], 3)
		self.assertEqual(response.context['high_prio_count'], 1)
		self.assertEqual(response.context['med_prio_count'], 1)
		self.assertEqual(response.context['low_prio_count'], 1)
		self.assertEqual(response.context['total_classified'], 3)
		for chart_id in ('categoryChart', 'priorityChart', 'sentimentChart', 'departmentChart'):
			self.assertContains(response, f'id="{chart_id}"')
		category_chart = json.loads(response.context['category_chart_json'])
		billing_index = category_chart['labels'].index('Billing')
		self.assertEqual(category_chart['data'][billing_index], 1)
		priority_chart = json.loads(response.context['priority_chart_json'])
		self.assertEqual(priority_chart['data'], [1, 1, 1])
		sentiment_chart = json.loads(response.context['sentiment_chart_json'])
		self.assertEqual(sentiment_chart['data'], [1, 1, 1])
		department_chart = json.loads(response.context['department_chart_json'])
		department_index = department_chart['labels'].index('Finance/Billing Team')
		self.assertEqual(department_chart['data'][department_index], 1)
