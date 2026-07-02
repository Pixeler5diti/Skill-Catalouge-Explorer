"""
ChatEngine — redesigned as a planning agent.

Flow per request:
  1. Extract structured constraints (full conversation; two-pass merge for refine).
  2. Detect catalog constraint conflicts (deterministic scan, no LLM, no retrieval).
  3. Plan intent (LLM reasoning step, no retrieval).
  4. Route:
       clarify   → ask ONE question. Never retrieve. recs=[].
       refuse    → policy refusal (legal / off-topic). Never retrieve. recs=[].
       compare   → direct catalog lookup. No embeddings.
       finish    → end_of_conversation=True.
       recommend → retrieve 30 → rule-based filter → rerank → LLM explains.
       refine    → merge new constraints → retrieve 30 → filter → rerank → LLM explains.

The LLM at step 4 (recommend/refine) ONLY explains why retrieved entries were
chosen. It never invents assessment names or URLs.
"""
import json
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from app.schemas import Message, ChatResponse, AssessmentEntry
from app.conversation.constraint_extractor import (
    extract_constraints,
    merge_constraints,
    constraints_to_query,
)
from app.conversation.planner import (
    detect_conflicts,
    plan as planner_plan,
    PlannerOutput,
    Conflict,
)
from app.conversation.prompt_builder import (
    build_recommendation_prompt,
    build_clarification_prompt,
    build_refusal_prompt,
)
from app.conversation.comparison import handle_comparison
from app.retrieval.filter import apply_domain_rules
from app.retrieval.reranker import rerank
from app.utils.validators import entity_ids_to_recommendations
from app.llm.groq_client import chat_completion
from app.utils.logger import logger
from app.config import settings

if TYPE_CHECKING:
    from app.retrieval.retriever import ConstraintAwareRetriever


class ChatEngine:
    def __init__(
        self,
        retriever: "ConstraintAwareRetriever",
        by_id: Dict[str, AssessmentEntry],
        by_name: Dict[str, AssessmentEntry],
    ):
        self.retriever = retriever
        self.by_id = by_id
        self.by_name = by_name
        self._all_entries = list(by_id.values())

    # ── Constraint extraction ───────────────────────────────────────────────────

    def _extract_constraints(
        self, messages: List[Message], intent: str = "recommend"
    ) -> Dict[str, Any]:
        """
        Two-pass extraction for refinement: base from prior turns, delta from
        the latest user message, then deterministic merge so follow-ups like
        "add personality" never drop earlier domain/language context.
        Single-pass for first recommendation turns.
        """
        if intent == "refine" and len(messages) >= 2:
            prior_msgs  = messages[:-1]
            latest_msgs = [m for m in messages[-2:] if m.role == "user"][:1]
            base  = extract_constraints(prior_msgs) if prior_msgs else {}
            delta = extract_constraints(latest_msgs) if latest_msgs else {}
            merged = merge_constraints(base, delta)
            logger.info(
                f"Refinement merge: base={list(base.keys())} "
                f"delta={list(delta.keys())} result={list(merged.keys())}"
            )
            return merged
        return extract_constraints(messages)

    # ── Retrieval pipeline ──────────────────────────────────────────────────────

    def _retrieve_filter_rerank(
        self,
        query: str,
        constraints: Dict[str, Any],
        conflict: Optional[Conflict],
        top_k_retrieve: int = 30,
        top_k_return: Optional[int] = None,
    ) -> List[AssessmentEntry]:
        candidates = self.retriever.retrieve(
            query,
            constraints=constraints,
            top_k=top_k_retrieve,
        )
        logger.info(f"Retrieved {len(candidates)} candidates")

        # Rule-based domain filter + boosts (no LLM)
        filtered = apply_domain_rules(
            candidates, constraints, self.by_id, conflict=conflict
        )

        # Metadata-aware reranker
        ranked_ids = rerank(
            filtered,
            self.by_id,
            constraints,
            top_k=top_k_return or settings.top_k_return,
        )
        return [self.by_id[eid] for eid in ranked_ids if eid in self.by_id]

    # ── LLM call ────────────────────────────────────────────────────────────────

    def _call_llm(
        self,
        prompt_msgs: List[Dict],
        max_tokens: Optional[int] = None,
    ) -> Dict:
        raw = chat_completion(
            messages=prompt_msgs,
            max_tokens=max_tokens or settings.groq_max_tokens,
            temperature=0.1,
            json_mode=True,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"LLM non-JSON: {raw[:200]}")
            return {"reply": raw, "selected_ids": [], "end_of_conversation": False}

    # ── Main entry point ────────────────────────────────────────────────────────

    def process(self, messages: List[Message]) -> ChatResponse:
        t0 = time.perf_counter()

        # ── 1. Extract constraints (full conversation) ─────────────────────────
        # Initial extraction — may be re-extracted with two-pass merge if refine.
        constraints = extract_constraints(messages)

        # ── 2. Detect conflicts (deterministic, no LLM, no retrieval) ──────────
        conflict = detect_conflicts(constraints, self._all_entries)
        if conflict:
            logger.info(f"Conflict detected: {conflict.type} — {conflict.description[:80]}")

        # ── 3. Plan intent (LLM, no retrieval) ────────────────────────────────
        plan: PlannerOutput = planner_plan(messages, constraints, conflict)
        intent = plan.intent
        logger.info(f"Intent: {intent}")

        # ── 4. Route by intent ─────────────────────────────────────────────────

        # CLARIFY — never retrieve
        if intent == "clarify":
            prompt = build_clarification_prompt(messages, constraints)
            parsed = self._call_llm(prompt, max_tokens=250)
            return ChatResponse(
                reply=parsed.get("reply", "What role are you hiring for?"),
                recommendations=[],
                end_of_conversation=False,
            )

        # REFUSE — legal / off-topic / prompt injection
        if intent == "refuse":
            prompt = build_refusal_prompt(messages, constraints, self.by_id)
            parsed = self._call_llm(prompt, max_tokens=350)
            return ChatResponse(
                reply=parsed.get(
                    "reply",
                    "I can only help with SHL assessment selection. "
                    "For legal or compliance questions please consult your legal counsel.",
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        # COMPARE — direct catalog lookup, no embeddings
        if intent == "compare":
            reply, ids = handle_comparison(
                messages, self.retriever, self.by_id, self.by_name
            )
            by_id_dict = {k: v.model_dump() for k, v in self.by_id.items()}
            recs = entity_ids_to_recommendations(ids, by_id_dict)
            return ChatResponse(
                reply=reply,
                recommendations=recs,
                end_of_conversation=False,
            )

        # FINISH
        if intent == "finish":
            return ChatResponse(
                reply=(
                    "You're welcome! If you need further assessment guidance "
                    "feel free to return. Good luck with your hiring."
                ),
                recommendations=[],
                end_of_conversation=True,
            )

        # RECOMMEND / REFINE ──────────────────────────────────────────────────
        # Re-extract with deterministic merge for refinement turns.
        if intent == "refine":
            constraints = self._extract_constraints(messages, intent="refine")
            # Re-run conflict detection with merged constraints
            conflict = detect_conflicts(constraints, self._all_entries)

        query = constraints_to_query(constraints)
        if not query:
            user_msgs = [m for m in messages if m.role == "user"]
            query = user_msgs[-1].content if user_msgs else ""

        entries = self._retrieve_filter_rerank(query, constraints, conflict)

        prompt = build_recommendation_prompt(
            messages, entries, constraints, intent, conflict=conflict
        )
        parsed = self._call_llm(prompt)

        reply        = parsed.get("reply", "")
        selected_ids = parsed.get("selected_ids", [])
        end_conv     = parsed.get("end_of_conversation", False)

        by_id_dict = {k: v.model_dump() for k, v in self.by_id.items()}
        recs = entity_ids_to_recommendations(selected_ids, by_id_dict)

        latency_ms = round((time.perf_counter() - t0) * 1000)
        logger.info(f"Response in {latency_ms}ms — {len(recs)} recommendations")

        return ChatResponse(
            reply=reply,
            recommendations=recs,
            end_of_conversation=end_conv,
        )
