"""
jsm_client.py
==============
A thin, well-tested Python client around the Jira Service Management
(Jira Cloud) REST API. This module contains no CLI code — it's pure
"talk to Jira" logic — so it can be imported by the CLI (jsm_toolkit.py),
by automated tests (with the network calls mocked out), or by any other
script you want to write later (e.g. a Slack bot, a scheduled report).

Jira Service Management tickets ARE Jira issues living in a
"service desk" project, so this client uses the standard Jira Cloud
REST API v3 (https://developer.atlassian.com/cloud/jira/platform/rest/v3/).

Authentication: Jira Cloud uses HTTP Basic Auth with your account email
+ an API token (NOT your normal password). See README.md for how to
create one.
"""

import os
import requests
from requests.auth import HTTPBasicAuth

# Standard JSM/Jira priority names. If your site uses custom priority
# names, update this list to match (Project settings -> Priorities).
VALID_PRIORITIES = ["Highest", "High", "Medium", "Low", "Lowest"]


class JSMClient:
    """
    A small wrapper around the pieces of the Jira Cloud REST API that a
    service-desk ticket workflow actually needs: create, search, view,
    transition (change status), assign, and comment.
    """

    def __init__(self, site_url=None, email=None, api_token=None, project_key=None):
        self.site_url = (site_url or os.environ.get("JIRA_SITE_URL", "")).rstrip("/")
        self.email = email or os.environ.get("JIRA_EMAIL", "")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN", "")
        self.project_key = project_key or os.environ.get("JIRA_PROJECT_KEY", "")

        if not all([self.site_url, self.email, self.api_token, self.project_key]):
            raise ValueError(
                "Missing Jira configuration. Set JIRA_SITE_URL, JIRA_EMAIL, "
                "JIRA_API_TOKEN, and JIRA_PROJECT_KEY (e.g. in a .env file). "
                "See README.md for setup instructions."
            )

        self.auth = HTTPBasicAuth(self.email, self.api_token)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------
    def _request(self, method, path, **kwargs):
        url = f"{self.site_url}{path}"
        response = requests.request(
            method, url, auth=self.auth, headers=self.headers, timeout=15, **kwargs
        )
        if response.status_code >= 400:
            raise JSMAPIError(response.status_code, response.text, url)
        return response

    # ------------------------------------------------------------------
    # Ticket creation
    # ------------------------------------------------------------------
    def create_ticket(self, summary, description="", issue_type="Task",
                       priority="Medium", labels=None):
        """
        Create a new ticket (issue) in the configured JSM project.
        Returns the created issue's key (e.g. "ITSD-42").
        """
        if priority not in VALID_PRIORITIES:
            priority = "Medium"

        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": self._to_adf(description),
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
                "labels": labels or [],
            }
        }
        response = self._request("POST", "/rest/api/3/issue", json=payload)
        return response.json()["key"]

    @staticmethod
    def _to_adf(text):
        """Jira Cloud requires descriptions in Atlassian Document Format (ADF)."""
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": text or ""}]}
            ],
        }

    # ------------------------------------------------------------------
    # Reading tickets
    # ------------------------------------------------------------------
    def get_ticket(self, issue_key):
        response = self._request("GET", f"/rest/api/3/issue/{issue_key}")
        return response.json()

    def search_tickets(self, jql=None, max_results=50):
        """
        Search for tickets using JQL (Jira Query Language). If no JQL is
        given, defaults to every ticket in the configured project,
        newest first.
        """
        jql = jql or f"project = {self.project_key} ORDER BY created DESC"
        response = self._request(
            "GET",
            "/rest/api/3/search",
            params={"jql": jql, "maxResults": max_results,
                    "fields": "summary,status,priority,assignee,created,updated,labels"},
        )
        return response.json().get("issues", [])

    # ------------------------------------------------------------------
    # Updating tickets
    # ------------------------------------------------------------------
    def get_available_transitions(self, issue_key):
        """
        Return the list of status transitions currently available for a
        ticket (e.g. "In Progress", "Done"). Workflows differ per
        project, so this is fetched live instead of hardcoded.
        """
        response = self._request("GET", f"/rest/api/3/issue/{issue_key}/transitions")
        return response.json().get("transitions", [])

    def transition_ticket(self, issue_key, transition_name):
        """Move a ticket to a new status by transition name (case-insensitive)."""
        transitions = self.get_available_transitions(issue_key)
        match = next(
            (t for t in transitions if t["name"].lower() == transition_name.lower()), None
        )
        if not match:
            available = ", ".join(t["name"] for t in transitions)
            raise ValueError(
                f"'{transition_name}' is not a valid transition for {issue_key}. "
                f"Available: {available}"
            )
        self._request(
            "POST", f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": match["id"]}},
        )
        return True

    def find_account_id_by_email(self, email):
        """Look up a Jira user's accountId from their email (needed to assign tickets)."""
        response = self._request(
            "GET", "/rest/api/3/user/search", params={"query": email}
        )
        results = response.json()
        if not results:
            return None
        return results[0]["accountId"]

    def assign_ticket(self, issue_key, assignee_email):
        account_id = self.find_account_id_by_email(assignee_email)
        if not account_id:
            raise ValueError(f"No Jira user found for email: {assignee_email}")
        self._request(
            "PUT", f"/rest/api/3/issue/{issue_key}/assignee",
            json={"accountId": account_id},
        )
        return True

    def add_comment(self, issue_key, comment_text):
        payload = {"body": self._to_adf(comment_text)}
        self._request("POST", f"/rest/api/3/issue/{issue_key}/comment", json=payload)
        return True

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def get_stats(self):
        """Return simple counts by status and priority for the whole project."""
        issues = self.search_tickets(max_results=200)
        by_status, by_priority = {}, {}
        for issue in issues:
            status = issue["fields"]["status"]["name"]
            priority = issue["fields"]["priority"]["name"]
            by_status[status] = by_status.get(status, 0) + 1
            by_priority[priority] = by_priority.get(priority, 0) + 1
        return {"total": len(issues), "by_status": by_status, "by_priority": by_priority}


class JSMAPIError(Exception):
    """Raised when the Jira API returns an error response."""

    def __init__(self, status_code, body, url):
        self.status_code = status_code
        self.body = body
        self.url = url
        super().__init__(f"Jira API error {status_code} calling {url}: {body}")
