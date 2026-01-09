"""
Central Memory Manager - MemGPT/Hindsight/O-Mem unified orchestrator.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import validate_session_id

from .belief_network import BeliefNetwork
from .experience_network import ExperienceNetwork
from .fact_network import FactNetwork
from .memory_operations import MemoryOperator
from .memory_scheduler import MemScheduler
from .observation_network import ObservationNetwork
from .persona_memory import PersonaMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Orchestrates all memory networks and operations.
    Inspired by MemGPT's OS-like memory management.
    """

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        # Validate session_id to prevent session forgery
        self.session_id = validate_session_id(session_id)

        # Initialize networks (Hindsight architecture)
        # Use validated session_id to prevent forgery attacks
        self.facts = FactNetwork(db, self.session_id)
        self.experiences = ExperienceNetwork(db, self.session_id)
        self.observations = ObservationNetwork(db, self.session_id)
        self.beliefs = BeliefNetwork(db, self.session_id)

        # O-Mem persona layer
        self.persona = PersonaMemory(db, self.session_id)

        # MemOS scheduling
        self.scheduler = MemScheduler(db, self.session_id)

        # Memory-R1 operations
        self.operator = MemoryOperator(db, self.session_id)

    # ==========================================
    # CONTEXT BUILDING (For each chat request)
    # ==========================================

    async def build_context_for_query(self, query: str) -> dict[str, Any]:
        """
        Build rich context using all memory networks.
        Implements O-Mem's hierarchical retrieval.
        """
        context: dict[str, Any] = {}

        try:
            # 1. Persona Memory (always included - O-Mem style)
            context["persona"] = await self.persona.get_active_profile()
        except Exception as e:
            logger.error(f"Error getting persona: {e}")
            context["persona"] = {}

        try:
            # 2. Relevant Facts (semantic search)
            context["relevant_facts"] = await self.facts.search(query, limit=10)
        except Exception as e:
            logger.error(f"Error searching facts: {e}")
            context["relevant_facts"] = []

        try:
            # 3. Recent Experiences (if relevant)
            context["recent_experiences"] = await self.experiences.get_recent(limit=5)
        except Exception as e:
            logger.error(f"Error getting experiences: {e}")
            context["recent_experiences"] = []

        try:
            # 4. Entity Context (observation network)
            entities = await self.observations.extract_entities(query)
            if entities:
                context["entity_context"] = await self.observations.get_entity_context(entities)
            else:
                context["entity_context"] = []
        except Exception as e:
            logger.error(f"Error getting entity context: {e}")
            context["entity_context"] = []

        try:
            # 5. Active Beliefs (high confidence)
            context["beliefs"] = await self.beliefs.get_active(min_confidence=0.7)
        except Exception as e:
            logger.error(f"Error getting beliefs: {e}")
            context["beliefs"] = []

        try:
            # 6. Topic Context (O-Mem working memory)
            topic = await self.persona.identify_topic(query)
            if topic and topic != "general":
                context["topic_history"] = await self.persona.get_topic_context(topic)
                context["current_topic"] = topic
        except Exception as e:
            logger.error(f"Error getting topic context: {e}")

        try:
            # 7. Schedule next-scene prediction (MemOS)
            await self.scheduler.predict_and_preload(query)
        except Exception as e:
            logger.error(f"Error in scheduler prediction: {e}")

        return context

    async def format_context_for_prompt(self, context: dict[str, Any]) -> str:
        """Format context into system prompt section.

        Applies strict length limits to prevent 413 errors from Claude API.
        Maximum prompt section size: ~4000 chars.
        """
        sections = []
        total_length = 0
        max_section_length = 2500  # Max chars per section
        max_total_length = 15000   # Max total chars - generous limit

        def truncate(text: str, max_len: int = 200) -> str:
            """Truncate text to max_len chars."""
            if not text:
                return ""
            text = str(text)
            if len(text) <= max_len:
                return text
            return text[:max_len - 3] + "..."

        # Persona (O-Mem style)
        if context.get("persona"):
            p = context["persona"]
            attrs = p.get("attributes", [])
            events = p.get("events", [])

            if p.get("summary") or attrs:
                persona_section = "## USER PROFILE\n"
                if p.get("summary"):
                    persona_section += f"{truncate(p['summary'], 300)}\n\n"

                if attrs:
                    persona_section += "**Key Attributes:**\n"
                    for a in attrs[:10]:  # More attributes
                        content = a.get('content', str(a)) if isinstance(a, dict) else str(a)
                        persona_section += f"- {truncate(content, 150)}\n"

                if events:
                    persona_section += "\n**Important Events:**\n"
                    for e in events[:7]:  # More events
                        content = e.get('content', str(e)) if isinstance(e, dict) else str(e)
                        persona_section += f"- {truncate(content, 150)}\n"

                if len(persona_section) <= max_section_length:
                    sections.append(persona_section)
                    total_length += len(persona_section)

        # Relevant Facts (Hindsight fact network) - only if room
        if context.get("relevant_facts") and total_length < max_total_length:
            facts = context["relevant_facts"][:10]  # More facts
            if facts:
                facts_str = "\n".join(
                    f"- {truncate(f['content'], 200)} ({f.get('confidence', 1.0):.0%})"
                    for f in facts
                )
                facts_section = f"## RELEVANT KNOWLEDGE\n{facts_str}"
                if len(facts_section) <= max_section_length:
                    sections.append(facts_section)
                    total_length += len(facts_section)

        # Entity Context (observation network) - only if room
        if context.get("entity_context") and total_length < max_total_length:
            entities = context["entity_context"][:7]  # More entities
            if entities:
                ent_lines = []
                for e in entities:
                    summary = truncate(e.get("summary") or "No summary", 120)
                    ent_lines.append(f"- **{truncate(e['name'], 50)}**: {summary}")
                ent_section = "## ENTITY CONTEXT\n" + "\n".join(ent_lines)
                if len(ent_section) <= max_section_length:
                    sections.append(ent_section)
                    total_length += len(ent_section)

        # Beliefs (high confidence) - only if room
        if context.get("beliefs") and total_length < max_total_length:
            beliefs = context["beliefs"][:7]  # More beliefs
            if beliefs:
                bel_str = "\n".join(
                    f"- {truncate(b['belief'], 180)} ({b.get('confidence', 0.5):.0%})"
                    for b in beliefs
                )
                bel_section = f"## MY UNDERSTANDING\n{bel_str}"
                if len(bel_section) <= max_section_length:
                    sections.append(bel_section)
                    total_length += len(bel_section)

        # Recent Experiences - only if room
        if context.get("recent_experiences") and total_length < max_total_length:
            exp = context["recent_experiences"][:5]  # More experiences
            if exp:
                exp_str = "\n".join(f"- {truncate(e['description'], 150)}" for e in exp)
                exp_section = f"## RECENT INTERACTIONS\n{exp_str}"
                if len(exp_section) <= max_section_length:
                    sections.append(exp_section)
                    total_length += len(exp_section)

        # Topic context - skip if already at limit
        if context.get("topic_history") and total_length < max_total_length - 300:
            th = context["topic_history"]
            if th.get("summary"):
                topic_section = f"## TOPIC: {truncate(th.get('topic', 'Unknown'), 30)}\n"
                topic_section += f"{truncate(th['summary'], 200)}\n"
                if th.get("key_points"):
                    topic_section += "Key points:\n"
                    for kp in th["key_points"][:2]:
                        topic_section += f"- {truncate(kp, 80)}\n"
                if len(topic_section) <= max_section_length:
                    sections.append(topic_section)

        result = "\n\n".join(sections) if sections else ""

        # Final safety truncation
        if len(result) > max_total_length:
            result = result[:max_total_length - 50] + "\n\n[Context truncated]"

        return result

    # ==========================================
    # MEMORY PROCESSING (After each interaction)
    # ==========================================

    async def process_interaction(
        self,
        user_message: str,
        assistant_response: str,
        message_id: UUID | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Process an interaction and update all memory networks.
        Implements Memory-R1 style operations.
        """
        try:
            # 1. Decide what operations to perform (Memory-R1)
            operations = await self.operator.decide_operations(
                user_message=user_message,
                assistant_response=assistant_response,
                current_context=context,
            )

            # 2. Execute operations
            for op in operations:
                await self._execute_operation(op, user_message, assistant_response)

            # 3. Update persona (O-Mem)
            await self.persona.update_from_interaction(user_message, assistant_response)

            # 4. Update topic index (O-Mem working memory)
            topic = await self.persona.identify_topic(user_message)
            if topic and topic != "general":
                await self.persona.index_message_to_topic(topic, user_message, message_id)

            # 5. Update keyword index (O-Mem episodic memory)
            keywords = await self.observations.extract_keywords(user_message + " " + assistant_response)
            await self.persona.index_message_to_keywords(keywords, user_message, message_id)

            # 6. Update heat scores (MemOS scheduling)
            await self.scheduler.update_heat_scores(operations)

            await self.db.commit()

        except Exception as e:
            logger.error(f"Error processing interaction: {e}")
            await self.db.rollback()

    async def _execute_operation(
        self,
        operation: dict[str, Any],
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Execute a single memory operation."""
        op_type = operation.get("operation")

        try:
            if op_type == "ADD":
                await self._add_memory(operation, user_message, assistant_response)
            elif op_type == "UPDATE":
                await self._update_memory(operation)
            elif op_type == "DELETE":
                await self._delete_memory(operation)
            # NOOP does nothing

            # Log operation
            await self.operator.log_operation(operation, success=True)

        except Exception as e:
            logger.error(f"Error executing operation {op_type}: {e}")
            await self.operator.log_operation(operation, success=False, error=str(e))

    async def _add_memory(
        self,
        operation: dict[str, Any],
        user_msg: str,
        asst_msg: str,
    ) -> None:
        """Add new memory based on operation decision."""
        memory_type = operation.get("memory_type", "fact")
        content = operation.get("content")

        if not content:
            return

        if memory_type == "fact":
            await self.facts.add(
                content=content,
                fact_type=operation.get("fact_type", "fact"),
                confidence=operation.get("confidence", 0.8),
                source="chat",
            )
        elif memory_type == "belief":
            await self.beliefs.form(
                belief=content,
                belief_type=operation.get("belief_type", "inference"),
                initial_confidence=operation.get("confidence", 0.6),
            )
        elif memory_type == "experience":
            await self.experiences.add(
                description=content,
                experience_type="conversation",
                outcome="success",
            )

    async def _update_memory(self, operation: dict[str, Any]) -> None:
        """Update existing memory."""
        memory_type = operation.get("memory_type")
        memory_id = operation.get("memory_id")

        if not memory_id:
            return

        try:
            memory_uuid = UUID(memory_id)
        except ValueError:
            return

        if memory_type == "fact":
            await self.facts.update(
                fact_id=memory_uuid,
                new_content=operation.get("new_content"),
                new_confidence=operation.get("new_confidence"),
            )
        elif memory_type == "belief":
            if operation.get("reinforce"):
                await self.beliefs.reinforce(memory_uuid)
            elif operation.get("challenge"):
                await self.beliefs.challenge(memory_uuid)

    async def _delete_memory(self, operation: dict[str, Any]) -> None:
        """Invalidate memory (soft delete)."""
        memory_type = operation.get("memory_type")
        memory_id = operation.get("memory_id")

        if not memory_id:
            return

        try:
            memory_uuid = UUID(memory_id)
        except ValueError:
            return

        if memory_type == "fact":
            await self.facts.invalidate(memory_uuid)
        elif memory_type == "belief":
            await self.beliefs.reject(memory_uuid)

    # ==========================================
    # CONSOLIDATION (Background job)
    # ==========================================

    async def consolidate(self) -> dict[str, Any]:
        """
        Periodic memory consolidation.
        Implements MemOS lifecycle management.
        """
        logger.info(f"Starting memory consolidation for session {self.session_id}")
        stats: dict[str, Any] = {}

        try:
            # 1. Extract facts from recent conversations
            facts = await self.facts.extract_from_recent_chats()
            stats["facts_extracted"] = len(facts)
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            stats["facts_extracted"] = 0

        try:
            # 2. Update entity observations
            updated = await self.observations.update_entity_summaries()
            stats["entities_updated"] = updated
        except Exception as e:
            logger.error(f"Error updating entities: {e}")
            stats["entities_updated"] = 0

        try:
            # 3. Evolve beliefs based on new evidence
            evolved = await self.beliefs.evolve_from_evidence()
            stats["beliefs_evolved"] = evolved
        except Exception as e:
            logger.error(f"Error evolving beliefs: {e}")
            stats["beliefs_evolved"] = 0

        try:
            # 4. Learn procedures from experiences
            procedures = await self.experiences.extract_procedures()
            stats["procedures_learned"] = len(procedures)
        except Exception as e:
            logger.error(f"Error extracting procedures: {e}")
            stats["procedures_learned"] = 0

        try:
            # 5. Apply memory decay (MemOS/Mem0)
            decay_stats = await self.scheduler.apply_decay()
            stats["decay_applied"] = decay_stats
        except Exception as e:
            logger.error(f"Error applying decay: {e}")
            stats["decay_applied"] = {}

        try:
            # 6. Create A-MEM links
            await self._create_cross_links()
            stats["links_created"] = True
        except Exception as e:
            logger.error(f"Error creating links: {e}")
            stats["links_created"] = False

        try:
            # 7. Update meta-knowledge
            await self._update_meta_knowledge()
            stats["meta_updated"] = True
        except Exception as e:
            logger.error(f"Error updating meta: {e}")
            stats["meta_updated"] = False

        await self.db.commit()
        logger.info(f"Memory consolidation complete: {stats}")
        return stats

    async def _create_cross_links(self) -> None:
        """Create A-MEM style links between memories."""
        # Get recent unlinked facts
        recent_facts = await self.facts.get_unlinked(limit=20)

        for fact in recent_facts:
            # Find similar facts
            similar = await self.facts.search(fact.content, limit=5)
            for s in similar:
                if s["id"] != str(fact.id) and s.get("score", 0) > 0.75:
                    await self.facts.create_link(
                        source_id=fact.id,
                        target_id=UUID(s["id"]),
                        link_type="related",
                        strength=s["score"],
                    )

    async def _update_meta_knowledge(self) -> None:
        """Update self-knowledge about what we know."""
        from sqlalchemy import select

        from src.db.models.memory import MemoryMeta

        domains = ["work", "personal", "preferences", "habits", "goals"]

        for domain in domains:
            facts_count = await self.facts.count_by_category(domain)
            beliefs_count = await self.beliefs.count_by_domain(domain)

            # Calculate confidence based on coverage
            confidence = min(1.0, (facts_count + beliefs_count) / 10)

            # Upsert meta record
            result = await self.db.execute(
                select(MemoryMeta).where(
                    MemoryMeta.session_id == self.session_id,
                    MemoryMeta.domain == domain,
                )
            )
            meta = result.scalar_one_or_none()

            if meta:
                meta.facts_count = facts_count
                meta.beliefs_count = beliefs_count
                meta.confidence_score = confidence
                meta.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                meta = MemoryMeta(
                    id=uuid4(),
                    session_id=self.session_id,
                    domain=domain,
                    facts_count=facts_count,
                    beliefs_count=beliefs_count,
                    confidence_score=confidence,
                )
                self.db.add(meta)

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    async def get_memory_stats(self) -> dict[str, Any]:
        """Get overall memory statistics."""
        from sqlalchemy import func, select

        from src.db.models.memory import (
            MemoryBelief,
            MemoryEntity,
            MemoryExperience,
            MemoryFact,
            MemoryTopic,
        )

        stats = {}

        # Count facts
        result = await self.db.execute(
            select(func.count(MemoryFact.id)).where(
                MemoryFact.session_id == self.session_id
            )
        )
        stats["facts"] = result.scalar() or 0

        # Count experiences
        result = await self.db.execute(
            select(func.count(MemoryExperience.id)).where(
                MemoryExperience.session_id == self.session_id
            )
        )
        stats["experiences"] = result.scalar() or 0

        # Count entities
        result = await self.db.execute(
            select(func.count(MemoryEntity.id)).where(
                MemoryEntity.session_id == self.session_id
            )
        )
        stats["entities"] = result.scalar() or 0

        # Count active beliefs
        result = await self.db.execute(
            select(func.count(MemoryBelief.id)).where(
                MemoryBelief.session_id == self.session_id,
                MemoryBelief.status == "active",
            )
        )
        stats["active_beliefs"] = result.scalar() or 0

        # Count topics
        result = await self.db.execute(
            select(func.count(MemoryTopic.id)).where(
                MemoryTopic.session_id == self.session_id
            )
        )
        stats["topics"] = result.scalar() or 0

        # Scheduling stats
        stats["scheduling"] = await self.scheduler.get_scheduling_stats()

        return stats

    async def clear_session(self) -> None:
        """Clear all memory for current session."""
        from sqlalchemy import delete

        from src.db.models.memory import (
            MemoryBelief,
            MemoryCube,
            MemoryEntity,
            MemoryEpisode,
            MemoryExperience,
            MemoryFact,
            MemoryKeywordIndex,
            MemoryLink,
            MemoryMeta,
            MemoryOperation,
            MemoryProcedure,
            MemoryRelationship,
            MemoryTopic,
        )

        tables = [
            MemoryLink, MemoryRelationship, MemoryCube,
            MemoryOperation, MemoryEpisode, MemoryProcedure,
            MemoryMeta, MemoryKeywordIndex, MemoryTopic,
            MemoryBelief, MemoryEntity, MemoryExperience, MemoryFact
        ]

        for table in tables:
            await self.db.execute(
                delete(table).where(table.session_id == self.session_id)
            )

        await self.db.commit()
        logger.info(f"Cleared all memory for session {self.session_id}")
