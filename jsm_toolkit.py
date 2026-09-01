#!/usr/bin/env python3
"""
Jira Service Management Ticket Toolkit
=========================================
A command-line front-end for managing IT support tickets in a real
Jira Service Management project, using the Jira Cloud REST API.

This does everything a helpdesk technician does day-to-day, without
leaving the terminal: create tickets, view/search them, change status,
assign them, comment, and pull a quick stats dashboard.

Author: (your name here)
License: MIT

Setup required before running — see README.md. In short:
  1. Create a .env file (copy .env.example) with your Jira site URL,
     email, API token, and project key.
  2. pip install -r requirements.txt --break-system-packages
"""

import csv
import sys

from dotenv import load_dotenv

from jsm_client import JSMClient, JSMAPIError, VALID_PRIORITIES

load_dotenv()  # reads variables from a local .env file, if present


def prompt(text, default=None, required=False):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{text}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if not value and required:
            print("This field is required.")
            continue
        return value


def choose_from(text, options):
    print(f"{text}: {', '.join(options)}")
    while True:
        value = input("> ").strip()
        for option in options:
            if value.lower() == option.lower():
                return option
        print(f"Please choose one of: {', '.join(options)}")


def print_ticket_row(issue):
    fields = issue["fields"]
    priority = fields.get("priority", {}).get("name", "n/a")
    status = fields.get("status", {}).get("name", "n/a")
    assignee = fields.get("assignee")
    assignee_name = assignee["displayName"] if assignee else "Unassigned"
    print(f"{issue['key']:<10} | {priority:<8} | {status:<14} | "
          f"{fields['summary'][:40]:<40} | {assignee_name}")


def print_ticket_detail(issue):
    fields = issue["fields"]
    assignee = fields.get("assignee")
    print("-" * 70)
    print(f"Ticket: {issue['key']}")
    print(f"  Summary   : {fields['summary']}")
    print(f"  Status    : {fields['status']['name']}")
    print(f"  Priority  : {fields.get('priority', {}).get('name', 'n/a')}")
    print(f"  Assignee  : {assignee['displayName'] if assignee else 'Unassigned'}")
    print(f"  Labels    : {', '.join(fields.get('labels', [])) or 'none'}")
    print(f"  Created   : {fields.get('created', 'n/a')}")
    print(f"  Updated   : {fields.get('updated', 'n/a')}")
    print("-" * 70)


def menu():
    try:
        client = JSMClient()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        sys.exit(1)

    while True:
        print("\n=== Jira Service Management Ticket Toolkit ===")
        print("1. Create new ticket")
        print("2. View / search tickets")
        print("3. View ticket detail")
        print("4. Change ticket status")
        print("5. Assign ticket")
        print("6. Add a comment")
        print("7. Export tickets to CSV")
        print("8. View statistics dashboard")
        print("0. Exit")
        choice = input("Select an option: ").strip()

        try:
            if choice == "1":
                summary = prompt("Issue summary (short title)", required=True)
                description = prompt("Description")
                priority = choose_from("Priority", VALID_PRIORITIES)
                labels_raw = prompt("Labels/category, comma-separated (e.g. network,vpn)")
                labels = [l.strip() for l in labels_raw.split(",") if l.strip()]
                key = client.create_ticket(summary, description, priority=priority, labels=labels)
                print(f"Created ticket: {key}")

            elif choice == "2":
                jql = prompt(
                    "JQL filter (leave blank for all tickets in project, "
                    "e.g. 'status = \"In Progress\"')"
                )
                issues = client.search_tickets(jql or None)
                if not issues:
                    print("No tickets found.")
                for issue in issues:
                    print_ticket_row(issue)

            elif choice == "3":
                key = prompt("Ticket key (e.g. ITSD-12)", required=True)
                issue = client.get_ticket(key)
                print_ticket_detail(issue)

            elif choice == "4":
                key = prompt("Ticket key", required=True)
                transitions = client.get_available_transitions(key)
                names = [t["name"] for t in transitions]
                if not names:
                    print("No transitions available for this ticket.")
                    continue
                new_status = choose_from("New status", names)
                client.transition_ticket(key, new_status)
                print(f"{key} moved to '{new_status}'.")

            elif choice == "5":
                key = prompt("Ticket key", required=True)
                email = prompt("Assignee's Jira account email", required=True)
                client.assign_ticket(key, email)
                print(f"{key} assigned to {email}.")

            elif choice == "6":
                key = prompt("Ticket key", required=True)
                text = prompt("Comment text", required=True)
                client.add_comment(key, text)
                print("Comment added.")

            elif choice == "7":
                filename = prompt("Export filename", default="jsm_tickets_export.csv")
                issues = client.search_tickets(max_results=200)
                if not issues:
                    print("No tickets to export.")
                    continue
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Key", "Summary", "Status", "Priority", "Assignee", "Created"])
                    for issue in issues:
                        fields = issue["fields"]
                        assignee = fields.get("assignee")
                        writer.writerow([
                            issue["key"], fields["summary"],
                            fields["status"]["name"],
                            fields.get("priority", {}).get("name", "n/a"),
                            assignee["displayName"] if assignee else "Unassigned",
                            fields.get("created", "n/a"),
                        ])
                print(f"Exported to {filename}")

            elif choice == "8":
                stats = client.get_stats()
                print("\n--- Ticket Statistics ---")
                print(f"Total tickets: {stats['total']}")
                print("By status:")
                for status, count in stats["by_status"].items():
                    print(f"  {status}: {count}")
                print("By priority:")
                for priority, count in stats["by_priority"].items():
                    print(f"  {priority}: {count}")

            elif choice == "0":
                print("Goodbye!")
                sys.exit(0)

            else:
                print("Invalid option, please try again.")

        except JSMAPIError as exc:
            print(f"Jira API error: {exc}")
        except ValueError as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    menu()
