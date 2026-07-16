# Logistics Workflow Portal, Unit 4 Prototype

This is the initial working prototype for the MSIT 5910 capstone project. It demonstrates a role-based logistics workflow portal with Flask, SQLite, and simple Bootstrap pages.

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Customer | customer1 | pass123 |
| Employee | employee1 | pass123 |
| Manager | manager1 | pass123 |

## How to run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in the browser.

## Working features for Unit 4 demo

1. Login with role-based routing.
2. Customer status view and request submission.
3. Employee workflow update for document status and delay reason.
4. Manager dashboard with counts for records, missing documents, delayed records, and open requests.

This prototype uses sample data only and is not a production system.
