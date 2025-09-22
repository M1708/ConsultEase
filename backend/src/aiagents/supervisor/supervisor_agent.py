"""
Supervisor Agent for coordinating complex multi-agent tasks.
Handles task decomposition, agent coordination, and workflow management.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.aiagents.memory.conversation_memory import ConversationMemoryManager
from src.aiagents.memory.context_manager import ContextManager
from src.aiagents.graph.state import AgentState, update_state_for_handoff


class SupervisorAgent:
    """
    Supervisor agent that coordinates complex tasks across multiple specialized agents.
    """
    
    def __init__(self):
        self.memory_manager = ConversationMemoryManager()
        self.context_manager = ContextManager()
        self.instructions = self._get_system_instructions()
        self.tools = self._get_tool_schemas()
    
    def _get_system_instructions(self) -> str:
        """Get system instructions for the supervisor agent"""
        return f"""You are Core, the Supervisor Agent for a consulting management system.
        Current date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        CORE RESPONSIBILITIES:
        - Coordinate complex tasks that require multiple specialized agents
        - Decompose complex requests into manageable subtasks
        - Orchestrate agent handoffs and collaboration
        - Ensure task completion and quality control
        - Handle escalations and error recovery

        AVAILABLE SPECIALIZED AGENTS:
        - client_agent: Client management, company information, contact details
        - contract_agent: Contract management, agreements, terms, billing
        - employee_agent: Employee/contractor management, HR tasks
        - deliverable_agent: Project deliverables, milestones, task tracking
        - time_agent: Time tracking, timesheets, productivity management
        - user_agent: User accounts, profiles, permissions

        COORDINATION STRATEGIES:
        1. Sequential: Tasks that must be completed in order
        2. Parallel: Independent tasks that can run simultaneously
        3. Conditional: Tasks dependent on outcomes of other tasks
        4. Collaborative: Tasks requiring multiple agents working together

        TASK DECOMPOSITION PRINCIPLES:
        - Break complex requests into atomic, agent-specific tasks
        - Identify dependencies between subtasks
        - Determine optimal execution strategy (sequential/parallel)
        - Plan for error handling and recovery

        QUALITY CONTROL:
        - Validate outputs from specialized agents
        - Ensure task completion meets requirements
        - Handle conflicts between agent outputs
        - Provide comprehensive status updates

        COMMUNICATION STYLE:
        - Be clear and authoritative in coordination
        - Provide status updates on complex workflows
        - Explain the reasoning behind task decomposition
        - Keep users informed of progress and next steps
        """
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Define tool schemas for supervisor coordination"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "decompose_task",
                    "description": "Break down a complex task into subtasks for specialized agents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "main_task": {"type": "string", "description": "The main task to decompose"},
                            "subtasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "task_id": {"type": "string"},
                                        "description": {"type": "string"},
                                        "assigned_agent": {"type": "string"},
                                        "dependencies": {"type": "array", "items": {"type": "string"}},
                                        "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                                    }
                                }
                            },
                            "execution_strategy": {"type": "string", "enum": ["sequential", "parallel", "conditional"]}
                        },
                        "required": ["main_task", "subtasks", "execution_strategy"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "coordinate_agents",
                    "description": "Coordinate multiple agents for collaborative task execution",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "coordination_type": {"type": "string", "enum": ["handoff", "collaboration", "escalation"]},
                            "involved_agents": {"type": "array", "items": {"type": "string"}},
                            "coordination_plan": {"type": "string"},
                            "expected_outcome": {"type": "string"}
                        },
                        "required": ["coordination_type", "involved_agents", "coordination_plan"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_task_completion",
                    "description": "Validate that a task has been completed successfully",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "completion_status": {"type": "string", "enum": ["completed", "partial", "failed"]},
                            "validation_criteria": {"type": "array", "items": {"type": "string"}},
                            "quality_score": {"type": "number", "minimum": 0, "maximum": 10}
                        },
                        "required": ["task_id", "completion_status"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "escalate_issue",
                    "description": "Escalate an issue that requires human intervention",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "issue_type": {"type": "string", "enum": ["technical", "business", "permission", "data"]},
                            "description": {"type": "string"},
                            "affected_agents": {"type": "array", "items": {"type": "string"}},
                            "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "suggested_resolution": {"type": "string"}
                        },
                        "required": ["issue_type", "description", "urgency"]
                    }
                }
            }
        ]
    
    async def analyze_task_complexity(self, user_message: str, state: AgentState) -> Dict[str, Any]:
        """Analyze if a task requires supervisor coordination"""
        try:
            # Extract intent and entities
            intent_data = self.context_manager.extract_user_intent(user_message)
            
            # Determine complexity factors
            complexity_factors = {
                "multiple_entities": len(intent_data["entities"]) > 1,
                "complex_intent": intent_data["complexity"] == "complex",
                "high_urgency": intent_data["urgency"] == "high",
                "requires_coordination": any(word in user_message.lower() for word in [
                    "and", "then", "after", "before", "also", "plus", "along with"
                ]),
                "cross_domain": self._involves_multiple_domains(intent_data["entities"])
            }
            
            complexity_score = sum(complexity_factors.values())
            
            return {
                "requires_supervision": complexity_score >= 2,
                "complexity_score": complexity_score,
                "factors": complexity_factors,
                "recommended_strategy": self._recommend_strategy(complexity_factors)
            }
            
        except Exception as e:
            print(f"Error analyzing task complexity: {e}")
            return {
                "requires_supervision": False,
                "complexity_score": 0,
                "factors": {},
                "recommended_strategy": "single_agent"
            }
    
    def _involves_multiple_domains(self, entities: List[Dict]) -> bool:
        """Check if entities span multiple agent domains"""
        domains = set()
        domain_mapping = {
            "client": "client_domain",
            "contract": "contract_domain", 
            "employee": "employee_domain",
            "deliverable": "deliverable_domain",
            "time_entry": "time_domain",
            "user": "user_domain"
        }
        
        for entity in entities:
            entity_value = entity.get("value", "")
            for key, domain in domain_mapping.items():
                if key in entity_value:
                    domains.add(domain)
        
        return len(domains) > 1
    
    def _recommend_strategy(self, factors: Dict[str, bool]) -> str:
        """Recommend execution strategy based on complexity factors"""
        if factors.get("requires_coordination") and factors.get("multiple_entities"):
            return "sequential"
        elif factors.get("multiple_entities") and not factors.get("requires_coordination"):
            return "parallel"
        elif factors.get("complex_intent"):
            return "conditional"
        else:
            return "single_agent"
    
    async def create_coordination_plan(
        self, 
        user_message: str, 
        state: AgentState
    ) -> Dict[str, Any]:
        """Create a coordination plan for complex tasks"""
        try:
            # Analyze task complexity
            analysis = await self.analyze_task_complexity(user_message, state)
            
            if not analysis["requires_supervision"]:
                return {
                    "requires_coordination": False,
                    "recommended_agent": self._get_primary_agent(user_message)
                }
            
            # Create coordination plan
            plan = {
                "requires_coordination": True,
                "strategy": analysis["recommended_strategy"],
                "subtasks": self._decompose_into_subtasks(user_message, state),
                "execution_order": [],
                "dependencies": {},
                "estimated_duration": self._estimate_duration(analysis["complexity_score"])
            }
            
            return plan
            
        except Exception as e:
            print(f"Error creating coordination plan: {e}")
            return {
                "requires_coordination": False,
                "recommended_agent": "client_agent"
            }
    
    def _get_primary_agent(self, user_message: str) -> str:
        """Get the primary agent for simple tasks"""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["client", "company", "customer"]):
            return "client_agent"
        elif any(word in message_lower for word in ["contract", "agreement"]):
            return "contract_agent"
        elif any(word in message_lower for word in ["employee", "staff"]):
            return "employee_agent"
        elif any(word in message_lower for word in ["deliverable", "project"]):
            return "deliverable_agent"
        elif any(word in message_lower for word in ["time", "hours"]):
            return "time_agent"
        elif any(word in message_lower for word in ["user", "account"]):
            return "user_agent"
        else:
            return "client_agent"
    
    def _decompose_into_subtasks(self, user_message: str, state: AgentState) -> List[Dict]:
        """Decompose complex task into subtasks"""
        # This is a simplified decomposition - in a real implementation,
        # this would use more sophisticated NLP and task analysis
        subtasks = []
        
        # Example decomposition logic
        if "create client and contract" in user_message.lower():
            subtasks = [
                {
                    "task_id": "create_client",
                    "description": "Create new client record",
                    "assigned_agent": "client_agent",
                    "dependencies": [],
                    "priority": "high"
                },
                {
                    "task_id": "create_contract",
                    "description": "Create contract for the new client",
                    "assigned_agent": "contract_agent", 
                    "dependencies": ["create_client"],
                    "priority": "high"
                }
            ]
        
        return subtasks
    
    def _estimate_duration(self, complexity_score: int) -> str:
        """Estimate task duration based on complexity"""
        if complexity_score <= 2:
            return "1-2 minutes"
        elif complexity_score <= 4:
            return "3-5 minutes"
        else:
            return "5+ minutes"
    
    async def get_enhanced_instructions(self, state: AgentState) -> str:
        """Get enhanced instructions with current context"""
        try:
            context = await self.context_manager.get_enhanced_context(state, "supervisor_agent")
            
            enhanced_instructions = f"""{self.instructions}

CURRENT CONTEXT:
{context}

ACTIVE COORDINATION:
- Current agents involved: {', '.join(state.get('active_agents', []))}
- Collaboration mode: {'Yes' if state.get('collaboration_mode', False) else 'No'}
- Pending handoffs: {len(state.get('pending_handoffs', []))}

PERFORMANCE TRACKING:
- Recent response times: {state.get('agent_response_times', {})}
- Error count: {state.get('error_recovery', {}).get('error_count', 0)}
"""
            
            return enhanced_instructions
            
        except Exception as e:
            print(f"Error getting enhanced supervisor instructions: {e}")
            return self.instructions
