"""Example usage of Memory Evolution system.

This demonstrates how to use MemoryEvolution to optimize memory parameters.
"""

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.evolution.memory_evolution import MemoryEvolution


async def example_usage(db: AsyncSession) -> None:
    """Example of using Memory Evolution."""

    # Initialize Memory Evolution
    evolution = MemoryEvolution(db, session_id="example_session")

    # Get current parameters
    current = evolution.get_current_params()
    print("Current parameters:")
    print(f"  decay_rate_facts: {current['decay_rate_facts']}")
    print(f"  decay_rate_beliefs: {current['decay_rate_beliefs']}")
    print(f"  importance_threshold: {current['importance_threshold']}")
    print()

    # Simulate detected issues
    issues: list[dict[str, Any]] = [
        {
            "type": "low_recall",
            "severity": "high",
            "details": "Users reporting forgotten important facts from recent conversations",
        },
        {
            "type": "poor_retrieval",
            "severity": "medium",
            "details": "Search not finding relevant memories",
        },
    ]

    # Evolve parameters based on issues
    print("Evolving parameters...")
    result = await evolution.evolve(issues)

    if result["changed"]:
        print(f"\nApplied {len(result['changes'])} changes:")
        for change in result["changes"]:
            print(f"  - {change}")
    else:
        print("\nNo changes needed")

    print("\nNew parameters:")
    new_params = result["new_params"]
    print(f"  decay_rate_facts: {new_params['decay_rate_facts']}")
    print(f"  decay_rate_beliefs: {new_params['decay_rate_beliefs']}")
    print(f"  importance_threshold: {new_params['importance_threshold']}")

    # View parameter history
    history = await evolution.get_param_history()
    print(f"\nParameter history: {len(history)} versions")

    # Rollback example (if needed)
    # rollback_result = await evolution.rollback()
    # print(f"Rollback: {rollback_result['message']}")


async def example_issue_handling() -> None:
    """Example of handling different issue types."""

    # Mock database session (replace with actual session in production)
    db = None

    evolution = MemoryEvolution(db, session_id="test")  # type: ignore[arg-type]

    # Example 1: Memory overload
    print("Example 1: Memory Overload")
    issues = [
        {
            "type": "memory_overload",
            "severity": "high",
            "details": "Database contains 10000+ low-importance memories",
        }
    ]
    result = await evolution.evolve(issues)
    print(f"Changes: {result['changes']}\n")

    # Example 2: Weak connections
    print("Example 2: Weak Memory Connections")
    issues = [
        {
            "type": "weak_connections",
            "severity": "medium",
            "details": "Few links between related memories",
        }
    ]
    result = await evolution.evolve(issues)
    print(f"Changes: {result['changes']}\n")

    # Example 3: Link noise
    print("Example 3: Too Many Weak Links")
    issues = [
        {
            "type": "link_noise",
            "severity": "medium",
            "details": "Many irrelevant memory connections",
        }
    ]
    result = await evolution.evolve(issues)
    print(f"Changes: {result['changes']}\n")


if __name__ == "__main__":
    print("Memory Evolution Examples")
    print("=" * 50)
    asyncio.run(example_issue_handling())
