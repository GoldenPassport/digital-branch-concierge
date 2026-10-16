# Mentor prompts for the OutSystems build

Send these to Mentor in ODC Studio in order, one at a time, waiting for each
to finish, then Publish. They are the corrected versions of the prompts used
on 5 and 6 October 2026: the fixes found in testing (no SQL nodes, the call
condition, word-scoring knowledge search, the guardrail handler, the
policy-earlier flag in the refused path) are folded in, so a fresh build
should not need the fix-up prompts. Prompt 06 needs prompt attack detection
switched on in the Portal first. Mentor on the Personal Edition has a daily
usage limit; six prompts fitted in one day, ten did not.

Prompts 07 to 09 add the outer process (work in progress, October 2026):

- 07 (agentic app): the DecisionOwner role, the ReviewRequested and
  ReviewDecided events, and the actions to list, read and decide review cases.
- 08 (agentic app): the CustomerRequestReceived event and the steps a workflow
  calls in turn: RunAgent, RunImpactPolicyGate, DeliverReply, ListReplies and
  RunAgentFollowUp. CallBranchConcierge stays as it is for the evaluations.
- 09 (test app): the chat raises CustomerRequestReceived and shows the replies
  the workflow delivers, plus a Review cases screen for the decision owner.
  Before sending 09, add the elements from Branch Concierge Demo to the test
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
