from agents import Agent
from typing import Dict, Any
from backend.src.aiagents.prompts import ContractAgentPrompts
from backend.src.aiagents.tools.contract_tools import (
    create_client_tool, search_clients_tool, analyze_contract_tool, ContractToolResult
)
from backend.src.aiagents.guardrails.input_guardrails import input_sanitization_guardrail
from backend.src.aiagents.guardrails.output_guardrails import output_validation_guardrail

class ContractAgent:
    def __init__(self):
        self.agent = Agent(
            name="ContractBot",
            instructions=ContractAgentPrompts.SYSTEM_INSTRUCTIONS,
            model="gpt-4o-mini",
            tools=[
                create_client_tool,
                search_clients_tool,
                analyze_contract_tool
            ],
            output_type=ContractToolResult,
            input_guardrails=[input_sanitization_guardrail]
        )
    
    async def process_message(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user message through ContractBot"""
        try:
            # Add context to message processing
            enhanced_context = {
                **context,
                "agent_type": "contract",
                "capabilities": ["client_management", "contract_analysis", "document_processing"]
            }
            
            # Process through OpenAI Agent
            response = await self.agent.run(message, context=enhanced_context)
            
            # Apply output guardrails
            validated_response = output_validation_guardrail(response)
            
            return {
                "agent": "ContractBot",
                "response": validated_response.message if hasattr(validated_response, 'message') else str(validated_response),
                "success": validated_response.success if hasattr(validated_response, 'success') else True,
                "data": validated_response.data if hasattr(validated_response, 'data') else None
            }
            
        except Exception as e:
            return {
                "agent": "ContractBot",
                "response": f"❌ Error processing request: {str(e)}",
                "success": False
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": "ContractBot",
            "description": "Client and contract management specialist",
            "capabilities": [
                "Create and manage client records",
                "Process contract documents",
                "Analyze contract terms and obligations",
                "Track contract renewals and deadlines",
                "Manage client relationships"
            ],
            "tools": ["create_client", "search_clients", "analyze_contract"]
        }