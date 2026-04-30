## Phase 1

### How many retries does the agent attempt before stopping?

In the current code, the database tool is queried 3 times in total. After the third consecutive failure, the circuit breaker opens and the agent stops trying again.


## Phase 2

### How does the system handle: "What is John’s salary and how much PTO does he have?"

The Coordinator Agent breaks the question into two parts. It sends the salary part to the Finance Agent and the PTO part to the HR Agent. In the current run, the final answer was: "John's salary is $90,000 USD annually, and he has 12 days of PTO remaining."

### How does the Coordinator sequence delegation?

The Coordinator first understands the request, then delegates each part to the correct specialist agent, and finally combines both answers into one response. It does not use finance or HR tools directly.

### Why is tool isolation critical for reducing prompt bloat?

Tool isolation keeps the Coordinator small and focused. Since it only gets delegation tools, its prompt does not need to describe every finance and HR tool in detail.

### Why is tool isolation critical for improving reliability?

Tool isolation reduces mistakes. The Finance Agent only handles salary-related work, and the HR Agent only handles PTO-related work, so each agent has a much narrower job and is less likely to call the wrong tool.


## Phase 3

### How do you pass a structured Context Payload during handoff?

In the current code, the shared app state is passed through `AppContext`, and the finance-specific fields are passed as structured tool arguments like `routing_number`, `account_number`, and `account_type`. Inside the tool, those fields are validated with the `BankingDetailsPayload` model.

### How do you ensure only relevant data is passed?

The Coordinator instructions explicitly say to pass only the finance-related fields needed for the task. That means only the task intent and banking fields are forwarded.

### How do you ensure full chat history is NOT transferred?

The current design avoids passing full chat history by not storing or forwarding unrelated messages during delegation. The Finance Agent only receives the relevant banking request and the shared `AppContext`, not the entire conversation transcript.


## Phase 4

### How does this prevent data loss?

It prevents data loss because important values are pulled out of the raw document and saved in a structured dictionary. Even if later chat messages are irrelevant, the critical facts are already preserved separately.

### How does this prevent context degradation?

It prevents context degradation because the agent does not rely only on a long running chat history. Instead, it keeps a clean structured memory of the important facts, so messages like "okay" or "cool" do not weaken or replace the useful data.


## Phase 5

### How do you pass memory between Planner and Executor?

Memory is passed through the shared `WorkflowContext` object. The planner output, execution log, original request, and shared step memory are all stored there, and the Executor reads them through the `fetch_shared_memory` tool.

### How do you maintain consistency across steps?

Consistency is maintained by using a structured plan, fixed `step_id` values, explicit dependencies, and one shared memory object that gets updated after every completed step.

### What is the biggest architectural advantage of Planner–Executor vs raw API chaining?

The biggest advantage is separation of concerns. The Planner focuses only on deciding what should happen next, and the Executor focuses only on doing the work. This makes the workflow easier to debug, easier to extend, and much safer than a long chain of ad-hoc API calls.
