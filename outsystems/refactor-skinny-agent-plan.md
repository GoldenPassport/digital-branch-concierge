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

## Article note

"In production the case data lives in a case-management app or core service, never in the agent. The agent is a pure reasoning step with tools; the workflow and case app own state, policy and audit."
