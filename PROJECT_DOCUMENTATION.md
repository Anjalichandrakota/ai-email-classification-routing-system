# AI Email Classification and Routing System
## Project Documentation

### 1. Introduction

The AI Email Classification and Routing System is a web-based application developed using Django and Google Gemini AI.

The system analyzes incoming emails and automatically determines their category, priority, sentiment, and appropriate department. This reduces manual email sorting and helps organizations route customer emails efficiently.

---

## 2. Problem Statement

Organizations receive a large number of emails every day. Manually reading, classifying, prioritizing, and forwarding these emails can be time-consuming.

This project provides an automated solution that uses Artificial Intelligence to analyze emails and route them to the appropriate department.

---

## 3. Objectives

The main objectives are:

1. Automatically classify incoming emails.
2. Identify email priority.
3. Analyze email sentiment.
4. Route emails to the appropriate department.
5. Store classification results in a database.
6. Provide email history and search functionality.
7. Provide dashboard-based analytics.
8. Use Google Gemini as the primary AI classification engine.
9. Provide a rule-based fallback when AI is unavailable.

---

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web application framework |
| Google Gemini | AI email classification |
| HTML | Web page structure |
| CSS | User interface styling |
| JavaScript | Client-side functionality |
| SQLite | Database |
| Chart.js | Dashboard charts |
| Git/GitHub | Version control |

---

## 5. System Architecture

```text
              User
                |
                v
        Email Input Form
                |
                v
        Django Application
                |
                v
          Gemini AI API
                |
                v
       AI Classification
        /       |       \
       /        |        \
 Category    Priority   Sentiment
       \        |        /
        \       |       /
                v
       Validation & Mapping
                |
                v
       Department Routing
                |
                v
          SQLite Database
                |
        +-------+-------+
        |               |
        v               v
    Dashboard      Email History