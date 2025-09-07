"""
Enhanced Routing Logic for Intelligent Agent Assignment

This module provides improved routing logic to ensure requests are correctly
classified and routed to the appropriate specialized agent.
"""

from typing import Dict, List, Tuple
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
    
    def classify_request(self, user_message: str) -> Dict[str, any]:
        """
        Classify a user request to determine the appropriate agent.
        
        Returns:
            Dict containing agent_name, confidence, reasoning, and operation_type
        """
        message_lower = user_message.lower()
        
        print(f"🔧 DEBUG: Enhanced routing - classifying: '{user_message}'")
        
        # Step 1: Identify operation type
        operation_type = self._identify_operation_type(message_lower)
        print(f"🔧 DEBUG: Enhanced routing - operation type: {operation_type}")
        
        # Step 2: Score each agent based on keyword matches
        agent_scores = self._calculate_agent_scores(user_message, message_lower)
        print(f"🔧 DEBUG: Enhanced routing - base scores: {agent_scores}")
        
        # Step 3: Apply context-aware adjustments
        adjusted_scores = self._apply_context_adjustments(
            user_message, message_lower, agent_scores, operation_type
        )
        print(f"🔧 DEBUG: Enhanced routing - adjusted scores: {adjusted_scores}")
        
        # Step 4: Determine the best agent
        best_agent, confidence = self._select_best_agent(adjusted_scores)
        print(f"🔧 DEBUG: Enhanced routing - selected agent: {best_agent} (confidence: {confidence})")
        
        # Step 5: Generate reasoning
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
        
        # Adjustment 2: Contract vs Client disambiguation
        if operation_type == "update" and any(word in message_lower for word in ["billing", "contract", "amount", "date"]):
            adjusted_scores["contract_agent"] += 3.0
        
        # Adjustment 3: Person name context (Agentic approach - let agent reason about context)
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
        employee_indicators = [
            "employee_number", "emp_number", "staff_id", "personnel_id",
            "job_title", "department", "salary", "wage", "hourly_rate",
            "full_time", "part_time", "employment_type", "hire_date",
            "contractor", "consultant", "permanent", "temporary"
        ]
        
        return any(indicator in message_lower for indicator in employee_indicators)
    
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
