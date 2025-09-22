"""
Enhanced Routing Logic for Intelligent Agent Assignment

This module provides improved routing logic to ensure requests are correctly
classified and routed to the appropriate specialized agent.
"""

from typing import Dict, List, Tuple, Any
import re


class EnhancedRoutingLogic:
    """
    Enhanced routing logic that uses context-aware classification
    to determine the correct agent for each request.
    """
    
    def __init__(self):
        # Define comprehensive keyword mappings for each agent
        self.agent_keywords = {
            "employee_agent": {
                "primary": [
                    "employee", "staff", "personnel", "worker", "contractor",
                    "hire", "hiring", "onboard", "onboarding", "recruit",
                    "employee_number", "emp_number", "staff_id", "personnel_id",
                    "job_title", "position", "role", "department_assignment",
                    "salary", "wage", "hourly_rate", "compensation",
                    "full_time", "part_time", "fulltime", "parttime",
                    "permanent", "temporary", "contract_worker", "consultant",
                    "hr", "human_resources", "payroll", "benefits"
                ],
                "patterns": [
                    r"employee\s+(?:number|id|code)",
                    r"emp\s*\d+",
                    r"staff\s+(?:member|id|number)",
                    r"hire\s+(?:date|new)",
                    r"job\s+title",
                    r"employment\s+type",
                    r"work\s+schedule",
                    r"salary\s+(?:is|of|amount)",
                    r"hourly\s+rate",
                    r"department\s+(?:assignment|transfer)"
                ],
                "context_indicators": [
                    "works in", "employed by", "hired on", "salary is",
                    "job title", "department", "full-time", "part-time",
                    "contractor", "permanent employee", "staff member"
                ]
            },
            
            "client_agent": {
                "primary": [
                    "client", "customer", "company", "business", "organization",
                    "contact_person", "primary_contact", "client_contact",
                    "industry", "company_size", "business_type",
                    "client_name", "company_name", "organization_name",
                    "contact_email", "contact_phone", "business_address"
                ],
                "patterns": [
                    r"client\s+(?:name|company|contact)",
                    r"company\s+(?:name|size|industry)",
                    r"primary\s+contact",
                    r"contact\s+(?:person|email|phone)",
                    r"business\s+(?:name|type|industry)"
                ],
                "context_indicators": [
                    "client company", "business client", "customer company",
                    "contact person", "primary contact", "client contact"
                ]
            },
            
            "contract_agent": {
                "primary": [
                    "contract", "agreement", "deal", "terms", "billing",
                    "contract_type", "contract_amount", "billing_frequency",
                    "start_date", "end_date", "renewal", "termination",
                    "fixed_price", "hourly_contract", "retainer",
                    "billing_prompt", "invoice", "payment_terms"
                ],
                "patterns": [
                    r"contract\s+(?:id|number|type|amount)",
                    r"billing\s+(?:date|frequency|prompt)",
                    r"agreement\s+(?:terms|type|amount)",
                    r"contract\s+for\s+(?:client|company)",
                    r"fixed\s+(?:price|amount)",
                    r"hourly\s+(?:contract|rate|billing)"
                ],
                "context_indicators": [
                    "contract terms", "billing schedule", "payment terms",
                    "contract renewal", "agreement details", "contract amount"
                ]
            },
            
            "deliverable_agent": {
                "primary": [
                    "deliverable", "project", "milestone", "task", "assignment",
                    "project_deliverable", "work_item", "output", "result",
                    "completion", "deadline", "due_date", "progress"
                ],
                "patterns": [
                    r"project\s+(?:deliverable|milestone|task)",
                    r"deliverable\s+(?:for|due|completion)",
                    r"milestone\s+(?:date|completion|progress)",
                    r"task\s+(?:assignment|completion|progress)"
                ],
                "context_indicators": [
                    "project milestone", "deliverable item", "task completion",
                    "project progress", "work deliverable"
                ]
            },
            
            "time_agent": {
                "primary": [
                    "time", "hours", "timesheet", "time_entry", "log_time",
                    "track_time", "time_tracking", "productivity", "billable_hours",
                    "work_hours", "overtime", "time_log", "hour_tracking"
                ],
                "patterns": [
                    r"log\s+(?:time|hours)",
                    r"track\s+(?:time|hours)",
                    r"time\s+(?:entry|tracking|log)",
                    r"billable\s+hours",
                    r"work\s+hours",
                    r"timesheet\s+(?:entry|update)"
                ],
                "context_indicators": [
                    "time tracking", "hour logging", "timesheet entry",
                    "billable time", "work time", "time management"
                ]
            },
            
            "user_agent": {
                "primary": [
                    "user", "account", "profile", "login", "password",
                    "permissions", "access", "role", "user_account",
                    "user_profile", "account_settings", "user_management"
                ],
                "patterns": [
                    r"user\s+(?:account|profile|permissions)",
                    r"account\s+(?:settings|management|access)",
                    r"login\s+(?:credentials|access)",
                    r"user\s+(?:role|permissions|access)"
                ],
                "context_indicators": [
                    "user account", "account settings", "user permissions",
                    "login access", "user management", "profile settings"
                ]
            }
        }
        
        # Define operation types and their priorities
        self.operation_types = {
            "create": ["create", "add", "new", "register", "onboard", "hire"],
            "update": ["update", "modify", "change", "edit", "set", "assign"],
            "retrieve": ["get", "show", "list", "find", "search", "retrieve", "display"],
            "delete": ["delete", "remove", "terminate", "deactivate"]
        }
    
    def classify_request(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify a user request to determine the appropriate agent.

        Args:
            user_message: The user's message
            context: Optional context from previous conversation state

        Returns:
            Dict containing agent_name, confidence, reasoning, and operation_type
        """
        print(f"🔍 ENHANCED ROUTING: classify_request called with user_message='{user_message}', context={context}")
        message_lower = user_message.lower()

        # EARLY special-case: explicit client details phrasing → client_agent
        if ("client" in message_lower) and (
            "show details" in message_lower or "client details" in message_lower or "details" in message_lower
        ):
            print("🔍 ENHANCED ROUTING: Early match for client details → client_agent")
            return {
                "agent_name": "client_agent",
                "confidence": "high",
                "reasoning": "Explicit client details phrasing",
                "operation_type": "retrieve",
                "scores": {"client_agent": 10.0, "contract_agent": 0.0, "employee_agent": 0.0}
            }

        # TODO: CONFIRMATION FIX - Step 0: Check for confirmation responses first
        if self._is_confirmation_response(user_message, context):
            current_agent = context.get('current_agent')
            if current_agent:
                print(f"🔍 ENHANCED ROUTING: Confirmation response detected, routing to {current_agent}")
                return {
                    "agent_name": current_agent,
                    "confidence": "high",
                    "reasoning": f"Confirmation response detected - routing to {current_agent}",
                    "operation_type": "confirmation",
                    "scores": {current_agent: 10.0, "client_agent": 0.0, "contract_agent": 0.0, "employee_agent": 0.0}
                }

        # Step 1: Identify operation type
        operation_type = self._identify_operation_type(message_lower)
        print(f"🔍 ENHANCED ROUTING: operation_type='{operation_type}'")

        # Special-case: client detail queries should go to client_agent
        if (
            ("client" in message_lower or "clients" in message_lower)
            and any(kw in message_lower for kw in ["show details", "details", "get details", "client details"]) 
        ):
            print("🔍 ENHANCED ROUTING: Detected client details request → routing to client_agent")
            return {
                "agent_name": "client_agent",
                "confidence": "high",
                "reasoning": "Detected client details request",
                "operation_type": "retrieve",
                "scores": {"client_agent": 10.0, "contract_agent": 0.0, "employee_agent": 0.0}
            }

        # Step 2: Check for contract operations (high priority)
        if any(keyword in user_message.lower() for keyword in ['create a new contract', 'create contract', 'new contract', 'contract for', 'billing', 'invoice']):
            print(f"🔍 ENHANCED ROUTING: Contract operation detected, routing to contract_agent")
            return {
                "agent_name": "contract_agent",
                "confidence": "high",
                "reasoning": "Contract operation detected - routing to contract agent",
                "operation_type": "create_contract",
                "scores": {"contract_agent": 10.0, "client_agent": 0.0, "employee_agent": 0.0}
            }
        
        # Step 3: Check for employee document uploads (special case)
        if self._is_employee_document_upload(user_message, context):
            print(f"🔍 ENHANCED ROUTING: Employee document upload detected, routing to employee_agent")
            return {
                "agent_name": "employee_agent",
                "confidence": "high",
                "reasoning": "Employee document upload detected - routing to employee agent",
                "operation_type": "upload_employee_document",
                "scores": {"employee_agent": 10.0, "client_agent": 0.0, "contract_agent": 0.0}
            }
        
        # Step 4: Check for contract ID responses (special case)
        if self._is_contract_id_response(user_message, context):
            print(f"🔍 ENHANCED ROUTING: Contract ID response detected, routing to contract_agent")
            return {
                "agent_name": "contract_agent",
                "confidence": "high",
                "reasoning": "Detected contract ID response - routing to contract agent",
                "operation_type": "contract_response",
                "scores": {"contract_agent": 10.0, "client_agent": 0.0, "employee_agent": 0.0}
            }
        
        # Step 4.5: Check for "all" responses to contract operations (special case)
        if self._is_all_response_to_contract_operation(user_message, context):
            print(f"🔍 ENHANCED ROUTING: 'All' response to contract operation detected, routing to contract_agent")
            return {
                "agent_name": "contract_agent",
                "confidence": "high",
                "reasoning": "Detected 'all' response to contract operation - routing to contract agent",
                "operation_type": "contract_all_response",
                "scores": {"contract_agent": 10.0, "client_agent": 0.0, "employee_agent": 0.0}
            }
        

        # Step 3: Score each agent based on keyword matches
        agent_scores = self._calculate_agent_scores(user_message, message_lower)

        # Step 4: Apply context-aware adjustments
        adjusted_scores = self._apply_context_adjustments(
            user_message, message_lower, agent_scores, operation_type
        )

        # Step 5: Determine the best agent
        best_agent, confidence = self._select_best_agent(adjusted_scores)

        # Step 6: Generate reasoning
        reasoning = self._generate_reasoning(
            best_agent, operation_type, adjusted_scores, user_message
        )

        return {
            "agent_name": best_agent,
            "confidence": confidence,
            "reasoning": reasoning,
            "operation_type": operation_type,
            "scores": adjusted_scores
        }
    
    def _identify_operation_type(self, message_lower: str) -> str:
        """Identify the type of operation being requested."""
        for op_type, keywords in self.operation_types.items():
            if any(keyword in message_lower for keyword in keywords):
                return op_type
        return "unknown"
    
    def _calculate_agent_scores(self, original_message: str, message_lower: str) -> Dict[str, float]:
        """Calculate initial scores for each agent based on keyword matches."""
        scores = {}
        
        for agent_name, keywords_data in self.agent_keywords.items():
            score = 0.0
            
            # Primary keyword matches (base score)
            primary_matches = sum(1 for keyword in keywords_data["primary"] 
                                if keyword in message_lower)
            score += primary_matches * 2.0
            
            # Pattern matches (higher weight)
            pattern_matches = sum(1 for pattern in keywords_data["patterns"]
                                if re.search(pattern, message_lower))
            score += pattern_matches * 3.0
            
            # Context indicator matches (medium weight)
            context_matches = sum(1 for indicator in keywords_data["context_indicators"]
                                if indicator in message_lower)
            score += context_matches * 2.5
            
            scores[agent_name] = score
        
        return scores
    
    def _apply_context_adjustments(
        self, 
        original_message: str, 
        message_lower: str, 
        base_scores: Dict[str, float],
        operation_type: str
    ) -> Dict[str, float]:
        """Apply context-aware adjustments to base scores."""
        adjusted_scores = base_scores.copy()
        
        # Adjustment 1: Employee-specific patterns
        if self._has_employee_context(message_lower):
            adjusted_scores["employee_agent"] += 5.0
            # Reduce client agent score if employee context is strong
            if adjusted_scores["employee_agent"] > adjusted_scores["client_agent"]:
                adjusted_scores["client_agent"] *= 0.5
        
        # Adjustment 1.5: Employee document operations - highest priority
        if (("delete" in message_lower or "upload" in message_lower) and 
            "document" in message_lower and 
            any(word in message_lower for word in ["employee", "staff", "worker", "personnel"])):
            # Employee document operations get highest priority
            adjusted_scores["employee_agent"] += 15.0
            adjusted_scores["contract_agent"] = 0.0
            adjusted_scores["client_agent"] = 0.0
        
        # Adjustment 2: Contract vs Client disambiguation
        if operation_type == "update" and any(word in message_lower for word in ["billing", "contract", "amount", "date"]):
            adjusted_scores["contract_agent"] += 3.0
        
        # Adjustment 3: Delete operations - route to contract agent for delete operations
        if operation_type == "delete":
            if "client" in message_lower and "delete" in message_lower:
                # Delete client operations should go to contract agent
                adjusted_scores["contract_agent"] += 10.0
                adjusted_scores["client_agent"] = 0.0
            elif "contract" in message_lower and "delete" in message_lower:
                # Delete contract operations should go to contract agent
                adjusted_scores["contract_agent"] += 10.0
                adjusted_scores["client_agent"] = 0.0
        
        # Adjustment 3.5: Contracts with documents - route to contract agent (unless it's employee document)
        if "contract" in message_lower and "document" in message_lower:
            # Check if this is an employee document operation first
            if not any(word in message_lower for word in ["employee", "staff", "worker", "personnel"]):
                # Only route to contract agent if it's NOT an employee document operation
                adjusted_scores["contract_agent"] += 10.0
                adjusted_scores["client_agent"] = 0.0
        
        # Adjustment 3.6: Contract queries with "all clients" - route to contract agent
        if ("contract" in message_lower and "all clients" in message_lower) or \
           ("contracts" in message_lower and "all clients" in message_lower):
            # Contract queries about all clients should go to contract agent
            adjusted_scores["contract_agent"] += 15.0
            adjusted_scores["client_agent"] = 0.0
        
        # Adjustment 4: Person name context (Agentic approach - let agent reason about context)
        person_names = self._extract_person_names(original_message)
        if person_names:
            # TODO: Make this more agentic - let the agent reason about person vs company context
            # Instead of hard-coded rules, provide contextual hints for agent reasoning
            if any(keyword in message_lower for keyword in ["employee_number", "emp", "staff", "hire", "salary"]):
                adjusted_scores["employee_agent"] += 4.0
            elif any(keyword in message_lower for keyword in ["client", "company", "contact", "business"]):
                adjusted_scores["client_agent"] += 4.0
        
        # Adjustment 4: Operation-specific boosts
        if operation_type == "create":
            # New employee creation often mentions job details
            if any(word in message_lower for word in ["job", "position", "department", "salary", "hire"]):
                adjusted_scores["employee_agent"] += 2.0
        
        # ENHANCEMENT: Multi-entity scenario handling
        # Adjustment 5: Complex client+contract creation scenarios
        if operation_type == "create" and self._has_multi_entity_context(message_lower, original_message):
            # If message contains both client and contract details, route to contract agent
            # The contract agent is responsible for checking if client exists and creating if needed
            if self._has_contract_creation_context(message_lower) and self._has_client_details_context(original_message):
                adjusted_scores["contract_agent"] += 8.0  # High boost for multi-entity scenarios
                # Reduce client agent score since contract agent will handle client creation if needed
                adjusted_scores["client_agent"] *= 0.3
        
        return adjusted_scores
    
    def _has_employee_context(self, message_lower: str) -> bool:
        """Check if the message has strong employee-related context."""
        # Basic employee patterns
        basic_patterns = [
            "employee", "staff", "personnel", "worker",
            "details for employee", "show details for", "employee details",
            "staff details", "personnel details"
        ]
        
        # Specific employee indicators
        specific_indicators = [
            "employee_number", "emp_number", "staff_id", "personnel_id",
            "job_title", "department", "salary", "wage", "hourly_rate",
            "full_time", "part_time", "employment_type", "hire_date",
            "contractor", "consultant", "permanent", "temporary"
        ]
        
        # Check both basic patterns and specific indicators
        return (any(pattern in message_lower for pattern in basic_patterns) or 
                any(indicator in message_lower for indicator in specific_indicators))
    
    def _extract_person_names(self, message: str) -> List[str]:
        """Extract person names from the message."""
        # Simple pattern for detecting person names (First Last)
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        matches = re.findall(name_pattern, message)
        
        # Filter out common false positives
        false_positives = ["New York", "Los Angeles", "San Francisco", "United States"]
        return [name for name in matches if name not in false_positives]
    
    
    def _has_multi_entity_context(self, message_lower: str, original_message: str) -> bool:
        """Check if the message involves multiple entities (client + contract)."""
        # Look for patterns that suggest both client and contract creation
        multi_entity_patterns = [
            "contract for",
            "create a contract for",
            "add a contract for",
            "new contract for",
            "contract with"
        ]
        
        return any(pattern in message_lower for pattern in multi_entity_patterns)
    
    def _has_contract_creation_context(self, message_lower: str) -> bool:
        """Check if the message has contract creation context."""
        contract_creation_indicators = [
            "contract", "agreement", "deal",
            "fixed price", "hourly rate", "retainer",
            "billing", "monthly", "worth",
            "starting", "starts", "begins"
        ]
        
        return any(indicator in message_lower for indicator in contract_creation_indicators)
    
    def _has_client_details_context(self, original_message: str) -> bool:
        """Check if the message contains client details (suggesting new client)."""
        # Look for email addresses (strong indicator of new client)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        if re.search(email_pattern, original_message):
            return True
        
        # Look for contact person patterns
        contact_patterns = [
            r'contact\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'with\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'[A-Z][a-z]+\s+[A-Z][a-z]+\s+at\s+',
            r'contact\s+.*@'
        ]
        
        if any(re.search(pattern, original_message) for pattern in contact_patterns):
            return True
        
        # Look for company details that suggest new client
        new_client_indicators = [
            "corp", "corporation", "company", "inc", "llc", "ltd",
            "startup", "tech", "solutions", "systems", "group"
        ]
        
        # Check if company name appears with contact details
        message_lower = original_message.lower()
        has_company = any(indicator in message_lower for indicator in new_client_indicators)
        has_contact_info = any(word in message_lower for word in ["contact", "email", "@", "phone"])
        
        return has_company and has_contact_info

    def _is_confirmation_response(self, user_message: str, context: Dict[str, Any] = None) -> bool:
        """Check if the user message is a confirmation response (yes/no)."""
        print(f"🔍 CONFIRMATION CHECK: user_message='{user_message}', context={context}")
        
        # Check for confirmation words
        confirmation_words = ['yes', 'no', 'y', 'n', 'ok', 'okay', 'confirm', 'cancel', 'proceed', 'go ahead', 'sure', 'alright']
        message_lower = user_message.lower().strip()
        
        print(f"🔍 CONFIRMATION CHECK: message_lower='{message_lower}', in confirmation_words={message_lower in confirmation_words}")
        
        if message_lower in confirmation_words:
            print(f"🔍 CONFIRMATION CHECK: Confirmation word detected: '{message_lower}'")
            # Check if we have an active workflow that needs confirmation
            current_workflow = context.get('current_workflow') if context else None
            user_operation = context.get('user_operation') if context else None
            
            print(f"🔍 CONFIRMATION CHECK: current_workflow='{current_workflow}', user_operation='{user_operation}'")
            
            # If we have an active workflow, this is likely a confirmation
            if current_workflow or user_operation:
                print(f"🔍 CONFIRMATION CHECK: Active workflow/operation found, returning True")
                return True
            else:
                print(f"🔍 CONFIRMATION CHECK: No active workflow/operation found")
        else:
            print(f"🔍 CONFIRMATION CHECK: Message '{message_lower}' not in confirmation words: {confirmation_words}")
        
        print(f"🔍 CONFIRMATION CHECK: Not a confirmation response, returning False")
        return False

    def _is_contract_id_response(self, user_message: str, context: Dict[str, Any] = None) -> bool:
        """Check if the user message is a contract ID response that should be routed to contract agent."""
        print(f"🔍 CONTRACT ID CHECK: user_message='{user_message}', context={context}")
        
        # Check if message is just a number (potential contract ID)
        if not user_message.strip().isdigit():
            print(f"🔍 CONTRACT ID CHECK: Not a digit, returning False")
            return False

        # If we have context indicating a pending contract operation, route to contract agent
        if context:
            context_str = str(context)
            print(f"🔍 CONTRACT ID CHECK: Context available, checking for contract operations")
            
            # Check for file upload context (indicates document upload operation)
            if isinstance(context, dict):
                if context.get('file_info') or 'file_info' in context_str:
                    print(f"🔍 CONTRACT ID CHECK: File info found, returning True")
                    return True

                # Check for pending contract operations
                user_operation = context.get('user_operation', '')
                print(f"🔍 CONTRACT ID CHECK: user_operation='{user_operation}'")
                if any(op in user_operation.lower() for op in ['contract', 'upload_contract_document']):
                    print(f"🔍 CONTRACT ID CHECK: Contract operation found, returning True")
                    return True

                # Check for contract-related context
                if context.get('current_contract_id') or 'contract' in context_str.lower():
                    print(f"🔍 CONTRACT ID CHECK: Contract context found, returning True")
                    return True
            else:
                # Handle string context
                if 'file_info' in context_str:
                    print(f"🔍 CONTRACT ID CHECK: File info in string context, returning True")
                    return True
                
                if 'contract' in context_str.lower():
                    print(f"🔍 CONTRACT ID CHECK: Contract in string context, returning True")
                    return True
            
            # Check for operation state in string context
            if 'Current operation: update_contract' in context_str:
                return True

        # Also check state data for contract operations
        if context and 'data' in context:
            state_data = context['data']
            user_operation = state_data.get('user_operation', '')
            if any(op in user_operation.lower() for op in ['contract', 'upload_contract_document']):
                return True

        return False

    def _is_all_response_to_contract_operation(self, user_message: str, context: Dict[str, Any] = None) -> bool:
        """Check if the user message is an 'all' response to a contract operation."""
        print(f"🔍 ALL RESPONSE CHECK: user_message='{user_message}', context={context}")
        
        # Check if message is "all" (case insensitive)
        if user_message.lower().strip() != 'all':
            print(f"🔍 ALL RESPONSE CHECK: Not 'all', returning False")
            return False

        # If we have context indicating a pending contract operation, route to contract agent
        if context:
            context_str = str(context)
            print(f"🔍 ALL RESPONSE CHECK: Context available, checking for contract operations")
            
            # Check for pending contract operations
            if isinstance(context, dict):
                user_operation = context.get('user_operation', '')
                print(f"🔍 ALL RESPONSE CHECK: user_operation='{user_operation}'")
                if any(op in user_operation.lower() for op in ['update_contract', 'delete_contract', 'create_contract']):
                    print(f"🔍 ALL RESPONSE CHECK: Contract operation found, returning True")
                    return True

                # Check for contract-related context
                if context.get('current_contract_id') or 'contract' in context_str.lower():
                    print(f"🔍 ALL RESPONSE CHECK: Contract context found, returning True")
                    return True
            else:
                # Handle string context
                if 'contract' in context_str.lower():
                    print(f"🔍 ALL RESPONSE CHECK: Contract in string context, returning True")
                    return True
            
            # Check for operation state in string context
            if 'update_contract' in context_str or 'delete_contract' in context_str or 'create_contract' in context_str:
                print(f"🔍 ALL RESPONSE CHECK: Contract operation in string context, returning True")
                return True

        # Also check state data for contract operations
        if context and 'data' in context:
            state_data = context['data']
            user_operation = state_data.get('user_operation', '')
            if any(op in user_operation.lower() for op in ['update_contract', 'delete_contract', 'create_contract']):
                print(f"🔍 ALL RESPONSE CHECK: Contract operation in state data, returning True")
                return True

        print(f"🔍 ALL RESPONSE CHECK: No contract operation found, returning False")
        return False

    def _is_employee_document_upload(self, user_message: str, context: Dict[str, Any] = None) -> bool:
        """Check if this is an employee document upload operation."""
        message_lower = user_message.lower()
        print(f"🔍 EMPLOYEE DOCUMENT CHECK: Checking message='{user_message}', context={context}")
        
        # Check for file upload context
        if context and isinstance(context, dict):
            if context.get('file_info'):
                print(f"🔍 EMPLOYEE DOCUMENT CHECK: File info found, checking for employee context")
                
                # Check if this is an employee operation - prioritize current message over context
                user_operation = context.get('user_operation', '')
                print(f"🔍 EMPLOYEE DOCUMENT CHECK: user_operation='{user_operation}'")
                
                # First check if the current message indicates an employee operation
                if ('employee' in message_lower or 'staff' in message_lower or 'worker' in message_lower or 'personnel' in message_lower):
                    print(f"🔍 EMPLOYEE DOCUMENT CHECK: Current message indicates employee operation")
                    return True
                
                # Only check context if current message doesn't clearly indicate a different operation
                if not ('client' in message_lower or 'contract' in message_lower or 'delete' in message_lower):
                    if 'employee' in user_operation.lower() or 'upload_employee_document' in user_operation.lower():
                        print(f"🔍 EMPLOYEE DOCUMENT CHECK: Employee operation detected from context")
                        return True
                
                # Generic logic: Check for explicit employee context indicators
                # Priority 1: Explicit employee keywords
                if 'employee' in message_lower or 'staff' in message_lower or 'worker' in message_lower or 'personnel' in message_lower:
                    print(f"🔍 EMPLOYEE DOCUMENT CHECK: Explicit employee keyword detected")
                    return True
                
                # Priority 2: Check if this is clearly a client operation (explicit client mention)
                if 'client' in message_lower:
                    print(f"🔍 EMPLOYEE DOCUMENT CHECK: Client mentioned - NOT an employee operation")
                    return False
                
                # Priority 3: Check for employee document patterns (NDA without client context)
                if 'nda' in message_lower and 'document' in message_lower and 'client' not in message_lower:
                    print(f"🔍 EMPLOYEE DOCUMENT CHECK: NDA document without client context - likely employee")
                    return True
                
                # Priority 4: Check for person-like names (first name + last name pattern)
                # This is more generic than hardcoded names
                
                # Look for patterns like "for John Smith" or "for Sarah Johnson" (not company names)
                person_pattern = r'for\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
                person_matches = re.findall(person_pattern, user_message)
                if person_matches:
                    # Check if it's not a company name (companies often have LLC, Inc, Corp, etc.)
                    company_indicators = ['llc', 'inc', 'corp', 'ltd', 'co', 'company', 'solutions', 'systems', 'group', 'international']
                    for match in person_matches:
                        if not any(indicator in match.lower() for indicator in company_indicators):
                            print(f"🔍 EMPLOYEE DOCUMENT CHECK: Person name pattern detected: {match}")
                            return True
            else:
                print(f"🔍 EMPLOYEE DOCUMENT CHECK: No file_info found in context")
        else:
            print(f"🔍 EMPLOYEE DOCUMENT CHECK: No context or context is not dict")
        
        print(f"🔍 EMPLOYEE DOCUMENT CHECK: Returning False")
        return False

    def _select_best_agent(self, scores: Dict[str, float]) -> Tuple[str, str]:
        """Select the best agent based on scores."""
        if not scores or all(score == 0 for score in scores.values()):
            return "client_agent", "low"  # Default fallback
        
        # Find the agent with the highest score
        best_agent = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_agent]
        
        # Calculate confidence based on score and margin
        sorted_scores = sorted(scores.values(), reverse=True)
        
        if best_score >= 5.0:
            confidence = "high"
        elif best_score >= 2.0:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Adjust confidence based on margin between top two scores
        if len(sorted_scores) > 1:
            margin = sorted_scores[0] - sorted_scores[1]
            if margin < 1.0:
                confidence = "low"
            elif margin >= 3.0 and confidence != "low":
                confidence = "high"
        
        return best_agent, confidence
    
    def _generate_reasoning(
        self, 
        selected_agent: str, 
        operation_type: str, 
        scores: Dict[str, float],
        original_message: str
    ) -> str:
        """Generate human-readable reasoning for the routing decision."""
        agent_name_map = {
            "employee_agent": "Employee Agent",
            "client_agent": "Client Agent", 
            "contract_agent": "Contract Agent",
            "deliverable_agent": "Deliverable Agent",
            "time_agent": "Time Agent",
            "user_agent": "User Agent"
        }
        
        agent_display_name = agent_name_map.get(selected_agent, selected_agent)
        selected_score = scores.get(selected_agent, 0)
        
        # Generate reasoning based on the selected agent and context
        if selected_agent == "employee_agent":
            if "employee_number" in original_message.lower():
                return f"Routed to {agent_display_name} - detected employee number update operation"
            elif any(word in original_message.lower() for word in ["hire", "onboard", "new employee"]):
                return f"Routed to {agent_display_name} - detected employee creation/hiring operation"
            elif any(word in original_message.lower() for word in ["salary", "job_title", "department"]):
                return f"Routed to {agent_display_name} - detected employee information update"
            else:
                return f"Routed to {agent_display_name} - detected employee-related {operation_type} operation"
        
        elif selected_agent == "client_agent":
            if "contact" in original_message.lower():
                return f"Routed to {agent_display_name} - detected client contact management"
            elif "company" in original_message.lower():
                return f"Routed to {agent_display_name} - detected company/client information operation"
            else:
                return f"Routed to {agent_display_name} - detected client-related {operation_type} operation"
        
        elif selected_agent == "contract_agent":
            if "billing" in original_message.lower():
                return f"Routed to {agent_display_name} - detected contract billing operation"
            elif "contract" in original_message.lower():
                return f"Routed to {agent_display_name} - detected contract management operation"
            else:
                return f"Routed to {agent_display_name} - detected contract-related {operation_type} operation"
        
        else:
            return f"Routed to {agent_display_name} - best match for {operation_type} operation (score: {selected_score:.1f})"


# Example usage and test cases
def test_enhanced_routing():
    """Test the enhanced routing logic with various scenarios."""
    router = EnhancedRoutingLogic()
    
    test_cases = [
        # Employee-related requests
        "Update employee_number to EMP10 for Tina Miles",
        "Create a new employee named John Smith as senior developer",
        "Change salary for employee Sarah Johnson to $85000",
        "Add new staff member Mike Wilson in Marketing department",
        
        # Client-related requests  
        "Update contact person for Acme Corporation",
        "Create new client TechCorp with contact Maria Garcia",
        "Change primary contact email for Global Retail",
        
        # Contract-related requests
        "Update billing date for Acme contract to December 15th",
        "Create new contract for TechCorp worth $50000",
        "Modify contract terms for existing client",
        
        # Ambiguous cases
        "Update Tina Miles information",
        "Create new record for John Smith",
        "Change details for Acme Corporation"
    ]
    
    print("=== Enhanced Routing Logic Test Results ===\n")
    
    for i, test_message in enumerate(test_cases, 1):
        result = router.classify_request(test_message)
        print(f"{i}. Message: '{test_message}'")
        print(f"   → Agent: {result['agent_name']}")
        print(f"   → Confidence: {result['confidence']}")
        print(f"   → Reasoning: {result['reasoning']}")
        print(f"   → Operation: {result['operation_type']}")
        print(f"   → Scores: {result['scores']}")
        print()

if __name__ == "__main__":
    test_enhanced_routing()
