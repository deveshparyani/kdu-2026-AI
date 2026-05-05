from __future__ import annotations

import json

from crewai import Agent, Crew, Task

from ..config import Settings
from .repositories import BillingDatabaseRepository, BillingVectorRepository
from .schemas import ConsensusOutput, WorkerSearchResult
from .tools import SearchBillingDatabaseTool, SearchBillingVectorTool


class RetrievalCrewFactory:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._db_tool = SearchBillingDatabaseTool(BillingDatabaseRepository())
        self._vector_tool = SearchBillingVectorTool(BillingVectorRepository())

        self._db_agent = Agent(
            role="DB Agent",
            goal="Retrieve the most relevant structured billing records using the approved database tool only.",
            backstory=(
                "You are a careful database retrieval specialist. "
                "You never attempt file access, secrets access, or arbitrary SQL."
            ),
            llm=settings.agent_model,
            tools=[self._db_tool],
            verbose=settings.verbose,
            allow_delegation=False,
        )
        self._vector_agent = Agent(
            role="Vector Agent",
            goal="Retrieve relevant billing support knowledge using the approved vector retrieval tool only.",
            backstory=(
                "You specialize in semantic retrieval across billing support knowledge. "
                "You never use filesystem access or request secrets."
            ),
            llm=settings.agent_model,
            tools=[self._vector_tool],
            verbose=settings.verbose,
            allow_delegation=False,
        )
        self._consensus_agent = Agent(
            role="Consensus Agent",
            goal="Combine worker results into one grounded answer without inventing missing facts.",
            backstory=(
                "You compare evidence from structured records and semantic knowledge, "
                "prefer authoritative database facts when they conflict, and clearly flag degraded confidence."
            ),
            llm=settings.agent_model,
            verbose=settings.verbose,
            allow_delegation=False,
        )

    async def run_db_worker(self, query: str, trace_id: str) -> WorkerSearchResult:
        task = Task(
            description=(
                "Use the database tool exactly once.\n"
                "Input query: {query}\n"
                "Trace id: {trace_id}\n"
                "Top K: {top_k}\n"
                "Return structured output only."
            ),
            expected_output="Structured WorkerSearchResult for database retrieval.",
            agent=self._db_agent,
            output_pydantic=WorkerSearchResult,
        )
        crew = Crew(agents=[self._db_agent], tasks=[task], verbose=self._settings.verbose)
        output = await crew.akickoff(
            inputs={"query": query, "trace_id": trace_id, "top_k": self._settings.retrieval_max_results}
        )
        if output.pydantic is None:
            raise RuntimeError("DB worker did not return structured output.")
        return output.pydantic

    async def run_vector_worker(self, query: str, trace_id: str) -> WorkerSearchResult:
        task = Task(
            description=(
                "Use the vector retrieval tool exactly once.\n"
                "Input query: {query}\n"
                "Trace id: {trace_id}\n"
                "Top K: {top_k}\n"
                "Return structured output only."
            ),
            expected_output="Structured WorkerSearchResult for vector retrieval.",
            agent=self._vector_agent,
            output_pydantic=WorkerSearchResult,
        )
        crew = Crew(agents=[self._vector_agent], tasks=[task], verbose=self._settings.verbose)
        output = await crew.akickoff(
            inputs={"query": query, "trace_id": trace_id, "top_k": self._settings.retrieval_max_results}
        )
        if output.pydantic is None:
            raise RuntimeError("Vector worker did not return structured output.")
        return output.pydantic

    async def run_consensus(
        self,
        query: str,
        db_result: WorkerSearchResult,
        vector_result: WorkerSearchResult,
        trace_id: str,
    ) -> ConsensusOutput:
        task = Task(
            description=(
                "Combine worker evidence into one answer.\n"
                "User query: {query}\n"
                "Trace id: {trace_id}\n"
                "Database result JSON:\n{db_result_json}\n"
                "Vector result JSON:\n{vector_result_json}\n"
                "Rules:\n"
                "- Prefer authoritative database facts when sources conflict.\n"
                "- If one worker failed, answer from the successful one and mark degraded confidence.\n"
                "- If both failed, set can_answer to false.\n"
                "- Never invent account details not present in the evidence.\n"
                "Return structured output only."
            ),
            expected_output="Structured consensus answer grounded in worker evidence.",
            agent=self._consensus_agent,
            output_pydantic=ConsensusOutput,
        )
        crew = Crew(agents=[self._consensus_agent], tasks=[task], verbose=self._settings.verbose)
        output = await crew.akickoff(
            inputs={
                "query": query,
                "trace_id": trace_id,
                "db_result_json": json.dumps(
                    db_result.compact_for_prompt(
                        max_records=self._settings.retrieval_prompt_records,
                        max_snippet_chars=self._settings.retrieval_prompt_snippet_chars,
                    ),
                    indent=2,
                ),
                "vector_result_json": json.dumps(
                    vector_result.compact_for_prompt(
                        max_records=self._settings.retrieval_prompt_records,
                        max_snippet_chars=self._settings.retrieval_prompt_snippet_chars,
                    ),
                    indent=2,
                ),
            }
        )
        if output.pydantic is None:
            raise RuntimeError("Consensus worker did not return structured output.")
        return output.pydantic
