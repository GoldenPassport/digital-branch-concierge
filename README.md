# Digital branch concierge, three ways

Companion repository for *Structure at the edges, freedom in the middle* on
goldenpassport.blog: one bank branch concierge agent built in n8n, Camunda
and LangGraph to test where automated decision-making has to stop in a
regulated industry.

The design is a sandwich, not a dial: deterministic process orchestration on
the outside, bounded and risk-rated skills on the inside and the agent free
in between. Two deterministic gates guard it. Pre-action authorisation runs
on every skill call. An impact and policy gate on the agent's output routes
anything the law or policy names to a named decision owner.

| Folder | Status |
| --- | --- |
| `n8n/` | Built and run end to end on n8n cloud: workflows, README and test evidence. |
| `camunda/` | Coming: BPMN model, AI Agent connector, job workers. |
| `langgraph/` | Coming: typed state graph, tools, tests. |
| `shared/` | Customer records, knowledge documents and the evaluation set all three builds use. |

Article: https://www.goldenpassport.blog/blog/digital-branch-concierge
