"""Budget agent node implementation for LangGraph orchestration.

This module implements the budget optimization agent as a LangGraph node.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage.orchestration.utils.structured import StructuredExtractor, model_to_dict
from tripsage_core.config import get_settings
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class BudgetParameters(BaseModel):
    """Structured payload used for budget parameter extraction."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["optimize", "track", "compare", "analyze"] | None = None
    total_budget: float | None = Field(default=None, ge=0)
    trip_length: int | None = Field(default=None, ge=1)
    travelers: int | None = Field(default=None, ge=1)
    destination: str | None = None
    categories: list[str] | None = None
    expenses: list[dict[str, Any]] | None = None
    options: list[dict[str, Any]] | None = None
    preferences: dict[str, Any] | None = None


def _empty_tool_list() -> list[BaseTool]:
    """Return a typed empty tool list."""
    return []


@dataclass(slots=True)
class _RuntimeState:
    llm: ChatOpenAI | None = None
    llm_with_tools: ChatOpenAI | None = None
    parameter_extractor: StructuredExtractor[BudgetParameters] | None = None
    tools: list[BaseTool] = field(default_factory=_empty_tool_list)


class BudgetAgentNode(BaseAgentNode):
    """Budget optimization agent node.

    This node handles all budget-related requests including optimization,
    expense tracking, cost comparisons, and savings recommendations using MCP tool
    integration.
    """

    def __init__(self, services: AppServiceContainer, **config_overrides: Any):
        """Initialize the budget agent node with dynamic configuration.

        Args:
            services: Application service container for dependency injection
            **config_overrides: Runtime configuration overrides (e.g., temperature=0.5)
        """
        # Store overrides for async config loading
        self.config_overrides: dict[str, Any] = dict(config_overrides)
        self.agent_config: dict[str, Any] = {}
        self._runtime = _RuntimeState()

        super().__init__("budget_agent", services)

        # Get configuration service for database-backed config
        self.config_service: Any = self.get_service("configuration_service")

    def _initialize_tools(self) -> None:
        """Initialize budget-specific tools using simple tool catalog."""
        from tripsage.orchestration.tools.tools import get_tools_for_agent

        self._runtime.tools = get_tools_for_agent("budget_agent")

        if self._runtime.llm:
            runtime_llm = cast(Any, self._runtime.llm)
            self._runtime.llm_with_tools = cast(
                ChatOpenAI, runtime_llm.bind_tools(self._runtime.tools)
            )

        logger.info("Initialized budget agent with %s tools", len(self._runtime.tools))

    async def _load_configuration(self) -> None:
        """Load agent configuration from database with fallback to settings."""
        try:
            # Get configuration from database with runtime overrides
            self.agent_config = await self.config_service.get_agent_config(
                "budget_agent", **self.config_overrides
            )
            if not self.agent_config:
                raise RuntimeError("Budget agent configuration is missing")

            # Initialize LLM with loaded configuration
            self._runtime.llm = self._create_llm_from_config()
            self._runtime.parameter_extractor = StructuredExtractor(
                self._runtime.llm, BudgetParameters, logger=logger
            )
            if self._runtime.tools:
                runtime_llm = cast(Any, self._runtime.llm)
                self._runtime.llm_with_tools = cast(
                    ChatOpenAI, runtime_llm.bind_tools(self._runtime.tools)
                )

            logger.info(
                "Loaded budget agent configuration from database: temp=%s",
                self.agent_config["temperature"],
            )

        except Exception:
            logger.exception("Failed to load database configuration, using fallback")

            # Fallback to settings-based configuration
            settings = get_settings()
            from tripsage.orchestration.config import get_default_config

            fallback = get_default_config()
            secret_candidate: Any = settings.openai_api_key
            if isinstance(secret_candidate, SecretStr):
                api_key = secret_candidate.get_secret_value()  # type: ignore[attr-defined]  # pylint: disable=no-member
            else:
                api_key = ""
            self.agent_config = {
                "model": fallback.default_model,
                "temperature": fallback.temperature,
                "api_key": api_key,
                "top_p": 1.0,
            }

            self._runtime.llm = self._create_llm_from_config()
            self._runtime.parameter_extractor = StructuredExtractor(
                self._runtime.llm, BudgetParameters, logger=logger
            )
            if self._runtime.tools:
                runtime_llm = cast(Any, self._runtime.llm)
                self._runtime.llm_with_tools = cast(
                    ChatOpenAI, runtime_llm.bind_tools(self._runtime.tools)
                )

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process budget-related requests.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with budget analysis and response
        """
        # Ensure configuration is loaded before processing
        if not self.agent_config:
            await self._load_configuration()

        user_message = state["messages"][-1]["content"] if state["messages"] else ""

        # Extract budget parameters from user message and context
        budget_params = await self._extract_budget_parameters(user_message, state)

        if budget_params:
            # Determine the type of budget operation requested
            operation_type = budget_params.get("operation", "optimize")

            if operation_type == "optimize":
                # Perform budget optimization
                budget_analysis = await self._optimize_budget(budget_params, state)
            elif operation_type == "track":
                # Track expenses
                budget_analysis = await self._track_expenses(budget_params, state)
            elif operation_type == "compare":
                # Compare cost options
                budget_analysis = await self._compare_costs(budget_params, state)
            elif operation_type == "analyze":
                # Analyze spending patterns
                budget_analysis = await self._analyze_spending(budget_params, state)
            else:
                # Default to budget optimization
                budget_analysis = await self._optimize_budget(budget_params, state)

            # Update state with results
            budget_record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "operation": operation_type,
                "parameters": budget_params,
                "analysis": budget_analysis,
                "agent": "budget_agent",
            }

            if "budget_analyses" not in state:
                state["budget_analyses"] = []
            state["budget_analyses"].append(budget_record)

            # Generate user-friendly response
            response_message = await self._generate_budget_response(
                budget_analysis, budget_params, operation_type, state
            )
        else:
            # Handle general budget inquiries
            response_message = await self._handle_general_budget_inquiry(
                user_message, state
            )

        # Add response to conversation
        state["messages"].append(response_message)

        return state

    async def _extract_budget_parameters(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any] | None:
        """Extract budget parameters from user message and conversation context.

        Args:
            message: User message to analyze
            state: Current conversation state for context

        Returns:
            Dictionary of budget parameters or None if insufficient info
        """
        # Use LLM to extract parameters and determine operation type
        extraction_prompt = f"""
        Extract budget-related parameters from this message and context, and determine
        the type of budget operation requested.

        User message: "{message}"

        Context from conversation:
        - Previous budget analyses: {len(state.get("budget_analyses", []))}
        - Flight searches: {len(state.get("flight_searches", []))}
        - Accommodation searches: {len(state.get("accommodation_searches", []))}
        - User preferences: {state.get("user_preferences", "None")}
        - Destination info: {state.get("destination_info", "None")}

        Determine the operation type from these options:
        - "optimize": Budget optimization and allocation
        - "track": Expense tracking and recording
        - "compare": Cost comparison between options
        - "analyze": Spending analysis and reporting

        Extract these parameters if mentioned:
        - operation: One of the operation types above
        - total_budget: Total available budget
        - trip_length: Duration in days
        - travelers: Number of travelers
        - destination: Destination(s)
        - categories: Budget categories to focus on
        - expenses: List of expenses (for tracking)
        - options: Items to compare (for comparison)
        - preferences: Budget preferences and priorities

        Respond with JSON only. If this doesn't seem budget-related, return null.

        Example: {{"operation": "optimize", "total_budget": 5000,
                   "trip_length": 10, "travelers": 2, "destination": "Paris"}}
        """

        try:
            extractor = self._runtime.parameter_extractor
            if extractor is None:
                raise RuntimeError("Budget parameter extractor is not initialised")

            result = await extractor.extract_from_prompts(
                system_prompt=(
                    "You are a budget analysis parameter extraction assistant."
                ),
                user_prompt=extraction_prompt,
            )
        except Exception:
            logger.exception("Error extracting budget parameters")
            return None
        params = model_to_dict(result)

        if params and (
            params.get("operation")
            or params.get("total_budget")
            or "budget" in message.lower()
        ):
            return params
        return None

    async def _optimize_budget(
        self, params: dict[str, Any], state: TravelPlanningState
    ) -> dict[str, Any]:
        """Optimize budget allocation based on trip parameters and preferences.

        Args:
            params: Budget optimization parameters
            state: Current conversation state

        Returns:
            Budget optimization analysis
        """
        total_budget = params.get("total_budget", 0)
        trip_length = params.get("trip_length", 7)
        travelers = params.get("travelers", 1)
        destination = params.get("destination", "")

        # Allocation logic based on destination and preferences
        # These percentages can be adjusted based on destination type, user
        # preferences, etc.
        if destination.lower() in ["paris", "london", "tokyo", "new york"]:
            # Expensive cities - allocate more to accommodation and food
            transportation_pct = 0.25
            accommodation_pct = 0.40
            food_pct = 0.25
            activities_pct = 0.05
            contingency_pct = 0.05
        elif destination.lower() in ["thailand", "vietnam", "india", "mexico"]:
            # Budget-friendly destinations - more for activities
            transportation_pct = 0.35
            accommodation_pct = 0.25
            food_pct = 0.15
            activities_pct = 0.20
            contingency_pct = 0.05
        else:
            # Default allocation
            transportation_pct = 0.30
            accommodation_pct = 0.35
            food_pct = 0.20
            activities_pct = 0.10
            contingency_pct = 0.05

        # Calculate allocations
        transportation = total_budget * transportation_pct
        accommodation = total_budget * accommodation_pct
        food = total_budget * food_pct
        activities = total_budget * activities_pct
        contingency = total_budget * contingency_pct

        # Calculate per-day and per-person amounts
        accommodation_per_night = accommodation / trip_length
        food_per_day = food / trip_length
        food_per_meal = food_per_day / 3
        activities_per_day = activities / trip_length
        daily_total = accommodation_per_night + food_per_day + activities_per_day

        return {
            "total_budget": total_budget,
            "trip_length": trip_length,
            "travelers": travelers,
            "destination": destination,
            "allocations": {
                "transportation": round(transportation, 2),
                "accommodation": round(accommodation, 2),
                "food": round(food, 2),
                "activities": round(activities, 2),
                "contingency": round(contingency, 2),
            },
            "daily_budget": {
                "accommodation_per_night": round(accommodation_per_night, 2),
                "food_per_day": round(food_per_day, 2),
                "food_per_meal": round(food_per_meal, 2),
                "activities_per_day": round(activities_per_day, 2),
                "daily_total": round(daily_total, 2),
            },
            "percentages": {
                "transportation": transportation_pct * 100,
                "accommodation": accommodation_pct * 100,
                "food": food_pct * 100,
                "activities": activities_pct * 100,
                "contingency": contingency_pct * 100,
            },
        }

    async def _track_expenses(
        self, params: dict[str, Any], state: TravelPlanningState
    ) -> dict[str, Any]:
        """Track and categorize travel expenses.

        Args:
            params: Expense tracking parameters
            state: Current conversation state

        Returns:
            Expense tracking analysis
        """
        expenses = params.get("expenses", [])
        trip_id = params.get("trip_id", f"trip_{datetime.now(UTC).strftime('%Y%m%d')}")

        # Categorize and sum expenses
        categories = {
            "transportation": 0,
            "accommodation": 0,
            "food": 0,
            "activities": 0,
            "other": 0,
        }

        for expense in expenses:
            category = expense.get("category", "other").lower()
            amount = expense.get("amount", 0)
            if category in categories:
                categories[category] += amount
            else:
                categories["other"] += amount

        total_spent = sum(categories.values())

        return {
            "trip_id": trip_id,
            "expenses_count": len(expenses),
            "total_spent": round(total_spent, 2),
            "categories": {k: round(v, 2) for k, v in categories.items()},
            "expenses": expenses,
        }

    async def _compare_costs(
        self, params: dict[str, Any], state: TravelPlanningState
    ) -> dict[str, Any]:
        """Compare cost options for travel components.

        Args:
            params: Cost comparison parameters
            state: Current conversation state

        Returns:
            Cost comparison analysis
        """
        category = params.get("category", "")
        options = params.get("options", [])
        budget = params.get("budget", 0)

        if not options:
            return {
                "category": category,
                "budget": budget,
                "options_count": 0,
                "message": "No options provided for comparison",
            }

        # Analyze options for cost, value, and recommendations
        analyzed_options: list[dict[str, Any]] = []
        options_list: list[dict[str, Any]] = [o for o in options if isinstance(o, dict)]
        for option in options_list:
            cost = option.get("cost", 0)
            value_score = self._calculate_value_score(option, category)
            analyzed_options.append(
                {
                    **option,
                    "value_score": value_score,
                    "within_budget": cost <= budget if budget > 0 else True,
                }
            )

        # Sort by value score
        analyzed_options.sort(
            key=lambda x: float(x.get("value_score", 0.0)), reverse=True
        )

        # Find best value within budget
        best_option: dict[str, Any] | None = None
        analyzed_options_typed: list[dict[str, Any]] = analyzed_options
        if not analyzed_options_typed:
            return {
                "category": category,
                "budget": budget,
                "options_count": 0,
                "analyzed_options": [],
                "best_value": None,
                "cheapest": None,
                "message": "No valid options provided for comparison",
            }
        cheapest_option = min(
            analyzed_options_typed,
            key=lambda x: float(x.get("cost", float("inf"))),
        )

        for option in analyzed_options:
            if option["within_budget"]:
                best_option = option
                break

        return {
            "category": category,
            "budget": budget,
            "options_count": len(options_list),
            "analyzed_options": analyzed_options,
            "best_value": best_option,
            "cheapest": cheapest_option,
        }

    async def _analyze_spending(
        self, params: dict[str, Any], state: TravelPlanningState
    ) -> dict[str, Any]:
        """Analyze spending patterns against budget.

        Args:
            params: Spending analysis parameters
            state: Current conversation state

        Returns:
            Spending analysis
        """
        trip_id = params.get("trip_id", "")

        # Get budget and expense data from state
        budget_data = None
        expense_data = None

        for analysis in state.get("budget_analyses", []):
            if analysis.get("operation") == "optimize":
                budget_data = analysis.get("analysis", {})
            elif analysis.get("operation") == "track":
                expense_data = analysis.get("analysis", {})

        if not budget_data or not expense_data:
            return {
                "trip_id": trip_id,
                "message": "Insufficient budget or expense data for analysis",
                "budget_available": budget_data is not None,
                "expenses_available": expense_data is not None,
            }

        # Compare actual spending to budget
        planned_budget = budget_data.get("allocations", {})
        actual_spending = expense_data.get("categories", {})

        variance_analysis = {}
        for category in planned_budget:
            planned = planned_budget.get(category, 0)
            actual = actual_spending.get(category, 0)
            variance = actual - planned
            variance_pct = (variance / planned * 100) if planned > 0 else 0

            variance_analysis[category] = {
                "planned": planned,
                "actual": actual,
                "variance": round(variance, 2),
                "variance_percentage": round(variance_pct, 2),
                "status": "over"
                if variance > 0
                else "under"
                if variance < 0
                else "on_track",
            }

        return {
            "trip_id": trip_id,
            "total_planned": sum(planned_budget.values()),
            "total_actual": sum(actual_spending.values()),
            "variance_analysis": variance_analysis,
        }

    def _calculate_value_score(self, option: dict[str, Any], category: str) -> float:
        """Calculate a value score for an option based on cost and features.

        Args:
            option: Option to evaluate
            category: Category of the option

        Returns:
            Value score (higher is better)
        """
        cost = option.get("cost", 0)
        rating = option.get("rating", 0)
        features = option.get("features", [])

        if cost <= 0:
            return 0

        # Base score from rating
        score = rating * 20  # Rating out of 5, so max 100

        # Bonus for features
        feature_bonus = len(features) * 5

        # Adjust for cost (lower cost = higher value)
        cost_factor = 1000 / cost if cost > 0 else 0

        return score + feature_bonus + cost_factor

    async def _generate_budget_response(
        self,
        analysis: dict[str, Any],
        params: dict[str, Any],
        operation_type: str,
        state: TravelPlanningState,
    ) -> dict[str, Any]:
        """Generate user-friendly response from budget analysis.

        Args:
            analysis: Budget analysis results
            params: Parameters used for analysis
            operation_type: Type of budget operation
            state: Current conversation state

        Returns:
            Formatted response message
        """
        if operation_type == "optimize":
            content = self._format_optimization_response(analysis, params)
        elif operation_type == "track":
            content = self._format_tracking_response(analysis, params)
        elif operation_type == "compare":
            content = self._format_comparison_response(analysis, params)
        elif operation_type == "analyze":
            content = self._format_analysis_response(analysis, params)
        else:
            content = "Budget analysis completed successfully."

        return self._create_response_message(
            content,
            {
                "operation": operation_type,
                "analysis_summary": analysis,
            },
        )

    def _format_optimization_response(
        self, analysis: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """Format budget optimization response."""
        total_budget = analysis.get("total_budget", 0)
        destination = analysis.get("destination", "your destination")
        trip_length = analysis.get("trip_length", 0)
        allocations = analysis.get("allocations", {})
        daily_budget = analysis.get("daily_budget", {})

        content = (
            f"I've optimized your ${total_budget:,.0f} budget for {trip_length} "
            f"days in {destination}:\n\n"
        )

        content += "**Budget Allocation:**\n"
        for category, amount in allocations.items():
            pct = analysis.get("percentages", {}).get(category, 0)
            content += f"• {category.title()}: ${amount:,.0f} ({pct:.0f}%)\n"

        content += "\n**Daily Budget Breakdown:**\n"
        content += (
            f"• Accommodation: "
            f"${daily_budget.get('accommodation_per_night', 0):.0f}/night\n"
        )
        content += (
            f"• Food: ${daily_budget.get('food_per_day', 0):.0f}/day "
            f"(${daily_budget.get('food_per_meal', 0):.0f}/meal)\n"
        )
        content += (
            f"• Activities: ${daily_budget.get('activities_per_day', 0):.0f}/day\n"
        )
        content += f"• Daily Total: ${daily_budget.get('daily_total', 0):.0f}/day\n"

        content += "\nWould you like me to help you find flights and "
        "accommodations within this budget?"

        return content

    def _format_tracking_response(
        self, analysis: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """Format expense tracking response."""
        total_spent = analysis.get("total_spent", 0)
        categories = analysis.get("categories", {})
        expenses_count = analysis.get("expenses_count", 0)

        content = (
            f"I've tracked {expenses_count} expenses totaling ${total_spent:,.2f}:\n\n"
        )

        content += "**Spending by Category:**\n"
        for category, amount in categories.items():
            if amount > 0:
                content += f"• {category.title()}: ${amount:,.2f}\n"

        content += "\nWould you like me to analyze this spending against your budget?"

        return content

    def _format_comparison_response(
        self, analysis: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """Format cost comparison response."""
        category = analysis.get("category", "options")
        options_count = analysis.get("options_count", 0)
        best_option = analysis.get("best_value")
        cheapest_option = analysis.get("cheapest")

        content = f"I've compared {options_count} {category} options:\n\n"

        if best_option:
            content += (
                f"**Best Value:** {best_option.get('name', 'Option')} - "
                f"${best_option.get('cost', 0):,.0f}\n"
            )
            content += f"Value Score: {best_option.get('value_score', 0):.1f}\n\n"

        if cheapest_option and cheapest_option != best_option:
            content += (
                f"**Cheapest Option:** {cheapest_option.get('name', 'Option')} "
                f"- ${cheapest_option.get('cost', 0):,.0f}\n\n"
            )

        content += "Would you like more details about any of these options?"

        return content

    def _format_analysis_response(
        self, analysis: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """Format spending analysis response."""
        if "message" in analysis:
            return analysis["message"]

        total_planned = analysis.get("total_planned", 0)
        total_actual = analysis.get("total_actual", 0)
        variance_analysis = analysis.get("variance_analysis", {})

        content = "**Budget vs. Actual Spending Analysis:**\n\n"
        content += f"Planned Budget: ${total_planned:,.2f}\n"
        content += f"Actual Spending: ${total_actual:,.2f}\n"
        content += f"Overall Variance: ${total_actual - total_planned:,.2f}\n\n"

        content += "**Category Breakdown:**\n"
        for category, data in variance_analysis.items():
            status_emoji = "⚠️" if data["status"] == "over" else "✅"
            content += (
                f"{status_emoji} {category.title()}: ${data['actual']:,.2f} vs "
                f"${data['planned']:,.2f} "
            )
            content += (
                f"({data['variance']:+,.2f}, {data['variance_percentage']:+.1f}%)\n"
            )

        return content

    async def _handle_general_budget_inquiry(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any]:
        """Handle general budget inquiries that don't require specific analysis.

        Args:
            message: User message
            state: Current conversation state

        Returns:
            Response message
        """
        # Use LLM to generate helpful response for general budget questions
        response_prompt = f"""
        The user is asking about travel budgeting but hasn't provided enough specific
        information for analysis.

        User message: "{message}"

        Provide a helpful response that:
        1. Acknowledges their budget interest
        2. Asks for specific information needed (total budget, trip length,
        destination, travelers)
        3. Explains what budget services you can provide (optimization, tracking,
        analysis)
        4. Offers to help once they provide details

        Keep the response friendly and concise.
        """

        llm = self._runtime.llm
        if llm is None:
            raise RuntimeError("Budget LLM is not initialized")

        try:
            messages = [
                SystemMessage(
                    content="You are a helpful travel budget optimization assistant."
                ),
                HumanMessage(content=response_prompt),
            ]

            response: Any = await llm.ainvoke(messages)
            raw_resp: Any = response
            if hasattr(raw_resp, "content"):
                raw_content: Any = raw_resp.content
            else:
                raw_content = raw_resp
            if isinstance(raw_content, str):
                content: str = raw_content
            else:
                content = str(raw_content)

        except Exception:
            logger.exception("Error generating budget response")
            content = (
                "I'd be happy to help you optimize your travel budget! To get started, "
                "I'll need to know your total budget, trip length, destination, and "
                "number of travelers. I can help with budget allocation, expense "
                "tracking, cost comparisons, and spending analysis. What aspect of "
                "budgeting would you like help with?"
            )

        return self._create_response_message(content)
