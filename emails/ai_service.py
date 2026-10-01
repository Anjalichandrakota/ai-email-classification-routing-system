"""
AI/LLM Email Classification Service with Automatic Fallback.

Connects to LLM APIs (OpenAI, Groq, Gemini, or custom OpenAI-compatible endpoint)
via environment variables to classify inbound emails, returning structured JSON.
Falls back automatically to the rule-based classifier if the AI API is missing,
unavailable, or returns an invalid response.
"""

import os
import json
import logging
import re
from typing import Dict, Any, Tuple

from django.conf import settings

from .classifier import classify_email, DEPARTMENT_MAPPINGS
from email_classifier.environment import load_local_environment

# Settings load the local .env at startup. Refresh here as well so provider
# detection works in a running development server after local config changes.
load_local_environment()

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = [
    'Technical Support',
    'Billing',
    'Complaint',
    'Sales',
    'Account & Access',
    'General Inquiry',
]

ALLOWED_PRIORITIES = ['High', 'Medium', 'Low']
ALLOWED_SENTIMENTS = ['Positive', 'Neutral', 'Negative']

SYSTEM_PROMPT = """You are an enterprise AI Email Classification and Routing System.
Analyze the inbound email provided by the user.

Classify the email into EXACTLY one of these allowed categories:
- Technical Support
- Billing
- Complaint
- Sales
- Account & Access
- General Inquiry

Assign Priority:
- High (severe urgency, outage, system down, loss of revenue, angry customer/legal risk)
- Medium (standard bugs, account issues, billing questions, normal inquiries)
- Low (casual inquiries, feedback, informational questions)

Assign Sentiment:
- Positive
- Neutral
- Negative

Assign Department strictly following this mapping:
- Technical Support -> Technical Support Team
- Billing -> Finance/Billing Team
- Complaint -> Customer Relations Team
- Sales -> Sales Team
- Account & Access -> Account Support Team
- General Inquiry -> General Support Team

Assign Confidence:
A floating point percentage between 50.0 and 99.5 reflecting model certainty.

Provide Reason:
A concise explanation of the decision based on intent, urgency cues, and context.

CRITICAL: Return ONLY a valid JSON object without markdown fences, code blocks, or extra text:
{
  "category": "Technical Support",
  "priority": "High",
  "sentiment": "Neutral",
  "confidence": 96.5,
  "department": "Technical Support Team",
  "reason": "Classified as Technical Support due to API outage and server 500 error mentions."
}
"""


def _clean_json_text(raw_text: str) -> str:
    """Strips markdown code fences and surrounding whitespace."""
    text = raw_text.strip()
    # Strip ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    # Extract first {...} block if there is surrounding text
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        text = match.group(1)
    return text.strip()


def _normalize_and_validate(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Validates and normalizes parsed AI response against required specs."""
    raw_cat = str(parsed.get('category', '')).strip()
    matched_cat = None
    for cat in ALLOWED_CATEGORIES:
        if raw_cat.lower() == cat.lower():
            matched_cat = cat
            break

    if not matched_cat:
        for cat in ALLOWED_CATEGORIES:
            if cat.lower() in raw_cat.lower():
                matched_cat = cat
                break

    if not matched_cat:
        raise ValueError(f"AI returned invalid category: '{raw_cat}'")

    # Priority
    raw_prio = str(parsed.get('priority', 'Medium')).strip().capitalize()
    if raw_prio not in ALLOWED_PRIORITIES:
        raw_prio = 'Medium'

    # Sentiment
    raw_sent = str(parsed.get('sentiment', 'Neutral')).strip().capitalize()
    if raw_sent not in ALLOWED_SENTIMENTS:
        raw_sent = 'Neutral'

    # Department
    department = DEPARTMENT_MAPPINGS.get(matched_cat, 'General Support Team')

    # Confidence
    try:
        conf = float(parsed.get('confidence', 90.0))
        if conf <= 1.0:
            conf = conf * 100.0
        conf = max(50.0, min(99.5, round(conf, 1)))
    except (ValueError, TypeError):
        conf = 88.0

    # Reason
    reason = str(parsed.get('reason', '')).strip()
    if not reason:
        reason = f"Classified by AI as {matched_cat} with {raw_prio} priority."

    return {
        'category': matched_cat,
        'priority': raw_prio,
        'sentiment': raw_sent,
        'confidence': conf,
        'department': department,
        'reason': reason,
    }


def _call_groq_api(api_key: str, user_content: str, model_name: str = None) -> Dict[str, Any]:
    """Calls Groq API."""
    from groq import Groq
    client = Groq(api_key=api_key)
    model = model_name or os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        timeout=15.0
    )
    raw_reply = completion.choices[0].message.content
    data = json.loads(_clean_json_text(raw_reply))
    res = _normalize_and_validate(data)
    res['engine'] = f'AI (Groq: {model})'
    return res


def _call_openai_api(api_key: str, user_content: str, base_url: str = None, model_name: str = None) -> Dict[str, Any]:
    """Calls OpenAI API or compatible endpoint."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    model = model_name or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        timeout=15.0
    )
    raw_reply = completion.choices[0].message.content
    data = json.loads(_clean_json_text(raw_reply))
    res = _normalize_and_validate(data)
    res['engine'] = f'AI (OpenAI: {model})'
    return res


def _call_gemini_api(api_key: str, user_content: str, model_name: str = None) -> Dict[str, Any]:
    """Calls Google Gemini API via REST."""
    import requests
    model = (model_name or os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')).strip()
    logger.info('Gemini _call_gemini_api() entered; model=%s', model)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{SYSTEM_PROMPT}\n\nEmail to classify:\n{user_content}"}
                ]
            }
        ],
        "generationConfig": {
            "responseFormat": {
                "text": {
                    "mimeType": "APPLICATION_JSON"
                }
            }
        }
    }

    logger.info('Gemini request started; model=%s', model)
    # In local DEBUG mode, bypass inherited HTTP(S)_PROXY / ALL_PROXY values
    # for this Gemini request only. Empty per-request proxy entries override
    # Requests' environment proxy discovery without changing other traffic.
    bypass_local_proxy = settings.DEBUG
    request_options = (
        {'proxies': {'http': '', 'https': ''}}
        if bypass_local_proxy
        else {}
    )
    logger.info('Gemini local proxy bypass enabled: %s', bypass_local_proxy)
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={'x-goog-api-key': api_key},
            timeout=15,
            **request_options,
        )
    except requests.RequestException as error:
        logger.warning('Gemini HTTP status: unavailable')
        logger.info('Gemini response parsing succeeded: false')
        logger.warning('Gemini request failed; error=%s', _safe_gemini_transport_error(error, api_key))
        raise

    logger.info('Gemini HTTP status: %s', resp.status_code)
    try:
        resp.raise_for_status()
    except requests.RequestException as error:
        logger.info('Gemini response parsing succeeded: false')
        message = _gemini_response_error(resp) or str(error)
        logger.warning('Gemini request failed; error=%s', _safe_gemini_error(message, api_key))
        raise

    try:
        result_json = resp.json()
        candidates = result_json.get('candidates') or []
        if not candidates:
            raise ValueError('Gemini response contained no candidates')

        parts = (candidates[0].get('content') or {}).get('parts') or []
        text_parts = [
            part['text']
            for part in parts
            if isinstance(part, dict) and isinstance(part.get('text'), str) and not part.get('thought')
        ]
        if not text_parts:
            raise ValueError('Gemini response contained no candidate text')

        raw_reply = ''.join(text_parts)
        data = json.loads(_clean_json_text(raw_reply))
        res = _normalize_and_validate(data)
    except Exception as error:
        logger.info('Gemini response parsing succeeded: false')
        # Avoid logging model output or email content when parsing/validation fails.
        safe_detail = f'Gemini response parsing failed ({error.__class__.__name__})'
        logger.warning('Gemini request failed; error=%s', _safe_gemini_error(safe_detail, api_key))
        raise

    logger.info('Gemini response parsing succeeded: true')
    res['engine'] = f'AI (Gemini: {model})'
    return res


def _gemini_response_error(response) -> str:
    """Extract only Google's error message, never response headers or key data."""
    import requests
    try:
        body = response.json()
    except (ValueError, requests.RequestException):
        return ''

    error = body.get('error') if isinstance(body, dict) else None
    message = error.get('message') if isinstance(error, dict) else None
    return message if isinstance(message, str) else ''


def _safe_gemini_error(message: str, api_key: str) -> str:
    """Sanitize provider errors before logging; secrets and headers are never logged."""
    safe_message = str(message or 'Unknown Gemini API error')
    if api_key:
        safe_message = safe_message.replace(api_key, '[REDACTED]')
    safe_message = re.sub(
        r'(?i)(x-goog-api-key|authorization|api[_ -]?key)(\s*[:=]\s*)([^\s,;]+)',
        r'\1\2[REDACTED]',
        safe_message,
    )
    safe_message = re.sub(r'AIza[0-9A-Za-z_-]{20,}|gsk_[0-9A-Za-z_-]{12,}', '[REDACTED]', safe_message)
    safe_message = ''.join(char for char in safe_message if char.isprintable())
    return ' '.join(safe_message.split())[:500]


def _safe_gemini_transport_error(error: Exception, api_key: str) -> str:
    """Keep transport diagnostics concise and exclude proxy/URL details."""
    import requests
    if isinstance(error, requests.exceptions.ProxyError):
        return 'Connection to the configured proxy failed'
    if isinstance(error, requests.Timeout):
        return 'Gemini request timed out'
    if isinstance(error, requests.ConnectionError):
        return 'Gemini connection failed'
    return _safe_gemini_error(str(error), api_key)


def classify_email_with_ai(sender_email: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Classifies an email using configured AI/LLM API.
    If the API is missing, unavailable, or errors, automatically falls back
    to the rule-based classifier.
    """
    logger.info('classify_email_with_ai() entered')
    load_local_environment()
    user_content = f"Sender: {sender_email}\nSubject: {subject}\n\nBody:\n{body}"

    # Check for available API keys in environment variables
    openai_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('LLM_API_KEY') or os.environ.get('AI_API_KEY')
    groq_key = os.environ.get('GROQ_API_KEY')
    gemini_key = os.environ.get('GEMINI_API_KEY')
    custom_base_url = os.environ.get('OPENAI_BASE_URL') or os.environ.get('LLM_BASE_URL')

    ai_error_reason = None

    # Gemini is the primary classification engine.
    if gemini_key:
        gemini_model = (os.environ.get('GEMINI_MODEL') or 'gemini-2.5-flash').strip()
        logger.info('Gemini provider selected; model=%s', gemini_model)
        try:
            return _call_gemini_api(gemini_key, user_content)
        except Exception as e:
            ai_error_reason = f"Gemini API error ({e.__class__.__name__})"
            logger.warning(
                'Gemini exception/failure; error=Gemini provider raised %s',
                e.__class__.__name__,
            )

    # Keep other configured AI providers available if Gemini cannot respond.
    if groq_key:
        try:
            return _call_groq_api(groq_key, user_content)
        except Exception as e:
            ai_error_reason = f"Groq API error ({e.__class__.__name__})"

    if openai_key:
        try:
            return _call_openai_api(openai_key, user_content, base_url=custom_base_url)
        except Exception as e:
            ai_error_reason = f"OpenAI API error ({e.__class__.__name__})"

    if not (groq_key or openai_key or gemini_key):
        ai_error_reason = "No AI API key found in environment variables (OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY)"

    # 4. Fallback to Rule-Based Classifier
    logger.warning('Rule-based fallback activated')
    fallback_result = classify_email(sender_email, subject, body)
    fallback_result['engine'] = 'Rule-Based Fallback'
    fallback_result['reason'] = f"[Fallback: {ai_error_reason}] {fallback_result['reason']}"
    return fallback_result


def has_ai_provider_configured() -> bool:
    """Return whether any supported provider key is currently available."""
    load_local_environment()
    return any(os.environ.get(name) for name in (
        'GEMINI_API_KEY',
        'GROQ_API_KEY',
        'OPENAI_API_KEY',
        'LLM_API_KEY',
        'AI_API_KEY',
    ))
