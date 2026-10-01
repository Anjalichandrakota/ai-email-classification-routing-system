from django.contrib import admin
from .models import EmailClassification

@admin.register(EmailClassification)
class EmailClassificationAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender_email', 'category', 'priority', 'sentiment', 'confidence', 'department', 'engine', 'created_at')
    list_filter = ('category', 'priority', 'sentiment', 'department', 'engine', 'created_at')
    search_fields = ('subject', 'sender_email', 'body', 'department', 'reason')
