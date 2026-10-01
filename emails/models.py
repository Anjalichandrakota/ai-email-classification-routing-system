from django.db import models

class EmailClassification(models.Model):
    """
    Stores email items along with classification metadata, sentiment, priority,
    routing department, confidence score, and classification rationale.
    """
    CATEGORY_CHOICES = [
        ('Technical Support', 'Technical Support'),
        ('Billing', 'Billing'),
        ('Complaint', 'Complaint'),
        ('Sales', 'Sales'),
        ('Account & Access', 'Account & Access'),
        ('General Inquiry', 'General Inquiry'),
    ]

    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    SENTIMENT_CHOICES = [
        ('Positive', 'Positive'),
        ('Neutral', 'Neutral'),
        ('Negative', 'Negative'),
    ]

    sender_email = models.EmailField(max_length=254)
    subject = models.CharField(max_length=255)
    body = models.TextField()

    # Classification fields
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='General Inquiry')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='Neutral')
    confidence = models.FloatField(default=0.85, help_text="Classification confidence percentage (e.g. 92.5)")

    # Routing and explanation fields
    department = models.CharField(max_length=150, default='General Support Team')
    reason = models.TextField(blank=True, default='')
    engine = models.CharField(max_length=100, default='AI (LLM)', help_text="AI Provider/Model or Fallback mechanism")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Classification'
        verbose_name_plural = 'Email Classifications'

    def __str__(self):
        return f"{self.subject} ({self.sender_email}) - {self.category} [{self.priority}]"

    # Compatibility properties
    @property
    def sender(self):
        return self.sender_email

    @property
    def assigned_department(self):
        return self.department

    @property
    def confidence_score(self):
        return self.confidence / 100.0 if self.confidence > 1.0 else self.confidence

    @property
    def status(self):
        return 'Classified'


# Alias for backward compatibility
EmailRecord = EmailClassification
