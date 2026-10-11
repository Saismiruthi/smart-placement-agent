# agents/memory_agent.py
# Long-term student memory using ChromaDB + RAG-based personalization

import json
import sqlite3
from datetime import datetime
from loguru import logger
from crewai import Agent
from langchain_community.llms import Ollama

from tools.vector_store import VectorStore
from tools.db_manager import init_database, get_student_profile
from config import LLM_MODEL, OLLAMA_BASE_URL, SQLITE_PATH

# Reuse threshold from feedback agent
WEAK_SCORE_THRESHOLD = 0.50


# ── Memory document types ─────────────────────────────────────────────────────
MEMORY_TYPE_EPISODIC    = "episodic"     # What happened in a session
MEMORY_TYPE_SEMANTIC    = "semantic"     # Generalized facts about the student
MEMORY_TYPE_PROCEDURAL  = "procedural"  # What helped the student improve


class MemoryAgent:
    """
    Manages long-term student memory using ChromaDB.

    Key operations:
        consolidate_memories()   — read SQLite sessions, write to ChromaDB
        retrieve_context()       — semantic search for relevant memories
        get_personalized_brief() — RAG: retrieve + LLM summarize for Planner
        forget_student()         — GDPR-style full memory reset
    """

    def __init__(self):
        logger.info("Initializing Memory Agent...")
        init_database()

        self.vector_store = VectorStore()

        self.llm = Ollama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2
        )

        self.agent = Agent(
            role="Student Memory Manager",
            goal=(
                "Maintain accurate long-term memory of each student's "
                "performance history, weaknesses, and progress so that "
                "every future session is fully personalized."
            ),
            backstory=(
                "You are a meticulous academic advisor who keeps detailed "
                "notes on every student. You never forget a weakness and "
                "always know exactly where each student needs help next."
            ),
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        logger.info("Memory Agent ready.")

    # ── Consolidation ─────────────────────────────────────────────────────────

    def consolidate_memories(self, student_id: str) -> dict:
        """
        Read all SQLite session data for a student and convert it
        into structured memory documents stored in ChromaDB.

        This should be called:
        - After every session ends
        - At the start of a new session (to refresh context)

        Returns:
            Summary of memories written
        """
        sessions = self._load_sessions(student_id)
        profile  = get_student_profile(student_id)

        if not sessions:
            return {
                "student_id":       student_id,
                "memories_written": 0,
                "message":          "No sessions to consolidate."
            }

        docs            = []
        episodic_count  = 0
        semantic_count  = 0
        procedural_count= 0
        _counter        = 0   # unique counter to prevent duplicate IDs
        # ── 1. Episodic memories (one per session) ────────────────────────────
        for i, session in enumerate(sessions):
            stype   = session["session_type"]
            score   = session["score"]
            details = session["details"]
            ts      = session["created_at"][:10]

            if stype == "coding_practice":
                text = (
                    f"On {ts}, student completed a coding session. "
                    f"Average score: {score:.0%}. "
                    f"Final difficulty reached: {details.get('final_difficulty', 'easy')}. "
                    f"Performance band: {details.get('performance_band', 'unknown')}. "
                    f"Problems attempted: {details.get('problems_attempted', 0)}."
                )

            elif stype == "mock_interview":
                hr_s   = details.get("hr_score", 0)
                tech_s = details.get("technical_score", 0)
                passed = "passed" if details.get("passed") else "did not pass"
                role   = details.get("target_role", "unknown role")
                text = (
                    f"On {ts}, student completed a mock interview for {role}. "
                    f"HR score: {hr_s:.0%}, Technical score: {tech_s:.0%}. "
                    f"Overall: {score:.0%}. Student {passed}."
                )

                # Add per-topic episodic memories from conversation
                for exchange in details.get("conversation", []):
                    topic     = exchange.get("topic", "General")
                    ex_score  = exchange.get("score", 0)
                    question  = exchange.get("question", "")
                    level     = "well" if ex_score >= 0.70 else "poorly"
                    topic_text = (
                        f"Student answered a {topic} question "
                        f"'{question[:60]}' {level} on {ts} "
                        f"(score: {ex_score:.0%})."
                    )
                    _counter += 1
                    docs.append({
                        "id": f"{student_id}_ep_topic_{ts}_{topic}_{_counter}",
                        "metadata": {
                            "student_id":   student_id,
                            "memory_type":  MEMORY_TYPE_EPISODIC,
                            "session_type": stype,
                            "topic":        topic,
                            "score":        ex_score,
                            "date":         ts
                        }
                    })
                    episodic_count += 1
            else:
                text = (
                    f"On {ts}, student completed a {stype} session "
                    f"with score {score:.0%}."
                )

            docs.append({
                "id": f"{student_id}_ep_{stype}_{i}",
                "text": text,
                "metadata": {
                    "student_id":   student_id,
                    "memory_type":  MEMORY_TYPE_EPISODIC,
                    "session_type": stype,
                    "score":        score,
                    "date":         ts
                }
            })
            episodic_count += 1

        # ── 2. Semantic memories (generalized weaknesses/strengths) ───────────
        topic_scores    = self._aggregate_topic_scores(sessions)
        weak_topics     = []
        strong_topics   = []

        for topic, scores in topic_scores.items():
            avg = sum(scores) / len(scores)
            if avg < WEAK_SCORE_THRESHOLD:
                weak_topics.append((topic, avg))
            elif avg >= 0.75:
                strong_topics.append((topic, avg))

        if weak_topics:
            weak_str = "; ".join(
                f"{t} (avg {s:.0%})" for t, s in sorted(weak_topics, key=lambda x: x[1])
            )
            docs.append({
                "id": f"{student_id}_sem_weaknesses",
                "text": (
                    f"Student {profile.get('name', student_id)} has persistent "
                    f"weaknesses in: {weak_str}. "
                    f"These topics need focused practice."
                ),
                "metadata": {
                    "student_id":  student_id,
                    "memory_type": MEMORY_TYPE_SEMANTIC,
                    "category":    "weaknesses",
                    "topics":      json.dumps([t for t, _ in weak_topics])
                }
            })
            semantic_count += 1

        if strong_topics:
            strong_str = "; ".join(
                f"{t} (avg {s:.0%})" for t, s in strong_topics
            )
            docs.append({
                "id": f"{student_id}_sem_strengths",
                "text": (
                    f"Student {profile.get('name', student_id)} performs "
                    f"strongly in: {strong_str}."
                ),
                "metadata": {
                    "student_id":  student_id,
                    "memory_type": MEMORY_TYPE_SEMANTIC,
                    "category":    "strengths",
                    "topics":      json.dumps([t for t, _ in strong_topics])
                }
            })
            semantic_count += 1

        # Overall progress semantic memory
        all_scores = [s["score"] for s in sessions]
        if len(all_scores) >= 2:
            trend = "improving" if all_scores[-1] > all_scores[0] else "declining"
            docs.append({
                "id": f"{student_id}_sem_trend",
                "text": (
                    f"Student's overall performance is {trend}. "
                    f"First session score: {all_scores[0]:.0%}. "
                    f"Latest session score: {all_scores[-1]:.0%}. "
                    f"Total sessions completed: {len(sessions)}."
                ),
                "metadata": {
                    "student_id":  student_id,
                    "memory_type": MEMORY_TYPE_SEMANTIC,
                    "category":    "trend",
                    "trend":       trend
                }
            })
            semantic_count += 1

        # ── 3. Procedural memories (what strategies worked) ───────────────────
        coding_sessions = [s for s in sessions if s["session_type"] == "coding_practice"]
        if len(coding_sessions) >= 2:
            scores_over_time = [s["score"] for s in coding_sessions]
            best_idx         = scores_over_time.index(max(scores_over_time))
            best_session     = coding_sessions[best_idx]
            best_difficulty  = best_session["details"].get("final_difficulty", "easy")

            docs.append({
                "id": f"{student_id}_proc_coding_best",
                "text": (
                    f"Student performed best in coding when reaching "
                    f"{best_difficulty} difficulty problems. "
                    f"Best coding session score: {max(scores_over_time):.0%}."
                ),
                "metadata": {
                    "student_id":  student_id,
                    "memory_type": MEMORY_TYPE_PROCEDURAL,
                    "category":    "coding_strategy"
                }
            })
            procedural_count += 1

        # ── Deduplicate by ID before batch write ──────────────────────────────
        seen_ids = set()
        unique_docs = []
        for doc in docs:
            if doc["id"] not in seen_ids:
                seen_ids.add(doc["id"])
                unique_docs.append(doc)

        written = self.vector_store.add_documents_batch("memory", unique_docs)

        logger.info(
            f"Memory consolidated for {student_id}: "
            f"{episodic_count} episodic, {semantic_count} semantic, "
            f"{procedural_count} procedural"
        )

        return {
            "student_id":        student_id,
            "memories_written":  written,
            "episodic_count":    episodic_count,
            "semantic_count":    semantic_count,
            "procedural_count":  procedural_count,
            "total_in_store":    self.vector_store.get_collection_stats()["memory"]
        }

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve_context(
        self,
        student_id:  str,
        query:       str,
        n_results:   int  = 5,
        memory_type: str  = None
    ) -> list[dict]:
        """
        Retrieve the most relevant memories for a student
        using semantic similarity search.

        Args:
            student_id  : The student's unique ID
            query       : Natural language query
                          e.g. "what topics is this student weak in?"
            n_results   : Max memories to return
            memory_type : Optional filter — 'episodic', 'semantic', 'procedural'

        Returns:
            List of relevant memory dicts sorted by relevance
        """
        where = {"student_id": student_id}
        if memory_type:
            where["memory_type"] = memory_type

        results = self.vector_store.query(
            collection_name = "memory",
            query_text      = query,
            n_results       = n_results,
            where           = where
        )

        logger.debug(
            f"Retrieved {len(results)} memories for '{query}' "
            f"(student: {student_id})"
        )
        return results

    def get_weak_topics(self, student_id: str) -> list[str]:
        """
        Quick lookup: return the student's known weak topics
        from semantic memory.

        Returns:
            List of topic strings
        """
        results = self.retrieve_context(
            student_id  = student_id,
            query       = "student weaknesses and poor performance topics",
            n_results   = 3,
            memory_type = MEMORY_TYPE_SEMANTIC
        )

        weak_topics = []
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("category") == "weaknesses":
                try:
                    topics = json.loads(meta.get("topics", "[]"))
                    weak_topics.extend(topics)
                except (json.JSONDecodeError, TypeError):
                    pass

        return list(dict.fromkeys(weak_topics))   # deduplicated, order preserved

    def get_strong_topics(self, student_id: str) -> list[str]:
        """Return the student's known strong topics from semantic memory."""
        results = self.retrieve_context(
            student_id  = student_id,
            query       = "student strengths and high performance topics",
            n_results   = 3,
            memory_type = MEMORY_TYPE_SEMANTIC
        )

        strong_topics = []
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("category") == "strengths":
                try:
                    topics = json.loads(meta.get("topics", "[]"))
                    strong_topics.extend(topics)
                except (json.JSONDecodeError, TypeError):
                    pass

        return list(dict.fromkeys(strong_topics))

    # ── RAG Personalized Brief ────────────────────────────────────────────────

    def get_personalized_brief(self, student_id: str) -> dict:
        """
        RAG pipeline: retrieve relevant memories → feed to LLM →
        get a concise personalized session brief.

        Used by the Planner Agent at the start of every session
        to understand the student before making decisions.

        Returns:
            Dict with memory context and LLM-generated brief
        """
        # Retrieve most relevant memories
        weakness_mems = self.retrieve_context(
            student_id = student_id,
            query      = "student weaknesses problems struggles difficulty",
            n_results  = 4
        )
        trend_mems = self.retrieve_context(
            student_id = student_id,
            query      = "student progress improvement trend performance",
            n_results  = 3
        )

        # Build context string for LLM
        all_mems = weakness_mems + trend_mems
        if not all_mems:
            return {
                "student_id": student_id,
                "brief":      "No memory available. This appears to be a new student.",
                "weak_topics":   [],
                "strong_topics": [],
                "memories_used": 0
            }

        context_parts = []
        for mem in all_mems:
            context_parts.append(f"- {mem['text']}")

        context_str = "\n".join(context_parts)

        prompt = f"""You are a placement mentor reviewing your notes before a student session.

Your notes about this student:
{context_str}

Write a concise 3-sentence briefing that covers:
1. Where the student currently stands overall
2. Their top 2 weak areas that need focus today
3. One encouraging observation about their progress

Write only the 3 sentences, no headers:"""

        try:
            brief = self.llm.invoke(prompt).strip()
        except Exception as e:
            logger.warning(f"Brief generation failed: {e}")
            brief = f"Retrieved {len(all_mems)} memories. Review weak areas before session."

        return {
            "student_id":    student_id,
            "brief":         brief,
            "weak_topics":   self.get_weak_topics(student_id),
            "strong_topics": self.get_strong_topics(student_id),
            "memories_used": len(all_mems),
            "raw_memories":  [m["text"] for m in all_mems[:5]]
        }

    # ── Save Single Memory ────────────────────────────────────────────────────

    def save_memory(
        self,
        student_id:   str,
        text:         str,
        memory_type:  str  = MEMORY_TYPE_EPISODIC,
        metadata:     dict = None
    ) -> bool:
        """
        Save a single memory document directly.
        Useful for agents to log important observations mid-session.

        Example:
            memory_agent.save_memory(
                student_id  = "arjun_001",
                text        = "Student asked for hint 3 times on recursion problem",
                memory_type = "episodic"
            )
        """
        doc_id = (
            f"{student_id}_{memory_type}_"
            f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        )
        meta = metadata or {}
        meta.update({
            "student_id":  student_id,
            "memory_type": memory_type
        })

        return self.vector_store.add_document(
            collection_name = "memory",
            doc_id          = doc_id,
            text            = text,
            metadata        = meta
        )

    # ── Forget (Reset) ────────────────────────────────────────────────────────

    def forget_student(self, student_id: str) -> dict:
        """
        Delete all ChromaDB memories for a student.
        SQLite session data is kept (for audit purposes).

        Returns:
            Count of memories deleted
        """
        deleted = self.vector_store.delete_student_memories(student_id)
        logger.info(f"Forgot all ChromaDB memories for {student_id}")
        return {
            "student_id":      student_id,
            "memories_deleted": deleted,
            "message":         "ChromaDB memories cleared. SQLite history retained."
        }

    # ── Memory Stats ──────────────────────────────────────────────────────────

    def get_memory_stats(self, student_id: str) -> dict:
        """Return a summary of stored memory for a student."""
        all_mems   = self.retrieve_context(
            student_id = student_id,
            query      = "student performance history",
            n_results  = 50
        )
        type_counts = {}
        for mem in all_mems:
            mtype = mem["metadata"].get("memory_type", "unknown")
            type_counts[mtype] = type_counts.get(mtype, 0) + 1

        return {
            "student_id":      student_id,
            "total_memories":  len(all_mems),
            "by_type":         type_counts,
            "collection_stats": self.vector_store.get_collection_stats()
        }

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _load_sessions(self, student_id: str) -> list[dict]:
        """Load all sessions for a student from SQLite."""
        conn = sqlite3.connect(str(SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT session_type, score, details, created_at
            FROM sessions
            WHERE student_id = ?
            ORDER BY created_at ASC
        """, (student_id,)).fetchall()
        conn.close()

        sessions = []
        for row in rows:
            try:
                details = json.loads(row["details"]) if row["details"] else {}
            except json.JSONDecodeError:
                details = {}
            sessions.append({
                "session_type": row["session_type"],
                "score":        float(row["score"]),
                "details":      details,
                "created_at":   row["created_at"]
            })
        return sessions

    def _aggregate_topic_scores(self, sessions: list[dict]) -> dict:
        """Aggregate per-topic scores across all interview sessions."""
        from collections import defaultdict
        topic_scores = defaultdict(list)

        for session in sessions:
            if session["session_type"] != "mock_interview":
                continue
            for exchange in session["details"].get("conversation", []):
                topic = exchange.get("topic", "")
                score = exchange.get("score", 0)
                if topic:
                    topic_scores[topic].append(score)

        return dict(topic_scores)