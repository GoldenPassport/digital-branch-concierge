# Shared data

The records, knowledge and test conversations every build of the concierge
uses, so the builds can be compared on the same inputs. All of it is
invented demo data: the names are fictional, the email addresses use
`example.com` and the phone numbers sit in Ofcom's 07700 900 range reserved
for drama.

| File | What it is |
| --- | --- |
| `data/customers.csv` | Four demo customers with an account, balance, contact details and two flags. C1001 has an open complaint, C1002 has a vulnerability flag, C1003 is the default customer and C1004 has an overdrawn balance. |
| `knowledge/fees-and-product-terms.md` | Current accounts, statements, mortgages and contact details. What the concierge may answer from. |
| `knowledge/branch-policies-and-faqs.md` | Opening hours, identification, appointments, complaints, vulnerable customers, and what the concierge may do and must never decide. |
| `evaluations/test-conversations.csv` | Version 1 of the twelve test conversations, with the expected route and skill. The n8n build was run and scored against this file. |
| `evaluations/test-conversations-v2.csv` | Version 2, used by the LangGraph build. |

## The two versions of the test set

Version 2 changes only the expected skill for two conversations, after a
reviewed LangGraph run showed the original expectation was wrong:

| Test | Version 1 | Version 2 | Why |
| --- | --- | --- | --- |
| T03 | `book_appointment` | `knowledge` | The customer asked what to bring. Answering and offering a slot is right; booking without the customer choosing is not. |
| T04 | `book_appointment` | `find_slots` | "Tomorrow afternoon" matches more than one adviser slot, so the agent should ask which one rather than book. |

The expected routes are identical in both versions, so the n8n results,
which score routes, still stand. Version 1 is kept unchanged because the
n8n Data Table and its recorded evidence were built from it.

## Columns in the test sets

- `test_id`: T01 to T12. Not `id`, which is reserved in n8n Data Tables.
- `message`: what the customer types.
- `customer_id`: the identified customer for the conversation.
- `expected_route`: `straight_through`, `review` or `refused`.
- `expected_skill`: the skill or tool that should run, or empty when none
  should.
- `note`: what the conversation is testing.
