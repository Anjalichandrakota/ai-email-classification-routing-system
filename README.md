# AI Email Classification and Routing System

## Project Overview

The AI Email Classification and Routing System is a Django-based web application that automatically analyzes incoming emails using Google Gemini AI and routes them to the appropriate department.

The system classifies emails based on:

- Category
- Priority
- Sentiment
- Confidence
- Department
- Reason for classification

A rule-based fallback classifier is also available when the AI service is unavailable.

## Objectives

- Automate email classification.
- Reduce manual email routing.
- Identify the priority of incoming emails.
- Analyze customer sentiment.
- Route emails to the appropriate department.
- Maintain email classification history.
- Provide a dashboard for monitoring and analytics.

## Main Features

### 1. AI Email Analysis

Users can enter:

- Sender
- Subject
- Email body

The application sends the email information to Google Gemini and receives an AI-generated classification.

### 2. Email Categories

The system supports:

- Technical Support
- Billing
- Complaint
- Sales
- Account & Access
- General Inquiry

### 3. Priority Classification

Emails are classified as:

- High
- Medium
- Low

### 4. Sentiment Analysis

The system identifies:

- Positive
- Neutral
- Negative

### 5. Department Routing

| Category | Department |
|---|---|
| Technical Support | Technical Support Team |
| Billing | Finance/Billing Team |
| Complaint | Customer Relations Team |
| Sales | Sales Team |
| Account & Access | Account Support Team |
| General Inquiry | General Support Team |

### 6. Dashboard

The dashboard provides analytics about classified emails, including category, priority, sentiment, and routing information.

### 7. Email History

Previously analyzed emails can be searched, filtered, and viewed in detail.

### 8. Fallback Classification

If Google Gemini is unavailable, the application can use a rule-based classification system so that email processing can continue.

## Technology Stack

- Python
- Django
- HTML
- CSS
- JavaScript
- SQLite
- Google Gemini API
- Chart.js

## System Workflow

```text
Incoming Email
      ↓
Email Input
      ↓
Google Gemini AI
      ↓
Category + Priority + Sentiment
      ↓
Validation and Normalization
      ↓
Department Routing
      ↓
Database
      ↓
Dashboard / Email History