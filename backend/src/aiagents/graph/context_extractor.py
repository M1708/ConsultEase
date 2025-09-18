"""
Context extraction and saving mechanism for agent conversations.
This module processes agent responses and extracts context information to save to state['data'].
"""

import re
from typing import Dict, Any, Optional
from ..graph.state import AgentState


class ContextExtractor:
    """Extracts context from agent responses and user messages to maintain conversation state."""
    
    def __init__(self):
        self.client_patterns = [
            r"client['\"]?\s*:\s*['\"]?([^'\",\n]+)['\"]?",
            r"for\s+client\s+['\"]?([A-Z][a-zA-Z\s&]+(?:Corp|Inc|LLC|Ltd|Solutions|Technologies|Systems)?)(?=\s+(?:with|that|where|having)\b|\s*$)['\"]?",
            r"client\s+['\"]?([A-Z][a-zA-Z\s&]+(?:Corp|Inc|LLC|Ltd|Solutions|Technologies|Systems)?)['\"]?",
            r"contract\s+with\s+([A-Z][a-zA-Z\s&]+(?:Corp|Inc|LLC|Ltd|Solutions|Technologies|Systems)?)",
            r"for\s+([A-Z][a-zA-Z\s&]+(?:Corp|Inc|LLC|Ltd|Solutions|Technologies|Systems)?)(?:\s|$)",
            r"['\"]?([A-Z][a-zA-Z\s&]+(?:Corp|Inc|LLC|Ltd|Solutions|Technologies|Systems)?)['\"]?"
        ]

        # Exclude patterns that should not be considered client names
        self.client_exclude_patterns = [
            r"file\s+attached",
            r"document\s+attached",
            r"attachment",
            r"upload",
            r"update\s+client",
            r"create\s+client",
            r"delete\s+client"
        ]
        
        self.workflow_patterns = [
            r"workflow['\"]?\s*:\s*['\"]?(update|delete|create|upload)['\"]?",
            r"operation['\"]?\s*:\s*['\"]?(update|delete|create|upload)['\"]?",
            r"(update|delete|create|upload)\s+contract",
            r"(update|delete|create|upload)\s+client"
        ]
        
        self.contract_id_patterns = [
            r"contract_id['\"]?\s*:\s*['\"]?(\d+)['\"]?",
            r"contract\s+id['\"]?\s*:\s*['\"]?(\d+)['\"]?",
            r"id['\"]?\s*:\s*['\"]?(\d+)['\"]?",
            r"contract\s+(\d+)",
            r"^(\d+)$"  # Just a number
        ]
        
        # Note: Removed billing_date_patterns - let LLM handle date extraction for better flexibility
    
    def extract_context_from_user_message(self, user_message: str, existing_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract context from user message."""
        context = {}

        # Extract client name first to check for client switching
        client_name = self._extract_client_name(user_message)
        if client_name:
            context['current_client'] = client_name
            print(f"🔍 DEBUG: Extracted client name: {client_name}")
            
            # Check if client is switching - if so, clear contract ID from previous client
            if existing_state and 'current_client' in existing_state:
                previous_client = existing_state.get('current_client', '')
                if previous_client and previous_client.lower() != client_name.lower():
                    print(f"🔍 DEBUG: Client switching from '{previous_client}' to '{client_name}' - clearing contract ID")
                    context['current_contract_id'] = None  # Clear contract ID when switching clients

        # Extract contract ID only if no client switching occurred
        if not client_name or (existing_state and existing_state.get('current_client', '').lower() == client_name.lower()):
            contract_id = self._extract_contract_id(user_message)
            if contract_id:
                context['current_contract_id'] = contract_id

        # Extract workflow/operation
        workflow = self._extract_workflow(user_message)
        if workflow:
            context['current_workflow'] = workflow

        # Note: Removed billing date extraction - let LLM handle this for better flexibility

        # Check if this is a new operation request (not just a contract ID response)
        is_new_operation = self._is_new_operation_request(user_message)
        print(f"🔍 DEBUG: Is new operation request: {is_new_operation} for message: '{user_message}'")

        if is_new_operation:
            context['user_operation'] = self._extract_operation_type(user_message)
            context['original_user_request'] = user_message
            print(f"🔍 DEBUG: Detected new user operation: {context['user_operation']}")
        else:
            # If it's just a contract ID, check if we have a pending operation from previous context
            if contract_id and not is_new_operation:
                print(f"🔍 DEBUG: Contract ID provided without operation - will preserve existing operation context")
                # Don't extract user_operation, let the existing one be preserved
            else:
                print(f"🔍 DEBUG: Not a new operation request (skipping user_operation extraction)")

        return context
    
    def extract_context_from_agent_response(self, agent_response: str) -> Dict[str, Any]:
        """Extract context from agent response."""
        context = {}
        
        # Look for explicit context statements
        if "current_client" in agent_response.lower():
            client_match = re.search(r"current_client['\"]?\s*=\s*['\"]?([^'\",\n]+)['\"]?", agent_response)
            if client_match:
                context['current_client'] = client_match.group(1).strip()
        
        if "current_workflow" in agent_response.lower():
            workflow_match = re.search(r"current_workflow['\"]?\s*=\s*['\"]?(update|delete|create|upload)['\"]?", agent_response)
            if workflow_match:
                context['current_workflow'] = workflow_match.group(1).strip()
        
        if "current_contract_id" in agent_response.lower():
            contract_id_match = re.search(r"current_contract_id['\"]?\s*=\s*['\"]?(\d+)['\"]?", agent_response)
            if contract_id_match:
                context['current_contract_id'] = contract_id_match.group(1).strip()
        
        # CRITICAL: Do NOT extract user_operation or original_user_request from agent responses
        # These should only come from actual user messages
        
        return context
    
    def _extract_client_name(self, text: str) -> Optional[str]:
        """Extract client name from text."""
        print(f"🔍 DEBUG: _extract_client_name called with text: '{text}'")
        for i, pattern in enumerate(self.client_patterns):
            print(f"🔍 DEBUG: Trying pattern {i}: {pattern}")
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                client_name = match.group(1).strip()
                print(f"🔍 DEBUG: Pattern {i} matched: '{client_name}'")

                # Check exclude patterns first
                should_exclude = False
                for exclude_pattern in self.client_exclude_patterns:
                    if re.search(exclude_pattern, client_name, re.IGNORECASE):
                        should_exclude = True
                        print(f"🔍 DEBUG: Excluded by pattern: {exclude_pattern}")
                        break

                if should_exclude:
                    continue

                # Filter out common false positives and overly long matches
                if (client_name.lower() not in ['the', 'a', 'an', 'this', 'that', 'for', 'with', 'and', 'or']
                    and len(client_name) < 50  # Avoid overly long matches
                    and not client_name.lower().startswith(('update', 'delete', 'create', 'upload'))
                    and not client_name.lower().startswith(('the contract', 'contract with', 'contract id'))
                    and not client_name.lower().startswith('contract')):
                    return client_name
        return None
    
    def _extract_workflow(self, text: str) -> Optional[str]:
        """Extract workflow/operation from text."""
        for pattern in self.workflow_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().lower()
        return None
    
    def _extract_contract_id(self, text: str) -> Optional[str]:
        """Extract contract ID from text."""
        print(f"🔍 DEBUG: Extracting contract ID from: '{text}'")
        
        # Skip extraction if the text contains "contract with [client]" pattern
        # This prevents false matches like "contract with InnovateTech Solutions"
        if re.search(r'contract\s+with\s+[a-zA-Z]', text, re.IGNORECASE):
            print(f"🔍 DEBUG: Skipping contract ID extraction - detected 'contract with [client]' pattern")
            return None
        
        for i, pattern in enumerate(self.contract_id_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted_id = match.group(1).strip()
                print(f"🔍 DEBUG: Pattern {i} matched: '{pattern}' -> extracted: '{extracted_id}'")
                return extracted_id
        print(f"🔍 DEBUG: No contract ID patterns matched")
        return None
    
    def _is_new_operation_request(self, text: str) -> bool:
        """Check if this is a new operation request (not just a contract ID response)."""
        text_lower = text.lower().strip()
        
        # Skip tool results and agent responses
        if (text_lower.startswith("tool '") or 
            text_lower.startswith("previous tool result:") or
            "result:" in text_lower and "success" in text_lower):
            return False
        
        # If it's just a number, it's likely a contract ID response
        if text_lower.isdigit():
            return False
        
        # If it contains operation keywords, it's a new request
        operation_keywords = ['update', 'delete', 'create', 'upload', 'show', 'get', 'list']
        return any(keyword in text_lower for keyword in operation_keywords)
    
    def _extract_operation_type(self, text: str) -> str:
        """Extract the specific tool operation from the user message."""
        text_lower = text.lower()
        
        # Contract operations
        if 'update' in text_lower and 'contract' in text_lower:
            return 'update_contract'
        elif 'delete' in text_lower and 'contract' in text_lower:
            return 'delete_contract'
        elif 'create' in text_lower and 'contract' in text_lower:
            return 'create_contract'
        elif 'upload' in text_lower and 'contract' in text_lower:
            return 'upload_contract_document'
        elif ('show' in text_lower or 'get' in text_lower or 'list' in text_lower) and 'contract' in text_lower:
            return 'get_contracts_by_client'
        
        # Client operations
        elif 'update' in text_lower and 'client' in text_lower:
            return 'update_client'
        elif 'create' in text_lower and 'client' in text_lower:
            return 'create_client'
        elif ('show' in text_lower or 'get' in text_lower or 'list' in text_lower) and 'client' in text_lower:
            return 'get_client_details'
        
        # Fallback to generic operations
        elif 'update' in text_lower:
            return 'update'
        elif 'delete' in text_lower:
            return 'delete'
        elif 'create' in text_lower:
            return 'create'
        elif 'upload' in text_lower:
            return 'upload'
        elif 'show' in text_lower or 'get' in text_lower or 'list' in text_lower:
            return 'show'
        else:
            return 'unknown'
    
    
    def update_state_with_context(self, state: AgentState, context: Dict[str, Any]) -> AgentState:
        """Update state with extracted context."""
        print(f"🔍 DEBUG: update_state_with_context called with context: {context}")
        print(f"🔍 DEBUG: Current state data before update: {state.get('data', {})}")
        
        if not context:
            print(f"🔍 DEBUG: No context provided, returning state unchanged")
            return state
        
        # Initialize data if it doesn't exist
        if 'data' not in state:
            state['data'] = {}
            print(f"🔍 DEBUG: Initialized empty data in state")
        
        # Update state with context
        for key, value in context.items():
            # Special handling for user operation - only update if it's a new operation
            if key == 'user_operation':
                # Always update user_operation if it's provided in context
                state['data'][key] = value
                print(f"🔍 DEBUG: Updated user operation: {value}")
            elif key == 'original_user_request':
                # Always update original_user_request if it's provided in context
                state['data'][key] = value
                print(f"🔍 DEBUG: Updated original user request: {value}")
            else:
                # For other context (client, contract_id, workflow), always update
                # Special handling for contract_id - if None, remove it from state
                if key == 'current_contract_id' and value is None:
                    if 'current_contract_id' in state['data']:
                        del state['data']['current_contract_id']
                        print(f"🔍 DEBUG: Cleared contract ID due to client switching")
                else:
                    state['data'][key] = value
                    print(f"🔍 DEBUG: Saved context {key} = {value}")
        
        # Preserve existing user_operation if not provided in new context
        if 'user_operation' not in context and 'user_operation' in state['data']:
            print(f"🔍 DEBUG: Preserving existing user operation: {state['data']['user_operation']}")
        elif 'user_operation' not in context:
            print(f"🔍 DEBUG: No user_operation in context and none in state to preserve")
        else:
            print(f"🔍 DEBUG: user_operation provided in context: {context['user_operation']}")
        
        # Preserve existing original_user_request if not provided in new context
        if 'original_user_request' not in context and 'original_user_request' in state['data']:
            print(f"🔍 DEBUG: Preserving existing original user request: {state['data']['original_user_request']}")
        elif 'original_user_request' not in context:
            print(f"🔍 DEBUG: No original_user_request in context and none in state to preserve")
        else:
            print(f"🔍 DEBUG: original_user_request provided in context: {context['original_user_request']}")
        
        print(f"🔍 DEBUG: Final state data after update: {state.get('data', {})}")
        return state
    
    def get_context_for_tool_call(self, state: AgentState, tool_name: str) -> Dict[str, Any]:
        """Get relevant context for a tool call."""
        context = {}
        
        if 'data' in state:
            data = state['data']
            
            # For contract operations, include client and workflow context
            if 'contract' in tool_name.lower():
                if 'current_client' in data:
                    context['current_client'] = data['current_client']
                if 'current_workflow' in data:
                    context['current_workflow'] = data['current_workflow']
                if 'current_contract_id' in data:
                    context['current_contract_id'] = data['current_contract_id']
        
        return context


# Global instance
context_extractor = ContextExtractor()
