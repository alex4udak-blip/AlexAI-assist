"""
Belief Network - Evolving opinions and inferences.
Implements Hindsight's Belief Network with confidence evolution.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.memory import MemoryBelief, MemoryFact

logger = logging.getLogger(__name__)


class BeliefNetwork:
    """
    Manages beliefs - subjective opinions that evolve with evidence.
    Features:
    - Confidence tracking and evolution
    - Evidence-based reinforcement/challenge
    - Belief supersession
    - History tracking
    """

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        self.session_id = session_id

    async def form(
        self,
        belief: str,
        belief_type: str = "inference",
        initial_confidence: float = 0.5,
        supporting_facts: list[UUID] | None = None,
    ) -> MemoryBelief:
        """
        Form a new belief.

        Args:
            belief: The belief content
            belief_type: Type (preference, opinion, inference, prediction)
            initial_confidence: Starting confidence (0-1)
            supporting_facts: Initial supporting evidence

        Returns:
            Created MemoryBelief
        """
        # Check for similar existing beliefs
        existing = await self._find_similar(belief)
        if existing:
            # Reinforce existing belief
            await self.reinforce(existing.id, supporting_facts)
            return existing

        new_belief = MemoryBelief(
            id=uuid4(),
            session_id=self.session_id,
            belief=belief,
            belief_type=belief_type,
            confidence=initial_confidence,
            confidence_history=[{
                "timestamp": datetime.utcnow().isoformat(),
                "value": initial_confidence,
                "reason": "initial formation",
            }],
            supporting_facts=supporting_facts or [],
            formed_at=datetime.utcnow(),
            status="active",
        )

        self.db.add(new_belief)
        logger.info(f"Formed belief: {belief[:50]}... (confidence={initial_confidence})")
        return new_belief

    async def _find_similar(self, belief: str) -> MemoryBelief | None:
        """Find similar existing active belief."""
        # Simple substring matching for now
        # Could be enhanced with semantic similarity
        result = await self.db.execute(
            select(MemoryBelief).where(
                and_(
                    MemoryBelief.session_id == self.session_id,
                    MemoryBelief.status == "active",
                    MemoryBelief.belief.ilike(f"%{belief[:50]}%"),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active(
        self,
        min_confidence: float = 0.0,
        belief_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get active beliefs.

        Args:
            min_confidence: Minimum confidence threshold
            belief_types: Filter by types
            limit: Maximum results

        Returns:
            List of beliefs
        """
        filters = [
            MemoryBelief.session_id == self.session_id,
            MemoryBelief.status == "active",
            MemoryBelief.confidence >= min_confidence,
        ]

        if belief_types:
            filters.append(MemoryBelief.belief_type.in_(belief_types))

        result = await self.db.execute(
            select(MemoryBelief)
            .where(and_(*filters))
            .order_by(MemoryBelief.confidence.desc())
            .limit(limit)
        )

        beliefs = []
        for b in result.scalars().all():
            beliefs.append({
                "id": str(b.id),
                "belief": b.belief,
                "belief_type": b.belief_type,
                "confidence": b.confidence,
                "times_reinforced": b.times_reinforced,
                "times_challenged": b.times_challenged,
                "formed_at": b.formed_at.isoformat() if b.formed_at else None,
                "last_reinforced": b.last_reinforced.isoformat() if b.last_reinforced else None,
            })

        return beliefs

    async def get_by_id(self, belief_id: UUID) -> MemoryBelief | None:
        """Get belief by ID."""
        result = await self.db.execute(
            select(MemoryBelief).where(MemoryBelief.id == belief_id)
        )
        return result.scalar_one_or_none()

    async def reinforce(
        self,
        belief_id: UUID,
        new_evidence: list[UUID] | None = None,
        reason: str = "confirmed by interaction",
    ) -> MemoryBelief | None:
        """
        Reinforce a belief with new evidence.
        Increases confidence.
        """
        belief = await self.get_by_id(belief_id)
        if not belief:
            return None

        # Increase confidence (with diminishing returns)
        old_confidence = belief.confidence
        new_confidence = min(0.99, old_confidence + (1 - old_confidence) * 0.2)

        belief.confidence = new_confidence
        belief.times_reinforced += 1
        belief.last_reinforced = datetime.utcnow()

        # Add to history
        history = belief.confidence_history or []
        history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "value": new_confidence,
            "reason": reason,
        })
        belief.confidence_history = history[-20:]  # Keep last 20 entries

        # Add new evidence
        if new_evidence:
            current_evidence = belief.supporting_facts or []
            belief.supporting_facts = list(set(current_evidence + new_evidence))

        belief.updated_at = datetime.utcnow()

        logger.info(
            f"Reinforced belief: {belief.belief[:50]}... "
            f"({old_confidence:.2f} -> {new_confidence:.2f})"
        )
        return belief

    async def challenge(
        self,
        belief_id: UUID,
        contradicting_evidence: list[UUID] | None = None,
        reason: str = "contradicted by evidence",
    ) -> MemoryBelief | None:
        """
        Challenge a belief with contradicting evidence.
        Decreases confidence.
        """
        belief = await self.get_by_id(belief_id)
        if not belief:
            return None

        # Decrease confidence
        old_confidence = belief.confidence
        new_confidence = max(0.01, old_confidence * 0.7)

        belief.confidence = new_confidence
        belief.times_challenged += 1
        belief.last_challenged = datetime.utcnow()

        # Add to history
        history = belief.confidence_history or []
        history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "value": new_confidence,
            "reason": reason,
        })
        belief.confidence_history = history[-20:]

        # Add contradicting evidence
        if contradicting_evidence:
            current = belief.contradicting_facts or []
            belief.contradicting_facts = list(set(current + contradicting_evidence))

        # If confidence drops too low, reject the belief
        if new_confidence < 0.1:
            belief.status = "rejected"
            logger.info(f"Rejected belief due to low confidence: {belief.belief[:50]}...")

        belief.updated_at = datetime.utcnow()

        logger.info(
            f"Challenged belief: {belief.belief[:50]}... "
            f"({old_confidence:.2f} -> {new_confidence:.2f})"
        )
        return belief

    async def supersede(
        self,
        old_belief_id: UUID,
        new_belief: str,
        reason: str = "evolved understanding",
    ) -> MemoryBelief | None:
        """
        Supersede an old belief with a new one.
        """
        old = await self.get_by_id(old_belief_id)
        if not old:
            return None

        # Create new belief with inherited confidence
        new = await self.form(
            belief=new_belief,
            belief_type=old.belief_type,
            initial_confidence=old.confidence,
            supporting_facts=old.supporting_facts,
        )

        # Mark old as superseded
        old.status = "superseded"
        old.superseded_by = new.id

        # Add to history
        history = old.confidence_history or []
        history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "value": old.confidence,
            "reason": f"superseded: {reason}",
        })
        old.confidence_history = history

        logger.info(f"Superseded belief: {old.belief[:30]}... -> {new.belief[:30]}...")
        return new

    async def reject(self, belief_id: UUID, reason: str = "manually rejected") -> bool:
        """Reject a belief (soft delete)."""
        belief = await self.get_by_id(belief_id)
        if not belief:
            return False

        belief.status = "rejected"
        belief.updated_at = datetime.utcnow()

        # Add to history
        history = belief.confidence_history or []
        history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "value": belief.confidence,
            "reason": f"rejected: {reason}",
        })
        belief.confidence_history = history

        logger.info(f"Rejected belief: {belief.belief[:50]}...")
        return True

    async def evolve_from_evidence(self) -> int:
        """
        Evolve beliefs based on accumulated evidence.
        Returns number of beliefs modified.
        """
        from src.db.models.memory import MemoryFact

        # Get active beliefs
        result = await self.db.execute(
            select(MemoryBelief).where(
                and_(
                    MemoryBelief.session_id == self.session_id,
                    MemoryBelief.status == "active",
                )
            )
        )
        beliefs = result.scalars().all()

        modified = 0
        for belief in beliefs:
            # Check for new supporting evidence
            if belief.supporting_facts:
                # Count valid supporting facts
                valid_count = await self.db.execute(
                    select(func.count(MemoryFact.id)).where(
                        and_(
                            MemoryFact.id.in_(belief.supporting_facts),
                            or_(
                                MemoryFact.valid_to.is_(None),
                                MemoryFact.valid_to > datetime.utcnow(),
                            ),
                        )
                    )
                )
                valid = valid_count.scalar() or 0

                # If most evidence is still valid, slightly reinforce
                if valid > len(belief.supporting_facts) * 0.5:
                    belief.confidence = min(0.99, belief.confidence + 0.02)
                    modified += 1

            # Check for contradicting evidence
            if belief.contradicting_facts:
                # Count valid contradicting facts
                contra_count = await self.db.execute(
                    select(func.count(MemoryFact.id)).where(
                        and_(
                            MemoryFact.id.in_(belief.contradicting_facts),
                            or_(
                                MemoryFact.valid_to.is_(None),
                                MemoryFact.valid_to > datetime.utcnow(),
                            ),
                        )
                    )
                )
                contra = contra_count.scalar() or 0

                # If contradicting evidence is strong, challenge
                if contra > 0:
                    ratio = contra / max(1, len(belief.supporting_facts or []) + contra)
                    if ratio > 0.3:
                        belief.confidence = max(0.1, belief.confidence * 0.9)
                        modified += 1

        return modified

    async def count_by_domain(self, domain: str) -> int:
        """Count beliefs related to a domain."""
        # Simple text matching for domain
        result = await self.db.execute(
            select(func.count(MemoryBelief.id)).where(
                and_(
                    MemoryBelief.session_id == self.session_id,
                    MemoryBelief.status == "active",
                    MemoryBelief.belief.ilike(f"%{domain}%"),
                )
            )
        )
        return result.scalar() or 0

    async def get_high_confidence(self, threshold: float = 0.8) -> list[MemoryBelief]:
        """Get high-confidence beliefs."""
        result = await self.db.execute(
            select(MemoryBelief).where(
                and_(
                    MemoryBelief.session_id == self.session_id,
                    MemoryBelief.status == "active",
                    MemoryBelief.confidence >= threshold,
                )
            ).order_by(MemoryBelief.confidence.desc())
        )
        return list(result.scalars().all())

    async def get_uncertain(self, threshold: float = 0.5) -> list[MemoryBelief]:
        """Get uncertain beliefs that need more evidence."""
        result = await self.db.execute(
            select(MemoryBelief).where(
                and_(
                    MemoryBelief.session_id == self.session_id,
                    MemoryBelief.status == "active",
                    MemoryBelief.confidence < threshold,
                    MemoryBelief.confidence > 0.1,
                )
            ).order_by(MemoryBelief.times_challenged.desc())
        )
        return list(result.scalars().all())
