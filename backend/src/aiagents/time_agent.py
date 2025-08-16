from agents import Agent
from backend.src.aiagents.prompts import TimeTrackerPrompts
from backend.src.aiagents.tools.time_tools import create_time_entry_tool 
from backend.src.aiagents.tools.time_tools import get_timesheet_tool
from backend.src.aiagents.tools.contract_tools import ContractToolResult
from backend.src.aiagents.guardrails.input_guardrails import input_sanitization_guardrail
from backend.src.aiagents.guardrails.output_guardrails import output_validation_guardrail
from typing import Dict, Any
from datetime import date
from decimal import Decimal
from backend.src.database.core.models import TimeEntry
from backend.src.database.core.schemas import TimeEntryCreate
from typing import Optional

class TimeTrackerAgent:
    def __init__(self):
        self.agent = Agent(
            name="TimeTracker",
            instructions=TimeTrackerPrompts.SYSTEM_INSTRUCTIONS,
            model="gpt-4o-mini",
            tools=[
                create_time_entry_tool,
                get_timesheet_tool
            ],
            output_type=ContractToolResult,
            input_guardrails=[input_sanitization_guardrail]
        )
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user message through TimeTracker"""
        try:
            enhanced_context = {
                **context,
                "agent_type": "time_tracking",
                "capabilities": ["time_logging", "productivity_analysis", "timesheet_generation"]
            }
            
            response = await self.agent.run(message, context=enhanced_context)
            validated_response = output_validation_guardrail(response)
            
            return {
                "agent": "TimeTracker",
                "response": validated_response.message if hasattr(validated_response, 'message') else str(validated_response),
                "success": validated_response.success if hasattr(validated_response, 'success') else True,
                "data": validated_response.data if hasattr(validated_response, 'data') else None
            }
            
        except Exception as e:
            return {
                "agent": "TimeTracker",
                "response": f"❌ Error processing request: {str(e)}",
                "success": False
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": "TimeTracker",
            "description": "Time and productivity management specialist",
            "capabilities": [
                "Log time entries for projects",
                "Generate timesheets and reports",
                "Track billable vs non-billable hours",
                "Analyze productivity patterns",
                "Validate time entry compliance"
            ],
            "tools": ["create_time_entry", "get_timesheet"]
        }