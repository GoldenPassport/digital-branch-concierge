"""Governed skills: bounded, typed, risk-rated capabilities the agent can call but not modify."""

from concierge.skills.book_appointment import book_appointment
from concierge.skills.fetch_balance import fetch_balance
from concierge.skills.print_statement import print_statement
from concierge.skills.update_contact_details import update_contact_details

SKILLS = [print_statement, fetch_balance, book_appointment, update_contact_details]
