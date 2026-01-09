"""Smart AI model router with cost optimization."""

import json
from collections import defaultdict
from datetime import timedelta
from enum import Enum
from typing import Any

from anthropic import Anthropic

from src.core.config import settings
from src.core.datetime_utils import utc_now_naive
from src.core.logging import get_logger

logger = get_logger(__name__)


class ModelTier(Enum):
    """Claude model tiers with pricing."""

    HAIKU = "claude-haiku-4-5-20251001"  # $0.25/$1.25 per MTok
    SONNET = "claude-sonnet-4-5-20250929"  # $3/$15 per MTok
    OPUS = "claude-opus-4-5-20251101"  # $15/$75 per MTok


class TaskComplexity(Enum):
    """Task complexity levels."""

    TRIVIAL = 1  # Simple classification, quick lookups
    SIMPLE = 2  # Basic analysis, simple queries
    MEDIUM = 3  # Moderate reasoning, summaries
    COMPLEX = 4  # Deep analysis, multi-step reasoning
    EXPERT = 5  # Advanced reasoning, code generation


class AIRouter:
    """Smart AI model router with budget management and caching."""

    # Daily budget limits (in USD)
    DAILY_BUDGETS = {
        ModelTier.HAIKU: 2.0,
        ModelTier.SONNET: 3.0,
        ModelTier.OPUS: 5.0,
    }

    # Approximate token costs (per 1M tokens)
    TOKEN_COSTS = {
        ModelTier.HAIKU: {"input": 0.25, "output": 1.25},
        ModelTier.SONNET: {"input": 3.0, "output": 15.0},
        ModelTier.OPUS: {"input": 15.0, "output": 75.0},
    }

    # Complexity to model mapping
    COMPLEXITY_MAP = {
        TaskComplexity.TRIVIAL: ModelTier.HAIKU,
        TaskComplexity.SIMPLE: ModelTier.HAIKU,
        TaskComplexity.MEDIUM: ModelTier.SONNET,
        TaskComplexity.COMPLEX: ModelTier.SONNET,
        TaskComplexity.EXPERT: ModelTier.OPUS,
    }

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize AI router with Anthropic client."""
        self.client = Anthropic(api_key=api_key or settings.anthropic_api_key)
        self.cache: dict[str, dict[str, Any]] = {}
        self.daily_usage: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "haiku_cost": 0.0,
                "sonnet_cost": 0.0,
                "opus_cost": 0.0,
                "haiku_requests": 0,
                "sonnet_requests": 0,
                "opus_requests": 0,
                "haiku_tokens_in": 0,
                "haiku_tokens_out": 0,
                "sonnet_tokens_in": 0,
                "sonnet_tokens_out": 0,
                "opus_tokens_in": 0,
                "opus_tokens_out": 0,
            }
        )

        logger.info(
            "AIRouter initialized",
            extra={
                "daily_budgets": {tier.name: budget for tier, budget in self.DAILY_BUDGETS.items()},
            },
        )

    def _get_today_key(self) -> str:
        """Get today's date key for usage tracking."""
        return utc_now_naive().strftime("%Y-%m-%d")

    def _select_model(
        self,
        complexity: TaskComplexity,
        force_model: ModelTier | None = None,
    ) -> ModelTier:
        """Select model based on complexity and budget."""
        if force_model:
            logger.debug(
                "Model forced by caller",
                extra={"model": force_model.name},
            )
            return force_model

        # Get recommended model
        recommended = self.COMPLEXITY_MAP[complexity]
        today_key = self._get_today_key()
        usage = self.daily_usage[today_key]

        # Check if recommended model is within budget
        model_key = f"{recommended.name.lower()}_cost"
        if usage[model_key] >= self.DAILY_BUDGETS[recommended]:
            # Budget exceeded, try to downgrade
            logger.warning(
                "Model budget exceeded, attempting downgrade",
                extra={
                    "model": recommended.name,
                    "usage": usage[model_key],
                    "budget": self.DAILY_BUDGETS[recommended],
                },
            )

            # Try downgrade path: OPUS -> SONNET -> HAIKU
            if recommended == ModelTier.OPUS:
                if usage["sonnet_cost"] < self.DAILY_BUDGETS[ModelTier.SONNET]:
                    logger.info("Downgraded from Opus to Sonnet")
                    return ModelTier.SONNET
                if usage["haiku_cost"] < self.DAILY_BUDGETS[ModelTier.HAIKU]:
                    logger.info("Downgraded from Opus to Haiku")
                    return ModelTier.HAIKU
            elif recommended == ModelTier.SONNET:
                if usage["haiku_cost"] < self.DAILY_BUDGETS[ModelTier.HAIKU]:
                    logger.info("Downgraded from Sonnet to Haiku")
                    return ModelTier.HAIKU

            # All budgets exceeded
            logger.error("All model budgets exceeded for today")
            raise RuntimeError("Daily AI budget exceeded for all models")

        return recommended

    def _estimate_complexity(
        self,
        prompt: str,
        context_length: int = 0,
    ) -> TaskComplexity:
        """Auto-detect task complexity from prompt and context."""
        prompt_lower = prompt.lower()

        # Simple heuristics for complexity estimation
        if any(
            keyword in prompt_lower
            for keyword in ["classify", "category", "tag", "is this", "yes or no"]
        ):
            return TaskComplexity.TRIVIAL

        if any(
            keyword in prompt_lower
            for keyword in ["list", "show", "what is", "simple"]
        ):
            return TaskComplexity.SIMPLE

        if any(
            keyword in prompt_lower
            for keyword in ["analyze", "compare", "summarize", "explain"]
        ):
            return TaskComplexity.MEDIUM

        if any(
            keyword in prompt_lower
            for keyword in [
                "deep analysis",
                "complex",
                "multi-step",
                "reasoning",
                "evaluate",
            ]
        ):
            return TaskComplexity.COMPLEX

        if any(
            keyword in prompt_lower
            for keyword in ["code", "implement", "create agent", "generate script"]
        ):
            return TaskComplexity.EXPERT

        # Default based on context length
        if context_length > 5000:
            return TaskComplexity.COMPLEX
        if context_length > 2000:
            return TaskComplexity.MEDIUM
        return TaskComplexity.SIMPLE

    def _calculate_cost(
        self,
        model: ModelTier,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for token usage."""
        costs = self.TOKEN_COSTS[model]
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost

    def _update_usage(
        self,
        model: ModelTier,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """Update daily usage statistics."""
        today_key = self._get_today_key()
        usage = self.daily_usage[today_key]
        model_name = model.name.lower()

        usage[f"{model_name}_cost"] += cost
        usage[f"{model_name}_requests"] += 1
        usage[f"{model_name}_tokens_in"] += input_tokens
        usage[f"{model_name}_tokens_out"] += output_tokens

        logger.debug(
            "Usage updated",
            extra={
                "model": model.name,
                "cost": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "daily_cost": usage[f"{model_name}_cost"],
            },
        )

    def _get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model."""
        return f"{model}:{hash(prompt)}"

    async def query(
        self,
        prompt: str,
        context: str = "",
        complexity: TaskComplexity | None = None,
        force_model: ModelTier | None = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Query AI with automatic model selection and caching."""
        # Auto-detect complexity if not provided
        if complexity is None:
            complexity = self._estimate_complexity(prompt, len(context))
            logger.debug(
                "Auto-detected complexity",
                extra={"complexity": complexity.name},
            )

        # Select model
        model = self._select_model(complexity, force_model)

        # Check cache
        cache_key = self._get_cache_key(prompt + context, model.value)
        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if utc_now_naive() - cached["timestamp"] < timedelta(seconds=cache_ttl):
                logger.info(
                    "Cache hit",
                    extra={"cache_key": cache_key[:50]},
                )
                return {
                    "response": cached["response"],
                    "model": model.name,
                    "cached": True,
                    "cost": 0.0,
                }

        # Build messages
        messages = []
        if context:
            messages.append(
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuery:\n{prompt}",
                }
            )
        else:
            messages.append({"role": "user", "content": prompt})

        # Call Anthropic API
        try:
            logger.info(
                "Calling Anthropic API",
                extra={
                    "model": model.name,
                    "complexity": complexity.name,
                    "prompt_length": len(prompt),
                    "context_length": len(context),
                },
            )

            response = self.client.messages.create(
                model=model.value,
                max_tokens=max_tokens,
                messages=messages,
            )

            # Extract response
            response_text = response.content[0].text if response.content else ""

            # Calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            # Update usage
            self._update_usage(model, input_tokens, output_tokens, cost)

            # Cache response
            if use_cache:
                self.cache[cache_key] = {
                    "response": response_text,
                    "timestamp": utc_now_naive(),
                }

            logger.info(
                "Anthropic API call successful",
                extra={
                    "model": model.name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": cost,
                },
            )

            return {
                "response": response_text,
                "model": model.name,
                "cached": False,
                "cost": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        except Exception as e:
            logger.error(
                "Anthropic API call failed",
                extra={
                    "model": model.name,
                    "error": str(e),
                },
            )
            raise

    def get_usage_stats(self, days: int = 7) -> dict[str, Any]:
        """Get usage statistics for dashboard."""
        today = utc_now_naive()
        stats = {
            "daily_usage": [],
            "total_cost": 0.0,
            "total_requests": 0,
            "model_breakdown": {
                "haiku": {"cost": 0.0, "requests": 0},
                "sonnet": {"cost": 0.0, "requests": 0},
                "opus": {"cost": 0.0, "requests": 0},
            },
            "budget_status": {
                "haiku": {
                    "used": 0.0,
                    "limit": self.DAILY_BUDGETS[ModelTier.HAIKU],
                    "remaining": self.DAILY_BUDGETS[ModelTier.HAIKU],
                },
                "sonnet": {
                    "used": 0.0,
                    "limit": self.DAILY_BUDGETS[ModelTier.SONNET],
                    "remaining": self.DAILY_BUDGETS[ModelTier.SONNET],
                },
                "opus": {
                    "used": 0.0,
                    "limit": self.DAILY_BUDGETS[ModelTier.OPUS],
                    "remaining": self.DAILY_BUDGETS[ModelTier.OPUS],
                },
            },
        }

        # Collect stats for last N days
        for day_offset in range(days):
            date = today - timedelta(days=day_offset)
            date_key = date.strftime("%Y-%m-%d")

            if date_key in self.daily_usage:
                usage = self.daily_usage[date_key]
                daily_total = (
                    usage["haiku_cost"] + usage["sonnet_cost"] + usage["opus_cost"]
                )
                daily_requests = (
                    usage["haiku_requests"]
                    + usage["sonnet_requests"]
                    + usage["opus_requests"]
                )

                stats["daily_usage"].append(
                    {
                        "date": date_key,
                        "cost": daily_total,
                        "requests": daily_requests,
                        "haiku_cost": usage["haiku_cost"],
                        "sonnet_cost": usage["sonnet_cost"],
                        "opus_cost": usage["opus_cost"],
                    }
                )

                stats["total_cost"] += daily_total
                stats["total_requests"] += daily_requests

                # Update model breakdown
                for model in ["haiku", "sonnet", "opus"]:
                    stats["model_breakdown"][model]["cost"] += usage[f"{model}_cost"]
                    stats["model_breakdown"][model]["requests"] += usage[
                        f"{model}_requests"
                    ]

        # Update today's budget status
        today_key = self._get_today_key()
        if today_key in self.daily_usage:
            usage = self.daily_usage[today_key]
            for model in ["haiku", "sonnet", "opus"]:
                model_tier = ModelTier[model.upper()]
                used = usage[f"{model}_cost"]
                limit = self.DAILY_BUDGETS[model_tier]
                stats["budget_status"][model]["used"] = used
                stats["budget_status"][model]["remaining"] = max(0, limit - used)

        return stats


class ObserverTasks:
    """Pre-configured tasks for Observer with optimized complexity."""

    def __init__(self, router: AIRouter):
        """Initialize with AI router."""
        self.router = router

    async def classify_activity(
        self,
        activity: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify activity (Haiku, cached)."""
        prompt = f"""Classify this activity into one of: productive, neutral, distracting.

App: {activity.get('app_name', 'unknown')}
Title: {activity.get('window_title', 'unknown')}

Reply with just one word: productive, neutral, or distracting."""

        return await self.router.query(
            prompt=prompt,
            complexity=TaskComplexity.TRIVIAL,
            use_cache=True,
            cache_ttl=86400,  # 24 hours
            max_tokens=10,
        )

    async def summarize_period(
        self,
        events: list[dict[str, Any]],
        period: str = "day",
    ) -> dict[str, Any]:
        """Summarize activity period (Haiku)."""
        # Build context from events
        context = json.dumps(
            [
                {
                    "app": e.get("app_name"),
                    "title": e.get("window_title"),
                    "duration": e.get("duration_seconds"),
                }
                for e in events[:50]  # Limit to avoid token limits
            ]
        )

        prompt = f"Summarize this {period}'s activity in 2-3 sentences. Focus on main apps and tasks."

        return await self.router.query(
            prompt=prompt,
            context=context,
            complexity=TaskComplexity.SIMPLE,
            use_cache=False,
            max_tokens=200,
        )

    async def analyze_productivity(
        self,
        daily_stats: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze productivity patterns (Sonnet)."""
        context = json.dumps(daily_stats)
        prompt = """Analyze productivity patterns and provide:
1. Key insights about work habits
2. Potential distractions identified
3. Recommendations for improvement

Keep response concise (3-4 bullet points)."""

        return await self.router.query(
            prompt=prompt,
            context=context,
            complexity=TaskComplexity.MEDIUM,
            use_cache=False,
            max_tokens=500,
        )

    async def chat_response(
        self,
        user_message: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Generate chat response (Sonnet)."""
        return await self.router.query(
            prompt=user_message,
            context=context,
            complexity=TaskComplexity.MEDIUM,
            use_cache=False,
            max_tokens=1024,
        )

    async def agent_code_task(
        self,
        task: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Generate agent code (Opus)."""
        prompt = f"""Generate Python code for this automation task:

{task}

Provide clean, well-documented code."""

        return await self.router.query(
            prompt=prompt,
            context=context,
            complexity=TaskComplexity.EXPERT,
            use_cache=False,
            max_tokens=4096,
        )

    async def create_automation_script(
        self,
        description: str,
    ) -> dict[str, Any]:
        """Create automation script from description (Opus)."""
        prompt = f"""Create an automation script for this task:

{description}

Provide:
1. Step-by-step commands
2. Error handling
3. Confirmation points

Return as JSON with structure: {{"steps": [...], "requires_confirmation": bool}}"""

        return await self.router.query(
            prompt=prompt,
            complexity=TaskComplexity.EXPERT,
            use_cache=True,
            cache_ttl=3600,
            max_tokens=2048,
        )


# Global AI router instance
_ai_router: AIRouter | None = None


def get_ai_router() -> AIRouter:
    """Get or create global AI router instance."""
    global _ai_router
    if _ai_router is None:
        _ai_router = AIRouter()
    return _ai_router
