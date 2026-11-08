# Mentor prompts for the OutSystems build

Send these to Mentor in ODC Studio in order, one at a time, waiting for each
to finish, then Publish. They are the corrected versions of the prompts used
on 5 and 6 October 2026: the fixes found in testing (no SQL nodes, the call
condition, word-scoring knowledge search, the guardrail handler, the
policy-earlier flag in the refused path) are folded in, so a fresh build
should not need the fix-up prompts. Prompt 06 needs prompt attack detection
switched on in the Portal first. Mentor on the Personal Edition has a daily
usage limit; six prompts fitted in one day, ten did not.

App names: the prompts use the current names, Branch Concierge Agent (the
agent app) and Branch Concierge Chatbot App. When they were first sent the
apps were called Branch Concierge Demo and Branch Concierge Demo test app.

Prompts 07 to 09 add the outer process (work in progress, October 2026):

- 07 (agent app): the DecisionOwner role, the ReviewRequested and
  ReviewDecided events, and the actions to list, read and decide review cases.
- 08 (agent app): the CustomerRequestReceived event and the steps a workflow
  calls in turn: RunAgent, RunImpactPolicyGate, DeliverReply, ListReplies and
  RunAgentFollowUp. CallBranchConcierge stays as it is for the evaluations.
- 09 (chatbot app): the chat raises CustomerRequestReceived and shows the replies
  the workflow delivers, plus a Review cases screen for the decision owner.
  Before sending 09, add the elements from Branch Concierge Agent to the chatbot
  app with App > Add public element; Mentor does not add them itself.

Prompts 10 to 12 complete it:

- 10 (both apps): the decision owner can edit the proposed reply; the case
  stores the edited reply and the reply the customer actually received.
- 11 (both apps): the gate's three flags (straight through, approval,
  review), the reviewer's outcomes (release, send back with guidance, take
  over), the agent retrying with guidance, and the learning loop: captured,
  promoted and exported as evaluation cases.
- 12 (both apps): SLAs in UK working hours, escalation, and the process
  instance id on every case and audit row.

The workflow itself is built in the Portal's workflow editor, not by Mentor.

Prompts 13 to 71 came after: 13 to 56 the case model, the review screens
and the refactor to a skinny agent (Agent V2 and Chatbot App V2, see
`../refactor-skinny-agent-plan.md`), 57 to 70 chat display, staff decision
and approval confirmation fixes found in the November retests. 71 (a guard
against one Enter press sending twice), 72 (case badge order and labels) and
73 (a session per customer) were sent through the OutSystems MCP connection
on 7 November 2026 and published as Chatbot App V2 revisions 2, 3 and 4. 74
was a lost-send report that turned out to be the test typing into a disabled
box; its changes were discarded. 75 (Agent V2: offer slots and book only after the customer has chosen) was published as Agent V2 revision 2 on 8 November. See `../evaluations/clean-run-2026-11-07.md`.
