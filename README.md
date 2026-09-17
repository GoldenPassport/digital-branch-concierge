# Digital branch concierge

Companion repository for *Structure at the edges, freedom in the middle* on
goldenpassport.blog: one bank branch concierge agent built in n8n and
LangGraph, with other leading automation platforms to follow, to test where
automated decision-making has to stop in a regulated industry.

The design is a sandwich, not a dial: deterministic process orchestration on
the outside, bounded and risk-rated skills on the inside and the agent free
in between. Two deterministic gates guard it. Pre-action authorisation runs
on every skill call. An impact and policy gate on the agent's output sends
flagged customers, medium-risk actions and requests that match its policy
keywords to a named decision owner.

| Folder | Status |
| --- | --- |
| `n8n/` | Built and run end to end on n8n cloud: workflows, README and test evidence. |
| `langgraph/` | Built and run end to end with LangGraph, LangChain and LangSmith: typed state graph, skills, gates, tests, evaluation and README. |
| `shared/` | Demo customer records, knowledge documents and the test conversations every build uses. See its README for the two versions of the test set. |

- Article: https://www.goldenpassport.blog/blog/digital-branch-concierge
- n8n walkthrough: https://www.goldenpassport.blog/blog/digital-branch-concierge-n8n-demo
- LangGraph walkthrough: https://www.goldenpassport.blog/blog/digital-branch-concierge-langgraph-demo

Everything here uses invented demo data. The builds are learning builds, not
production banking services or certifications of regulatory compliance.
