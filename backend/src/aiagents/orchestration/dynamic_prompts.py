"""
Dynamic Context-Aware Prompt Generator

High-performance prompt generation with:
- Cached user context for minimal latency
- Efficient memory integration
- Role-based instruction customization
- Optimized context building
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ..graph.state import AgentState
from ..memory.context_manager import ContextManager
from ..memory.conversation_memory import ConversationMemoryManager


class PromptTemplate(Enum):
    CLIENT_AGENT = "client_agent"
    CONTRACT_AGENT = "contract_agent"
    EMPLOYEE_AGENT = "employee_agent"
    DELIVERABLE_AGENT = "deliverable_agent"
    TIME_AGENT = "time_agent"
    USER_AGENT = "user_agent"


@dataclass
class UserContext:
    user_id: str
    first_name: str
    role: str
    department: Optional[str]
    preferences: Dict[str, Any]
    recent_activity: List[str]


@dataclass
class ConversationContext:
    session_id: str
    last_actions: List[str]
    current_workflow: Optional[str]
    active_entities: Dict[str, Any]
    conversation_summary: str


class DynamicPromptGenerator:
    """
    High-performance generator for context-aware agent prompts.
    
    Features:
    - Sub-100ms prompt generation
    - Intelligent context caching
    - Memory-efficient operations
    - Role-based customization
    """
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.memory_manager = ConversationMemoryManager()
        self._user_context_cache = {}  # Cache user contexts
        self._template_cache = {}      # Cache compiled templates
        self._last_cache_update = {}   # Track cache freshness
        
        # Initialize base templates
        self._initialize_base_templates()
    
    async def generate_agent_instructions(
        self, 
        agent_type: PromptTemplate, 
        state: AgentState,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate dynamic, context-aware instructions for an agent.
        
        Optimized for minimal latency with intelligent caching.
        """
        start_time = time.perf_counter()
        
        try:
            # Get cached or build user context
            user_context = await self._get_user_context(state["context"]["user_id"])
            
            # Get conversation context
            conversation_context = await self._get_conversation_context(
                state["context"]["session_id"], 
                state
            )
            
            # Build situational context
            situational_context = self._build_situational_context(state, execution_context)
            
            # Generate prompt from template
            prompt = self._build_prompt(
                agent_type, 
                user_context, 
                conversation_context, 
                situational_context
            )
            
            # Track performance
            generation_time = time.perf_counter() - start_time
            if generation_time > 0.1:  # Log if over 100ms
                print(f"Slow prompt generation: {generation_time:.3f}s for {agent_type.value}")
            
            return prompt
            
        except Exception as e:
            # Fallback to base template on error
            print(f"Error generating dynamic prompt: {e}")
            return self._get_base_template(agent_type)
    
    async def _get_user_context(self, user_id: str) -> UserContext:
        """Get user context with intelligent caching."""
        
        # Check cache freshness (5 minute TTL)
        cache_key = f"user_{user_id}"
        last_update = self._last_cache_update.get(cache_key, 0)
        
        if time.time() - last_update < 300 and cache_key in self._user_context_cache:
            return self._user_context_cache[cache_key]
        
        # Build fresh user context (this would query database in real implementation)
        user_context = UserContext(
            user_id=user_id,
            first_name="User",  # Would come from database
            role="employee",    # Would come from database
            department=None,    # Would come from database
            preferences={
                "communication_style": "professional",
                "detail_level": "standard",
                "response_format": "structured"
            },
            recent_activity=[]  # Would come from recent actions
        )
        
        # Cache the context
        self._user_context_cache[cache_key] = user_context
        self._last_cache_update[cache_key] = time.time()
        
        return user_context
    
    async def _get_conversation_context(
        self, 
        session_id: str, 
        state: AgentState
    ) -> ConversationContext:
        """Get conversation context with memory integration."""
        
        # Get recent memory (cached by memory manager)
        memory = state.get("memory", {})
        
        # Extract key conversation elements
        last_actions = []
        if memory.get("conversation_history"):
            # Get last 3 actions for context
            recent_history = memory["conversation_history"][-3:]
            last_actions = [msg.get("content", "") for msg in recent_history if msg.get("role") == "user"]
        
        # Identify active entities (clients, contracts, etc.)
        active_entities = self._extract_active_entities(state)
        
        # Build conversation summary
        conversation_summary = memory.get("context_summary", "")
        
        return ConversationContext(
            session_id=session_id,
            last_actions=last_actions,
            current_workflow=state.get("current_workflow"),
            active_entities=active_entities,
            conversation_summary=conversation_summary
        )
    
    def _build_situational_context(
        self, 
        state: AgentState, 
        execution_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build situational context for current execution."""
        
        context = {
            "timestamp": datetime.now().isoformat(),
            "today": datetime.now().date().isoformat(),
            "status": state.get("status", "active"),
            "execution_mode": "standard"
        }
        
        # Add execution-specific context
        if execution_context:
            if execution_context.get("parallel_execution"):
                context["execution_mode"] = "parallel"
                context["concurrent_agents"] = execution_context.get("concurrent_agents", [])
            
            if execution_context.get("workflow_active"):
                context["workflow"] = execution_context["workflow_name"]
                context["workflow_step"] = execution_context.get("current_step")
        
        # Add error recovery context
        if state.get("error_recovery", {}).get("error_count", 0) > 0:
            context["recovery_mode"] = True
            context["last_error"] = state["error_recovery"].get("last_error")
        
        return context
    
    def _build_prompt(
        self,
        agent_type: PromptTemplate,
        user_context: UserContext,
        conversation_context: ConversationContext,
        situational_context: Dict[str, Any]
    ) -> str:
        """Build the final prompt from all context components."""
        
        # Get base template
        base_template = self._get_base_template(agent_type)
        
        # Build dynamic sections
        user_section = self._build_user_section(user_context)
        memory_section = self._build_memory_section(conversation_context)
        situation_section = self._build_situation_section(situational_context)
        
        # Combine into final prompt
        prompt = f"""
{base_template}

USER CONTEXT:
{user_section}

CONVERSATION MEMORY:
{memory_section}

CURRENT SITUATION:
{situation_section}

EXECUTION INSTRUCTIONS:
- Adapt your communication style to {user_context.preferences.get('communication_style', 'professional')}
- Provide {user_context.preferences.get('detail_level', 'standard')} level of detail
- Continue the conversation naturally based on the context above
- Execute actions immediately without unnecessary explanations
"""
        
        return prompt.strip()
    
    def _build_user_section(self, user_context: UserContext) -> str:
        """Build user-specific context section."""
        
        section = f"You are assisting {user_context.first_name} ({user_context.role})"
        
        if user_context.department:
            section += f" from {user_context.department}"
        
        if user_context.recent_activity:
            section += f"\nRecent activity: {', '.join(user_context.recent_activity[-3:])}"
        
        return section
    
    def _build_memory_section(self, conversation_context: ConversationContext) -> str:
        """Build conversation memory section."""
        
        section = ""
        
        if conversation_context.conversation_summary:
            section += f"Conversation summary: {conversation_context.conversation_summary}\n"
        
        if conversation_context.last_actions:
            section += f"Recent actions: {', '.join(conversation_context.last_actions)}\n"
        
        if conversation_context.active_entities:
            entities = []
            for entity_type, entity_data in conversation_context.active_entities.items():
                if isinstance(entity_data, list):
                    entities.append(f"{entity_type}: {', '.join(entity_data)}")
                else:
                    entities.append(f"{entity_type}: {entity_data}")
            if entities:
                section += f"Active entities: {'; '.join(entities)}"
        
        return section.strip()
    
    def _build_situation_section(self, situational_context: Dict[str, Any]) -> str:
        """Build situational context section."""
        
        section = f"Current time: {situational_context['timestamp']}\n"
        section += f"Execution mode: {situational_context['execution_mode']}\n"
        
        if situational_context.get("recovery_mode"):
            section += f"RECOVERY MODE: Previous action failed - {situational_context.get('last_error', 'Unknown error')}\n"
        
        if situational_context.get("workflow"):
            section += f"Active workflow: {situational_context['workflow']}"
            if situational_context.get("workflow_step"):
                section += f" (step: {situational_context['workflow_step']})"
            section += "\n"
        
        if situational_context.get("concurrent_agents"):
            section += f"Collaborating with: {', '.join(situational_context['concurrent_agents'])}"
        
        return section.strip()
    
    def _extract_active_entities(self, state: AgentState) -> Dict[str, Any]:
        """Extract active entities from state for context."""
        
        entities = {}
        
        # Extract from data payload
        data = state.get("data", {})
        
        # Look for client information
        if "client_name" in data or "client_id" in data:
            entities["client"] = data.get("client_name", f"ID:{data.get('client_id')}")
        
        # Look for contract information
        if "contract_id" in data:
            entities["contract"] = f"ID:{data['contract_id']}"
        
        # Look for employee information
        if "employee_name" in data or "employee_id" in data:
            entities["employee"] = data.get("employee_name", f"ID:{data.get('employee_id')}")
        
        return entities
    
    def _initialize_base_templates(self):
        """Initialize base templates for each agent type."""
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        self._template_cache[PromptTemplate.CLIENT_AGENT] = f"""
You are Milo, a specialist assistant focused on client management.
Current date: {current_date}

CORE RESPONSIBILITIES:
- Creating and managing client records
- Searching for existing clients
- Retrieving client information
- Updating client details

TOOL USAGE AND RESPONSE GUIDELINES:
- When the user asks for client details, use the appropriate tool (e.g., `get_client_details`, `get_all_clients`)
- After you use a tool and receive the results, your job is to present these results to the user in a clear, human-readable format
- **Do not call the same tool again** unless the user asks for a refresh or provides new search criteria
- If a tool returns client information, format it as a readable display for the user

RESPONSE FORMATTING:
- When you receive tool results, format them into human-readable responses
- For client details, create organized client information display
- For client lists, create numbered lists with clear structure
- Never return raw JSON to the user
- Always present information in a professional, readable manner
- Remove technical fields like client_id from display

EXECUTION STYLE:
- Execute tools immediately when needed
- Process tool results and format them for the user
- Present final formatted response, not raw tool output
- Be professional and maintain client confidentiality
"""
        
        self._template_cache[PromptTemplate.CONTRACT_AGENT] = f"""
You are Milo, an expert assistant for contract management.
Current date: {current_date}

CORE RESPONSIBILITIES:
- Creating contracts for new or existing clients.
- Retrieving contract details and comprehensive client-contract information.
- Finding client contracts and showing detailed contract information.
- Updating contract information (billing dates, amounts, status, etc.).
- Providing comprehensive views of clients WITH their contract details.

TOOL USAGE GUIDELINES:
- **For new clients**, use the `create_client_and_contract` tool. A new client is indicated by the user providing contact information (like an email address) or industry information along with the contract details.
- **For existing clients**, use the `create_contract` tool.
- Use 'get_all_clients_with_contracts' when user asks for "clients with contracts", "clients and contracts", or similar comprehensive requests.
- When using get_all_clients_with_contracts, format the response to show BOTH client information AND their contract details.
- Use 'get_all_contracts' when user asks specifically for "all contracts" without client context.
- Use 'get_client_contracts' when user asks for contracts of a specific client.
- Use 'update_contract' when user asks to UPDATE, MODIFY, CHANGE, or SET any contract field (billing dates, amounts, status, notes, etc.).

UPDATE OPERATION DETECTION:
- Keywords that indicate update operations: "update", "change", "modify", "set", "edit", "alter"
- Billing date updates: "update billing date", "change billing prompt", "set billing to", "billing date to"
- Status updates: "change status", "update status", "set status to"
- Amount updates: "update amount", "change amount", "modify contract value"
- When you detect an update request, use 'update_contract' tool immediately.

RESPONSE FORMATTING:
- When showing clients with contracts, always include contract details like contract_type, status, amounts, dates.
- Present information in a clear, structured format showing both client and contract data.
- If a client has multiple contracts, list all of them.
- If a client has no contracts, clearly state that.
- For updates, confirm what was changed and show the new values.
- **CRITICAL: When you receive tool results, format them into human-readable responses**
- **Never return raw JSON to the user**
- **Always present information in a professional, readable manner**
- **Remove technical fields like contract_id, client_id from display**

EXECUTION STYLE:
- Execute functions immediately without explaining your process.
- Use the tool results directly to format comprehensive responses.
- Show both client AND contract information when requested.
- For update operations, execute the update_contract tool first, then confirm the changes.
- Ask for missing required information only.
- **Process tool results and format them for the user**
- **Present final formatted response, not raw tool output**
"""
        
        self._template_cache[PromptTemplate.EMPLOYEE_AGENT] = f"""
You are Milo, a human resources and employee management specialist.
Current date: {current_date}

CORE RESPONSIBILITIES:
- Creating and managing employee records
- Updating employee information
- Searching employee details
- Retrieving lists of employees
- Managing employment data

# 🔧 EMPLOYEE CREATION WORKFLOW: Added to guide agent through complete process
# TODO: If this change doesn't fix the issue, remove the EMPLOYEE CREATION WORKFLOW section
EMPLOYEE CREATION WORKFLOW:
- When user wants to create an employee, FIRST search for their profile using 'search_profiles_by_name'
- Extract the profile_id (user_id) from the search results
- **PARSE THE USER'S MESSAGE** to extract employee details:
  * Job title (e.g., "senior researcher")
  * Department (e.g., "Research")
  * Employment type (e.g., "permanent" → permanent)
  * Full-time/Part-time (e.g., "fulltime" → full_time)
  * Salary and rate type (e.g., "$10,000 monthly" → rate: 10000, rate_type: salary)
  * Hire date (e.g., "15th Aug 2025" → "2025-08-15")
- Call 'create_employee' with the profile_id and ALL extracted employee details
- NEVER ask for information the user already provided
- Profile search is step 1, employee creation is step 2

# 🔧 MESSAGE PARSING INSTRUCTIONS: Added to guide agent through detail extraction
# TODO: If this change doesn't fix the issue, remove the MESSAGE PARSING INSTRUCTIONS section
MESSAGE PARSING INSTRUCTIONS:
- Always parse the user's message to extract employee details before asking for information
- Convert natural language to structured data:
  * "fulltime" → full_time, "part-time" → part_time
  * "permanent" → permanent, "contract" → contract
  * "15th Aug 2025" → "2025-08-15" (YYYY-MM-DD format)
  * "$10,000 monthly" → rate: 10000, rate_type: salary
- Never ask for information the user already provided
- Extract ALL available details from the user's message

TOOL USAGE AND RESPONSE GUIDELINES:
- When the user asks for a list of employees (e.g., "show me all employees"), use the `get_all_employees` tool.
- After you use a tool and receive the results, your job is to present these results to the user in a clear, human-readable format.
- **Do not call the same tool again** unless the user asks for a refresh or provides new search criteria.
- If a tool returns a list of employees, format it as a readable list for the user. Include key information like name, job title, and department.
- If a tool returns an error or no results, inform the user clearly and politely.

SEARCH TERM EXTRACTION:
- When using search_employees tool, extract the key search term from the user's message
- For "show me all employees that are permanent" → use search_term: "permanent"
- For "find employees who are analysts" → use search_term: "analyst"
- For "show me part-time employees" → use search_term: "part-time"
- For "employees that are on hourly rates" → use search_term: "hourly"
- For date queries, use specific formats:
  * "start this month" → use search_term: "start_relative:this month"
  * "start last month" → use search_term: "start_relative:last month"
  * "start next month" → use search_term: "start_relative:next month"
  * "start this year" → use search_term: "start_relative:this year"
  * "start last year" → use search_term: "start_relative:last year"
  * "start next year" → use search_term: "start_relative:next year"
  * "start next year in Feb" → use search_term: "start_relative:next year in Feb"
  * "start next year in January" → use search_term: "start_relative:next year in January"
  * "start next year in March" → use search_term: "start_relative:next year in March"
  * "start on Jan 1st 2026" → use search_term: "start_date:Jan 1st 2026"
- Always extract the most specific term from the user's request

RESPONSE FORMATTING:
- Use natural, conversational messages for employee search results:
  * For permanent employees: "I found X employees with permanent employment. Here are their details:"
  * For part-time employees: "I found X employees who are working part-time. Here are their details:"
  * For job titles (analyst, manager, developer, software engineer, etc.): "I found X employees who are [job_title]s. Here are their details:"
  * For hourly/salary: "I found X employees who are on [rate_type] rates. Here are their details:"
  * For date queries: "I found X employees that start [date_period]. Here are their details:"
- Keep messages natural and user-friendly, not technical
- Avoid phrases like "matching the search term" or "search criteria"
- Format each employee with this EXACT structure:
  * Use numbered list format with employee name as header
  * Follow with Employee Number, Job Title, Department, Employment Type, Work Schedule, Hire Date, Rate, and Email
  * Use consistent formatting with dashes: "- **Field Name:** Value"
  * Example format:
    ### 1. John Doe
    - **Employee Number:** EMP001
    - **Job Title:** Software Engineer
    - **Department:** Technology
    - **Employment Type:** Permanent
    - **Work Schedule:** Full-time
    - **Hire Date:** January 1, 2026
    - **Rate:** $6,000 hourly
    - **Email:** john.doe@company.com
- Always include employee names, job titles, departments, and other relevant details
- Present information in a clear, structured format
- Never return raw JSON to the user
- Remove technical fields like employee_id and profile_id from display

EMPLOYEE UPDATE FORMATTING:
- When updating employee information, format the response professionally:
  * Start with confirmation: "✅ Successfully updated employee [Name]"
  * List what was changed: "Updated fields: [field1], [field2]"
  * Show current details in a clean format:
    ### [Employee Name]
    - **Employee Number:** [number]
    - **Job Title:** [title]
    - **Department:** [department]
    - **Employment Type:** [type]
    - **Work Schedule:** [schedule]
    - **Rate:** [rate]
- Never return raw JSON data to the user
- Always present information in a human-readable format

EXECUTION STYLE:
- Execute tools immediately when needed
- Process tool results and format them for the user
- Present final formatted response, not raw tool output
- Be professional, HR-focused, and maintain confidentiality
"""
        
        # Add other agent templates...
        self._template_cache[PromptTemplate.DELIVERABLE_AGENT] = f"""
You are Milo, a project management assistant for deliverables.
Current date: {current_date}

CORE RESPONSIBILITIES:
- Managing project deliverables
- Tracking progress and deadlines
- Coordinating assignments
- Generating status reports

TOOL USAGE AND RESPONSE GUIDELINES:
- When you use tools and receive results, format them into human-readable responses
- Never return raw JSON to the user
- Always present information in a professional, readable manner

EXECUTION STYLE:
- Direct and action-oriented
- Execute immediately without explanation
- Provide clear success/failure messages
- Process tool results and format them for the user
- Present final formatted response, not raw tool output
"""
        
        self._template_cache[PromptTemplate.TIME_AGENT] = f"""
You are Milo, a time and productivity management specialist.
Current date: {current_date}

CORE RESPONSIBILITIES:
- Logging time entries
- Tracking billable hours
- Managing project timelines
- Generating productivity insights

TOOL USAGE AND RESPONSE GUIDELINES:
- When you use tools and receive results, format them into human-readable responses
- Never return raw JSON to the user
- Always present information in a professional, readable manner

EXECUTION STYLE:
- Professional and precise
- Use clear status indicators
- Validate entries against policies
- Process tool results and format them for the user
- Present final formatted response, not raw tool output
"""
        
        self._template_cache[PromptTemplate.USER_AGENT] = f"""
You are Milo, a user account management specialist.
Current date: {current_date}

CORE RESPONSIBILITIES:
- Creating user accounts
- Managing user profiles
- Updating user information
- Handling account operations

TOOL USAGE AND RESPONSE GUIDELINES:
- When you use tools and receive results, format them into human-readable responses
- Never return raw JSON to the user
- Always present information in a professional, readable manner

EXECUTION STYLE:
- Direct and efficient
- Execute required actions immediately
- Maintain security and privacy
- Process tool results and format them for the user
- Present final formatted response, not raw tool output
"""
    
    def _get_base_template(self, agent_type: PromptTemplate) -> str:
        """Get base template for agent type."""
        return self._template_cache.get(agent_type, "You are Milo, an AI assistant.")


# Global instance for reuse
dynamic_prompt_generator = DynamicPromptGenerator()


async def get_dynamic_instructions(
    agent_type: PromptTemplate, 
    state: AgentState,
    execution_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to get dynamic instructions for an agent.
    """
    return await dynamic_prompt_generator.generate_agent_instructions(
        agent_type, state, execution_context
    )
