"""
Rule-Based Email Classifier and Routing Module.

Provides deterministic keyword and pattern matching for email categorization,
priority scoring, sentiment detection, department routing, and reasoning generation.
"""

import re
from typing import Dict, Any, List, Tuple

# Department mapping dictionary
DEPARTMENT_MAPPINGS = {
    'Technical Support': 'Technical Support Team',
    'Billing': 'Finance/Billing Team',
    'Complaint': 'Customer Relations Team',
    'Sales': 'Sales Team',
    'Account & Access': 'Account Support Team',
    'General Inquiry': 'General Support Team',
}

# Category keyword dictionaries with weights
CATEGORY_RULES = {
    'Technical Support': {
        'high_weights': [
            'error', 'bug', 'crash', 'crashed', 'crashing', 'exception', 'server down',
            'outage', 'api error', '500 error', '404 error', 'latency', 'timeout',
            'stack trace', 'glitch', 'database down', 'system failure', 'out of memory',
            'connection refused', 'ssl error', 'broken link', 'null pointer'
        ],
        'standard_weights': [
            'technical', 'issue', 'not working', 'debug', 'server', 'api', 'code',
            'endpoint', 'frontend', 'backend', 'performance', 'slow', 'deployment',
            'build failed', 'patch', 'software', 'hardware', 'troubleshoot', 'malfunction'
        ]
    },
    'Billing': {
        'high_weights': [
            'invoice', 'refund', 'overcharged', 'chargeback', 'credit card charged',
            'unauthorized charge', 'double charged', 'billing statement', 'wire transfer',
            'payment failed', 'receipt', 'subscription canceled', 'renewal fee', 'tax id'
        ],
        'standard_weights': [
            'billing', 'payment', 'charged', 'charge', 'cost', 'fee', 'pricing',
            'price', 'subscription', 'annual plan', 'monthly plan', 'bank',
            'transaction', 'discount code', 'currency', 'pay', 'checkout', 'paid'
        ]
    },
    'Complaint': {
        'high_weights': [
            'unacceptable', 'terrible', 'horrible', 'worst service', 'extremely disappointed',
            'disgusted', 'furious', 'sue', 'lawsuit', 'legal action', 'better business bureau',
            'consumer protection', 'scam', 'cheated', 'fraudulent', 'rip off', 'talk to supervisor',
            'speak to manager', 'demand an explanation'
        ],
        'standard_weights': [
            'complaint', 'complain', 'dissatisfied', 'bad experience', 'angry', 'frustrated',
            'poor quality', 'poor service', 'rude', 'unhappy', 'appalled', 'regret',
            'waste of time', 'waste of money', 'cancel my service', 'never again'
        ]
    },
    'Sales': {
        'high_weights': [
            'request a quote', 'enterprise quote', 'schedule a demo', 'book a demo',
            'sales inquiry', 'purchase license', 'rfp', 'rfi', 'procurement',
            'volume discount', 'custom plan', 'partnership inquiry', 'reseller agreement'
        ],
        'standard_weights': [
            'sales', 'quote', 'demo', 'pricing details', 'buy', 'purchase',
            'trial', 'enterprise', 'license', 'commercial', 'contract', 'partnership',
            'upgrade plan', 'tier', 'evaluation', 'interested in your product'
        ]
    },
    'Account & Access': {
        'high_weights': [
            'reset password', 'forgot password', 'locked out', 'unlock account',
            '2fa', 'two-factor', 'mfa', 'authenticator code', 'sso login',
            'unauthorized access', 'compromised account', 'suspended account', 'reactivate account'
        ],
        'standard_weights': [
            'login', 'log in', 'signin', 'sign in', 'password', 'credentials',
            'access', 'account', 'username', 'permission', 'forbidden 403',
            'verification email', 'profile', 'register', 'sign up', 'invite member'
        ]
    },
    'General Inquiry': {
        'high_weights': [
            'general inquiry', 'general question', 'business hours', 'headquarters address',
            'press inquiry', 'media request', 'careers', 'job opening'
        ],
        'standard_weights': [
            'inquiry', 'question', 'information', 'info', 'help', 'overview',
            'guidance', 'how do i', 'where can i', 'contact', 'feedback', 'suggestion',
            'learn more', 'details', 'curious', 'assistance'
        ]
    }
}

# Priority indicators
HIGH_PRIORITY_TERMS = [
    'urgent', 'urgently', 'emergency', 'asap', 'immediately', 'critical', 'severe',
    'outage', 'down', 'production down', 'blocker', 'legal action', 'lawyer', 'sue',
    'security breach', 'compromised', 'cannot work', 'system offline', 'deadline today'
]

MEDIUM_PRIORITY_TERMS = [
    'issue', 'problem', 'error', 'failed', 'refund', 'overdue', 'billing', 'locked out',
    'incorrect', 'discrepancy', 'escalate', 'soon', 'important', 'delay'
]

# Sentiment indicators
POSITIVE_TERMS = [
    'thank', 'thanks', 'thank you', 'appreciate', 'great', 'excellent', 'amazing',
    'awesome', 'helpful', 'love', 'pleased', 'good job', 'wonderful', 'kudos',
    'happy with', 'impressed', 'glad'
]

NEGATIVE_TERMS = [
    'angry', 'upset', 'terrible', 'horrible', 'worst', 'unacceptable', 'frustrated',
    'disappointed', 'hate', 'furious', 'broken', 'fail', 'failed', 'failing',
    'poor', 'bad', 'waste', 'ridiculous', 'annoying', 'complaint', 'scam', 'useless'
]


def _clean_text(text: str) -> str:
    """Normalize whitespace and lowercases text."""
    if not text:
        return ""
    return " ".join(text.lower().split())


def _find_matches(haystack: str, terms: List[str]) -> List[str]:
    """Finds exact sub-phrase or word boundaries matches."""
    matches = []
    for term in terms:
        # Regex search for full phrase or bounded word
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, haystack):
            matches.append(term)
    return matches


def classify_email(sender_email: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Analyzes an email's sender, subject, and body using rule-based heuristics.

    Returns:
        dict containing:
        - category: str
        - priority: 'High' | 'Medium' | 'Low'
        - sentiment: 'Positive' | 'Neutral' | 'Negative'
        - confidence: float (0.0 to 100.0)
        - department: str
        - reason: str
    """
    clean_subj = _clean_text(subject)
    clean_body = _clean_text(body)
    combined = f"{clean_subj} {clean_subj} {clean_body}"  # Weight subject 2x

    # 1. Category Scoring
    category_scores: Dict[str, float] = {cat: 0.0 for cat in CATEGORY_RULES.keys()}
    category_reasons: Dict[str, List[str]] = {cat: [] for cat in CATEGORY_RULES.keys()}

    for category, rule_dict in CATEGORY_RULES.items():
        # High weight terms (3 points)
        high_matches = _find_matches(combined, rule_dict['high_weights'])
        if high_matches:
            category_scores[category] += len(high_matches) * 3.5
            category_reasons[category].extend(high_matches[:3])

        # Standard weight terms (1 point)
        std_matches = _find_matches(combined, rule_dict['standard_weights'])
        if std_matches:
            category_scores[category] += len(std_matches) * 1.2
            category_reasons[category].extend(std_matches[:3])

    # Find highest scoring category
    sorted_categories: List[Tuple[str, float]] = sorted(
        category_scores.items(), key=lambda item: item[1], reverse=True
    )
    best_category, best_score = sorted_categories[0]

    # Default fallback if no keywords matched
    if best_score == 0.0:
        best_category = 'General Inquiry'
        confidence = 68.0
        reason_explanation = "No distinctive technical, billing, sales, or access keywords detected. Defaulted to General Inquiry."
    else:
        # Calculate confidence based on lead over 2nd place and match density
        second_score = sorted_categories[1][1] if len(sorted_categories) > 1 else 0.0
        margin = best_score - second_score
        
        # Base confidence from match strength
        base_confidence = min(96.0, 72.0 + (best_score * 3.0))
        if margin > 3.0:
            base_confidence = min(98.5, base_confidence + 4.0)
        elif margin < 1.0:
            base_confidence = max(65.0, base_confidence - 5.0)

        confidence = round(base_confidence, 1)

        matched_words = list(dict.fromkeys(category_reasons[best_category]))
        words_preview = ", ".join([f"'{w}'" for w in matched_words[:4]])
        reason_explanation = (
            f"Classified as {best_category} based on keyword triggers: {words_preview} "
            f"(intent score: {best_score:.1f})."
        )

    # 2. Priority Scoring
    high_prio_matches = _find_matches(combined, HIGH_PRIORITY_TERMS)
    med_prio_matches = _find_matches(combined, MEDIUM_PRIORITY_TERMS)

    if high_prio_matches or best_category == 'Complaint' and len(category_reasons['Complaint']) >= 2:
        priority = 'High'
        if high_prio_matches:
            reason_explanation += f" Elevated to High priority due to urgency markers: {', '.join(high_prio_matches[:2])}."
        else:
            reason_explanation += " Assigned High priority due to severe customer dissatisfaction indicators."
    elif med_prio_matches or best_category in ['Technical Support', 'Billing', 'Account & Access']:
        priority = 'Medium'
    else:
        priority = 'Low'

    # 3. Sentiment Detection
    pos_matches = _find_matches(combined, POSITIVE_TERMS)
    neg_matches = _find_matches(combined, NEGATIVE_TERMS)

    pos_score = len(pos_matches)
    neg_score = len(neg_matches)

    # If it's a complaint or has severe negatives
    if best_category == 'Complaint':
        neg_score += 2

    if neg_score > pos_score:
        sentiment = 'Negative'
    elif pos_score > neg_score and neg_score == 0:
        sentiment = 'Positive'
    else:
        sentiment = 'Neutral'

    # 4. Department Mapping
    department = DEPARTMENT_MAPPINGS.get(best_category, 'General Support Team')

    return {
        'category': best_category,
        'priority': priority,
        'sentiment': sentiment,
        'confidence': confidence,
        'department': department,
        'reason': reason_explanation,
    }
