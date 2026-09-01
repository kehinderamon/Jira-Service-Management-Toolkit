Jira Service Management Ticket Toolkit
A Python command-line tool that manages real IT support tickets in Jira Service Management (Jira Cloud) through its official REST API, create tickets, search/filter with JQL, change status through the actual workflow, assign to a technician, comment, export to CSV, and pull a quick stats dashboard. No custom database: every ticket lives in your real JSM project, exactly like it would at a company using Jira for their service desk.
Why this project
Jira Service Management is one of the most widely used ITSM tools in the industry. This project shows you can go beyond just clicking around Jira, you can script against its REST API to automate the repetitive parts of the job: bulk status changes, scheduled reports, CSV exports for management, or integrations with other systems. That's a skill that sets a support technician apart.
Features
Create tickets with summary, description, priority, and labels (used as categories, e.g. `network`, `hardware`)
Search/filter tickets using JQL (Jira Query Language),  e.g. `status = "In Progress"` or `priority = High`
View full ticket detail
Change ticket status, dynamically fetches the real transitions available for that ticket's workflow (so it always matches your project's actual setup, not a hardcoded guess)
Assign tickets to a technician by their Jira account email
Add comments to a ticket
Export tickets to CSV for reporting
Statistics dashboard — counts by status and priority
Clean separation between the Jira API logic (`jsm_client.py`) and the CLI menu (`jsm_toolkit.py`), so the client can be reused in other scripts
Full automated test suite that mocks the Jira API, so tests run instantly, offline, and without needing real credentials (safe for GitHub Actions / CI)
Tech stack
Python 3
`requests` — HTTP calls to the Jira Cloud REST API v3
`python-dotenv` — loads credentials from a local `.env` file
`unittest` + `unittest.mock` for automated tests
Project structure
```
1-jira-service-management-toolkit/
├── jsm_client.py           # Jira REST API wrapper (create/search/transition/assign/comment)
├── jsm_toolkit.py          # CLI menu (run this)
├── tests/
│   └── test_jsm_client.py  # automated tests (mocked API calls)
├── .env.example            # copy to .env and fill in your real credentials
├── requirements.txt
├── .gitignore
└── README.md
```
Getting started
1. Prerequisites
Python 3.8+
A Jira Service Management site (the free tier works fine) with at least one service project set up
Your Atlassian account email
2. Get a Jira API token
Go to https://id.atlassian.com/manage-profile/security/api-tokens
Click Create API token, give it a label like "helpdesk-toolkit", and copy the token — you won't be able to see it again
Keep it somewhere safe; you'll paste it into `.env` in a moment
3. Find your project key
Open your JSM project in the browser and look at any ticket's ID, e.g. `ITSD-42` — the part before the dash (`ITSD`) is your project key. You can also find it under Project settings → Details.
4. Install and configure
```bash
git clone https://github.com/<your-username>/jira-service-management-toolkit.git
cd jira-service-management-toolkit
pip install -r requirements.txt --break-system-packages

cp .env.example .env
```
Now open `.env` and fill in your real values:
```
JIRA_SITE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=paste_your_token_here
JIRA_PROJECT_KEY=ITSD
```
5. Run it
```bash
python3 jsm_toolkit.py
```
You'll see a numbered menu, pick an option and follow the prompts.
6. Run the tests
These use mocked API responses, so they work even without a `.env` file configured:
```bash
python3 tests/test_jsm_client.py
```
Example usage
```
=== Jira Service Management Ticket Toolkit ===
1. Create new ticket
...
Select an option: 1
Issue summary (short title): VPN keeps disconnecting
Description: User reports VPN drops every 20 minutes while working from home.
Priority: Highest, High, Medium, Low, Lowest
> High
Labels/category, comma-separated (e.g. network,vpn): network,vpn
Created ticket: ITSD-58
```
A note on JQL
JQL (Jira Query Language) is how Jira filters issues, and it's worth learning on its own — it's the same syntax used in Jira's web search bar. A few examples you can paste into option 2:
`status = "Open"`
`priority in (High, Highest)`
`assignee = currentUser()`
`created >= -7d` (created in the last 7 days)
Possible future improvements
Auto-create tickets from an incoming email inbox (IMAP polling)
Slack notifications when a Highest-priority ticket is created
SLA breach detection (flag tickets open longer than X hours based on priority)
A scheduled script (cron) that emails a daily ticket summary report
License
MIT, free to use, modify, and share.
