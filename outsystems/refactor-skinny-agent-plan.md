# Refactor: skinny agent app, case management in the Chatbot app

Decided 22 Oct 2026. Goal: the Branch Concierge Agent asset (type AIAgent) holds only the AI agent and its skills. Case management (data, lists, decisions, gate, SLA, headline) lives in the Branch Concierge Chatbot App. Dependencies run one way only: Chatbot -> Agent app (and Workflow -> Chatbot). The agent app never depends on the Chatbot.

Why (ODC docs): an agentic app is a separate element consumed through a generated Call<AgentName> service action, "managed apart from the consumer's core logic"; AI agents "run without a user interface" and get business data through grounding or tools. Apps "solve a specific business need" and stay loosely coupled through service actions and public entities. Where to set ownership is the architect's decision (Mentor output needs review).

## What stays in the agent app (AI + skills + mock core banking)

- AI agent: AgentFlow, CallBranchConciergeDemo, BuildMessages, GetGroundingData, StoreMemory, Memory entity, the SummariseCase / ClassifyReply / CheckReply agents (ClassifyCustomerReplyFlow, ReplyCheckFlow, SummariseCustomerCase's model call).
- Skills (tools the AI agent calls): Knowledge, OpeningHours, FetchBalance, PrintStatement, FindSlots, BookAppointment, UpdateContactDetails, Authorise.
- Mock core banking used by the skills: Customer, Appointment, ContactChangeRequest, Capability, KnowledgeSection, DecisionLog (the skills' audit trail), ConciergeSession.
- New thin public service actions for the Chatbot:
  - RunAgentTurn(SessionId, CustomerId, Message, Guidance, History) -> Reply, QuestionType, AwaitingCustomer, Reasons, TurnStart (no case writes).
  - GetTurnDecisions(SessionId, SinceUtc) -> DecisionLog rows of this turn (for the gate).
  - SummariseTranscript(Transcript) -> Headline topics, Summary (no case writes).
  - ClassifyReply(Text) -> intent.
  - ExecuteSkill / existing skill actions as needed for confirm-then-execute.

## What moves to the Chatbot app (case management)

- Entities: CustomerCase, ReviewCase, ReviewRound, ReviewCaseEvent, CaseEvent, CaseEventKind (static), ChatMessage, Conversation, ConciergeReply, LearningExample.
- Case logic (all current case service/server actions): SubmitCustomerRequest, SubmitCustomerReply / AcceptCustomerReply, TrackCaseForSession, EnsureCustomerCase, CreateChatMessageRecord, DeliverReply, ListReplies, GetChatHistory, GetCurrentCase, GetCaseDetail, ListCustomerCases, ListCasesForReview, ListReviewCases, ListReviewRounds, GetReviewCaseSummary, GetSessionRouting / RouteForSession, PrepareCustomerWait, CloseCustomerWait, GetReviewTimeout, SecondsUntil, CalculateSlaDueOn, ToUkTime, OpenReviewRound, CloseReviewRound, RecordReviewDecision, RecordReviewOutcome, EscalateReviewCase, AddCustomerFollowUp / AttachFollowUp, CaptureLearning, PromoteLearningExample, SetLearningFlag, ListLearningExamples, ExportLearningAsEvalCases, SetOutcomeReply, GetReviewOutcome, CloseCustomerCase, AutoCloseIdleCases, RefreshCaseHeadline, AddCaseEvent / LogCaseEvent, TriageCustomerReply, ArchiveTestData, ClearEvaluationRun, RepairCaseData, Backfill*.
- Orchestration wrappers that today mix AI and case writes: RunAgent, RunAgentFollowUp, RunAgentWithGuidance, RunImpactPolicyGate / ImpactPolicyGate (deterministic policy, not AI). In the Chatbot they become: load case context -> call agent app RunAgentTurn -> run the gate on GetTurnDecisions -> write case records.
- ReviewCases lists become screen aggregates on the Chatbot's own entities (sort + paging in the database). Prompt 32 is superseded by this.

## Data

Moving an entity to another app in ODC creates a new, empty table. Old cases (CASE-0001..0042) and learnings are not migrated: this is demo data. After the move: run BootstrapCustomers (Customer stays in the agent app, so customers are kept), then run fresh tests.

## Order of work

1. Chatbot app: copy the case entities from the agent app tab (Studio copy/paste between open apps), then the case actions. Fix references so they use the Chatbot's own entities. Publish.
2. Agent app: add RunAgentTurn, GetTurnDecisions, SummariseTranscript, ClassifyReply (thin, no case writes). Publish.
3. Chatbot app: rebuild RunAgent / RunAgentFollowUp / RunAgentWithGuidance / gate as case-side orchestration calling the agent app. Point Chat, ReviewCases, CaseFileModal at local actions. ReviewCases tables as aggregates. Publish.
4. Workflow (Portal editor, by hand): rebind every node to the Chatbot service actions (same names and signatures where possible). Publish.
5. Agent app: delete the moved entities and actions once nothing references them. Publish. Check that app_refs shows Chatbot -> Agent only.
6. Fresh data + full test: straight-through, held + approve + confirm + execute, reject, multi-request, timeout close, learning capture + promote, headline, hero cards, sorting.

## Status 22 Oct 2026, 14:50

- Done (unpublished, checkpoint `apps/Branch Concierge Chatbot App - refactor WIP.oml`): 10 case entities, 7 case structures, 22 case server actions, 36 case service actions copied into the Chatbot; Chatbot's references to the agent's case elements removed. Agent app published with AgentTurn, GetTurnDecisions, SummariseTranscript, ClassifyCustomerReply, CheckAgentReply.
- 263 errors left in the Chatbot:
  1. Writes to agent-owned tables (DecisionLog, ConciergeSession, Memory, ContactChangeRequest): add thin agent service actions (by hand).
  2. AI calls in RunAgent, RunAgentFollowUp, RunAgentWithGuidance, SummariseCustomerCase, TriageCustomerReply: rewire to the AI interface (Mentor).
  3. Events CustomerRequestReceived, CustomerReplied, ReviewDecided, ReviewEscalated: recreate in the Chatbot, rebind workflow triggers (by hand).
  4. SQL nodes still pointing at the agent's CustomerCase: re-point (Mentor).
  5. TrackCaseForSession did not paste: copy again.
- ReviewCases: delete the Learnings hero card's "<n> promoted" subtext (Luke, 22 Oct).
- After the refactor publishes: append `theme-css-pending.css` to the Chatbot theme (Review cases layout + blue/grey bubbles).

## Status 31 Oct 2026, 07:30

- Checkpoint: `apps/Branch Concierge Chatbot App - refactor WIP 2.oml` (unpublished; Studio work in progress). Agent app published 30 Oct, Revision 37, with the six write/read services from prompt 34.
- Chatbot errors 240 -> 60. Done: case data re-pointed to the chatbot's own entities and structures (stage 2); settings CustomerReplyTimeoutMinutes (10) and CaseAutoCloseHours (24) and ToUkTime added; 12 `...Logic` server actions created by hand (copy a service action, paste on the Server Actions folder, rename) and call sites rebound by Mentor.
- Started (Mentor stopped at its daily limit, resets about 16-17 h after 07:30): stages 3 and 4. Changed so far: ImpactPolicyGate, PromoteLearningExampleLogic, RecordReviewDecisionLogic, SetLearningFlagLogic, EscalateReviewCase, RecordReviewOutcome, RunAgent.
- Left: AgentFlow / CallClassifyReply / CallSummarise / Headline expression errors (stage 4), CreateDecisionLog etc. (stage 3), check the 12 service actions are thin wrappers over their Logic actions, delete RepairCaseData and ArchiveTestData, events cleanup (one public event each, no "2" suffix), then publish, rebind the workflow, retest.
- Next Mentor message: resend the stage 3 + 4 instruction (agent-table writes -> LogDecision / UpsertConciergeSession / ClearSessionAgentData / SetContactChangeStatus; AI calls -> AgentTurn / GetTurnDecisions / SummariseTranscript / ClassifyCustomerReply / CheckAgentReply / ExecuteSkill).

## Status 1 Nov 2026, 02:10

- Agent app published: Revision 38 (AgentTurn now also returns CustomerExpectedBy and ExpectationReason; unused variables removed from SummariseTranscript). Zero warnings.
- Chatbot: valid, 0 errors, 0 warnings in Studio. Events renamed (CustomerRequestReceived, CustomerReplied, ReviewDecided, ReviewEscalated, public). RepairCaseData and ArchiveTestData deleted. RunAgent / RunAgentFollowUp / RunAgentWithGuidance map the two new AgentTurn outputs.
- Chatbot publish FAILS twice at compile: Internal Error (OS-BEW-RDM-50000), then OS-DPL-50205. RDM = relational data model, so suspect the 10 case entities copied from the agent app (same names / keys as the agent's still-existing tables). Need publish_logs from the OutSystems MCP (re-auth via /mcp) before changing anything.
- 02:25 update: still failing after Studio restart (1.7.30), Mentor's mapping scan (fixed LogCaseEvent's CreateReviewCaseEvent mapping) and App > Remove unused elements (31 stale refs, incl. agent "...2" entities). Revisions 42-44 all fail with OS-BEW-RDM-50000.
- A clone of the same model (CloneOfBranchConciergeChatbotApp, key ddbb016b-7030-4d80-b684-c0aaad533f5c) publishes fine (Revision 1): the model is OK; the original app's deployment state is broken (likely: it used to consume the agent's CustomerCase etc. and now owns entities with the same names). Plan: make the clone the chatbot, delete the original (after Luke confirms), rename the clone, rebind the workflow.
- Workflow note from Mentor: the workflow passes RunAgent outputs into RunImpactPolicyGate; check that mapping when rebinding.

## Status 3 Nov 2026, 12:20 (fresh install)

- Old agent, chatbot and workflow were deleted from the tenant. Agent V2 (key ff5ef8fc-0248-47b5-84d4-ce5c4853b312) and Chatbot App V2 (key ddbb016b-7030-4d80-b684-c0aaad533f5c) imported and published, both Revision 1 on the tenant. `apps/*.oml` re-saved after publish; the chatbot file now has zero references to the old agent key.
- How the 269 import errors were cleared: add Agent V2 public elements (not its leftover CustomerCase), repoint leftover data sources to local entities, delete the old agent reference, rename the "...2" actions and role back to their original names (calls rebind), re-tick DecisionOwner on CaseDetail, Chat and ReviewCases. TrueChange said "valid" while calls were still bound to the deleted agent, so check the Logic tree, not only the error list.
- Workflow imported, all 24 bindings moved to Chatbot App V2 (role to Agent V2) and published 12:54 as Revision 1, key ada195e8-d13d-43c6-9251-f80f9b1065f3. Portal editor: delete a binding, re-pick the same name; action input mappings survive, but a wait or human task loses its event condition (restored: SessionId = Start.CustomerRequestReceived.SessionId; ReviewCaseId = RunImpactPolicyGate.RunImpactPolicyGate.ReviewCaseId). The role shows as DecisionOwner2 in the workflow (alias only). The workflow .oml in the repo is still the old 21 Oct export: re-export it.
- To check in the retest: DeliverReply's new QuestionType input and PrepareCustomerWait's LastQuestionType are unmapped in the workflow, so quick replies and triage may not get the question type.
- Left: assign DecisionOwner to Luke; run BootstrapCustomers; check the AI model; remove leftover CustomerCase and CaseEventKind from Agent V2; full retest.

## Article note

"In production the case data lives in a case-management app or core service, never in the agent. The agent is a pure reasoning step with tools; the workflow and case app own state, policy and audit."

## Status 4 Nov 2026, 09:30

Agent V2 published with new public action `ApplyContactChange`; Chatbot App V2 published 4 Nov 09:06. Verified in the Customer and ContactChangeRequest tables, not only in chat:

| Test | Case | Reply | Customer.Phone | Request status |
| --- | --- | --- | --- | --- |
| Approve + yes | CASE-0067, C1004 | "Done. I have changed your phone number..." | changed to +44 7700 900555 | applied (one row) |
| Approve + no | CASE-0068, C1003 | "I have not made any change..." | unchanged | cancelled |
| Reject with note | CASE-0069, C1001 | "not approved", passes on the note | unchanged | rejected |

- Lesson: "Done" was false until 3 Nov: nothing ever wrote Customer, ExecuteSkill only logged a pending request, and its Success meant "logged". The agent also repeated the new number from chat history. Check tables, not replies.
- Prompts 41 to 45 sent. Mentor hit its usage limit before reporting on 45, so how it matches the request has not been read; the tests above show the newest request is chosen when older pending rows exist.
- ID jumps (6 to 34, 36 to 67, and the same in ContactChangeRequest) look like database sequence blocks after idle or publish, not failed runs. Inference only; harmless.
- Open: "no" path Reasons says "confirmed by the customer"; "Next: anything else?" on held cases; overview wording while pending; leftover pending rows 1 to 38 from old tests; multi-request, timeout filing, learning capture/promote, refused request, sorting; re-export workflow .oml; drop V2 names; README and blog update.

## Status 4 Nov 2026, 10:00 (multi-request test, CASE-0070, C1004)

Worked: balance straight through; phone change in the same case held, approved, confirmed, applied (+44 7700 900888, request 70 applied); question during hold logged as review_pending; second change (email) held again, not carried by the first approval.

Failed, see `mentor-prompts/46-multi-request-fixes.txt` (not sent: Mentor limit resets about 13:10):
1. Correcting the value after approval skips review: route straight_through, "pre-approved", no review case, customer told staff will approve. Customer.Email did not change, so no unapproved write; requests 71 and 72 stuck pending.
2. Question asked during the hold is never answered.
3. Overview false: "no pending reviews", "approved and carried out".
4. Headline counts wrong. Also remove "Next:" (Luke has not objected; confirm before sending), fix "no" reasons, delete Decided by.

## Status 4 Nov 2026, 10:20

Chatbot Revision 13 published (prompt 46: items 1, 3 to 7; item 2 not started). Correction test passed on CASE-0071, checked in tables: first address superseded, corrected address opened its own approval, "Yes" during the hold applied nothing, then approved + confirmed = Customer.Email daniel.second@example.com, request applied. Requests 71 and 72 from before the fix stay pending. Prompt 47 sent: direct Reference link on the review case, "0 open" timing, overview on corrected cases, design for follow-ups during a hold.

## Status 4 Nov 2026, 11:10

Chatbot published 11:00 with prompt 47: ReviewCase.ChangeReference links each review to its request; headline refresh after the gate; superseded rounds labelled. Verified on CASE-0072, C1003, with old pending requests 35 and 36 for the same number: yes applied only new request 75, Customer.Phone +44 7700 900333, 35 and 36 stayed pending. "1 open" shows immediately after a hold. "No" on the email change: reply and reasons correct; request status still to read from the table.

Follow-ups during a hold, not built (Mentor's design): RunAgentFollowUp reads the review case's "Customer follow-up" events into FollowUpMessage for the decision reply. Contact-change approvals skip the agent, so they need a second agent turn after the change is applied (RunAgent on yes, or an extra workflow RunAgentFollowUp call, sent as a separate message). A plain "yes", "ok" or "thanks" during a hold should get a neutral status line and not be logged as a follow-up.

## Status 4 Nov 2026, 11:30

- "No" confirmed in tables: request 76 cancelled, C1003 email unchanged.
- Timeout passed on CASE-0072: closing message on the right case at 11:16 (10 minutes after the last reply), case closed, message bar hidden.
- Refused request FAILED on CASE-0073: route review, reasons "policy keyword in request;empty reply", no refusal. Nothing executed. Headline compounds ("0 open · 0 open · ..."), overview and proposed reply empty, reject note not passed on. See prompt 49 (not sent yet).
- Learning capture inconclusive: rejected CASE-0073 with Flag for learning clicked, not listed under Learnings, but the tick was not confirmed before Reject, and that case is abnormal. Retest on a normal case with the tick checked first.
- Prompt 48 (answer follow-ups after a hold) sent, Mentor working.
- Still to test: learning capture and promote, sorting, follow-ups after prompt 48.

## Status 4 Nov 2026, 11:55

Chatbot published 11:45 with prompt 48. Verified on CASE-0074, C1004: question during hold shown as "Customer also asked"; "Thanks" got the neutral line and was not logged; approve; yes = "Done", then a separate reply "We close at 13:00 on Saturdays"; Customer.Phone +44 7700 900123, request 77 applied. Learning flag ticked (checked) and captured: row under Learnings, hero count 2.

Regression: the "Done" reply's Reasons is now blank on the turn with a follow-up (was "approved by ..., confirmed by the customer"). Check DecisionLog too.
Open: flagged learning goes straight to Promoted = Yes with blank Guidance, no separate promote step on screen: check against intended design. Limit from Mentor: a review opened by the second turn does not trigger the workflow's review wait or SLA timer. Kind ("approva") and Case clip at about 1230px wide: widen in the theme after prompt 49.

Guardrail setting checked 4 Nov 12:00: Management > Configure > Agent guardrails, Development stage: Prompt attack detection Active, Block request and raise exception. So CASE-0073 is not a missing setting.
Logs confirm: guardrail fired in AgentTurn at 11:24:10 (OS-ABRS-FM-40005) and on each SummariseTranscriptFlow call. The block works; the refused signal is lost. See mentor-prompts/49b-refused-evidence.txt.

## Status 4 Nov 2026, 12:10

Agent published 12:04 (AgentTurn: guardrail block sets RawResponse guardrail_blocked, DecisionLog Step guardrail, Outcome refused). Chatbot published 12:05, Revision 16. Refused route passed on CASE-0075: polite refusal, route refused, reason "input guardrail: prompt attack detection", no review case, case closed. Workflow needed no change. Prompt 50 (sorting, blank Done reason, learning question) sent.

## Status 4 Nov 2026, 12:25

Chatbot Revision 17 published 12:14 (prompt 50 + width CSS). Verified: Decided sorts by Case both ways and Raised by real date, default newest decision first; "approval" no longer clips at about 1230px. Done reason passes on CASE-0077 with a follow-up: "approved by Luke Audie, confirmed by the customer", then a separate Saturday answer. Only Decided sorting was clicked; Inbox and Learnings headers not clicked.

Agent test results for the article: see the status sections from 4 Nov. Decision needed: promoted learnings do not reach the agent. Every AgentTurn call leaves LearningExamples empty, flag and promote are merged in SetLearningFlagLogic, and rows are only listed, counted and exportable with ExportLearningAsEvalCases. Do not claim in the article or poster that promoted learnings improve live replies unless this is built.

Left: learnings decision; clear test data (pending rows 1 to 38, 71, 72; garbled closed cases); Save all three .oml to the master folder (apps now open from the server; workflow from Portal); README/mentor-prompts README; article; commit.

## Status 4 Nov 2026, 13:20: normal replies failing

Chatbot Revisions 18 and 19 (prompts 51, 52). Plain questions go to review with "empty reply" (CASE-0078, 0079, 0080). DecisionLog row 156: "AgentTurn returned an empty reply. Learnings passed: 0. Raw response:" (empty). Failed turns write no authorise or reply_check rows. Summaries fail too (fallback topic "Customer request"), though prompt 51 did not touch the summariser. Last good turn 12:19 on Revision 17; agent app unchanged since 12:04. Runtime logs and traces show nothing after 12:18. So likely the model call rather than learnings, but not proven. Next: check the DeepSeek balance; if fine, republish Revision 17 as a test.
Not done: Test agent would create a new test app (uses a component slot), so cancelled.

## Status 4 Nov 2026, 13:35

Empty replies 13:03 to 13:15 were an empty DeepSeek balance, not the learnings change. Luke topped it up; replies recovered with no code change, on Revision 19. Lesson: an empty balance looks like a normal hold (route review, "empty reply"), with nothing in logs.

Learnings on Revision 19, reply checked in chat, audit in DecisionLog:
- Blank Guidance refused; Guidance with a phone and email refused.
- Promoted "End every reply by wishing the customer a lovely day." on CASE-0074 (C1004). C1003 same question: before, no wish; after, "Have a lovely day"; learnings_used rows 171 and 175.
- Held change stayed held with the learning active (CASE-0078, route review, skill risk medium).
- Demoted: C1004 reply has no wish; no learnings_used row on that turn. Different customer from the "after" run, so not a like-for-like control.
- Not tested: new flag creating Promoted = False. Prompt text itself not inspected (privacy check is Mentor's report plus the promotion refusals); plain names in Guidance are not detected.

Found: publishing Agent V2 runs BootstrapOnPublish, which reset Customer to seed values at 12:04 (C1003 phone back to 900103, C1004 email back to daniel.reyes@). Applied changes before that are gone from Customer though requests still say applied. Document it; avoid republishing the agent during a demo. Prompt 53 written, not sent.

## Saved 4 Nov 2026, 13:40

`apps/*.oml` exported from Studio: Agent V2 Revision 3, Chatbot App V2 Revision 19. Workflow .oml in the repo is still the 1 Nov export; the live workflow is Revision 1 of 3 Nov 12:54 (Export to OML is in the workflow editor's more options menu). Prompt 53 written, not sent.
