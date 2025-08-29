"""
Enhanced input validation that extends existing guardrails.
Provides comprehensive input sanitization and validation for agent interactions.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from src.aiagents.guardrails.input_guardrails import InputGuardrails
from src.aiagents.graph.state import AgentState


class EnhancedInputValidator:
    """Enhanced input validator extending existing guardrails"""
    
    def __init__(self):
        self.base_guardrails = InputGuardrails()
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for different input types"""
        return {
            "message_length": {
                "min": 1,
                "max": 10000,
                "warning_threshold": 5000
            },
            "sql_injection_patterns": [
                r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
                r"(?i)(or|and)\s+\d+\s*=\s*\d+",
                r"(?i)(\-\-|\#|\/\*|\*\/)",
                r"(?i)(exec|execute|sp_|xp_)"
            ],
            "xss_patterns": [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>.*?</iframe>"
            ],
            "sensitive_data_patterns": [
                r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"  # Email (for logging)
            ],
            "business_rules": {
                "client_name": {
                    "min_length": 2,
                    "max_length": 255,
                    "pattern": r"^[a-zA-Z0-9\s\-\.\&]+$"
                },
                "email": {
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                },
                "phone": {
                    "pattern": r"^[\+]?[1-9][\d\s\-\(\)]{7,15}$"
                }
            }
        }
    
    async def validate_input(
        self, 
        user_input: str, 
        state: AgentState,
        validation_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Comprehensive input validation with enhanced security checks
        """
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "sanitized_input": user_input,
            "risk_level": "low",
            "validation_details": {}
        }
        
        try:
            # Basic validation using existing guardrails
            base_result = await self.base_guardrails.validate_input(user_input)
            if not base_result.get("is_valid", True):
                validation_result["is_valid"] = False
                validation_result["errors"].extend(base_result.get("errors", []))
            
            # Enhanced security validation
            security_result = self._validate_security(user_input)
            validation_result["validation_details"]["security"] = security_result
            
            if security_result["risk_level"] == "high":
                validation_result["is_valid"] = False
                validation_result["errors"].append("High security risk detected")
                validation_result["risk_level"] = "high"
            elif security_result["risk_level"] == "medium":
                validation_result["warnings"].append("Medium security risk detected")
                validation_result["risk_level"] = "medium"
            
            # Business rule validation
            business_result = self._validate_business_rules(user_input, validation_context)
            validation_result["validation_details"]["business"] = business_result
            
            if business_result["violations"]:
                validation_result["warnings"].extend(business_result["violations"])
            
            # Context-aware validation
            context_result = await self._validate_context(user_input, state)
            validation_result["validation_details"]["context"] = context_result
            
            # Input sanitization
            sanitized = self._sanitize_input(user_input)
            validation_result["sanitized_input"] = sanitized
            
            # Length and format validation
            format_result = self._validate_format(user_input)
            validation_result["validation_details"]["format"] = format_result
            
            if not format_result["is_valid"]:
                validation_result["is_valid"] = False
                validation_result["errors"].extend(format_result["errors"])
            
            return validation_result["is_valid"], validation_result
            
        except Exception as e:
            print(f"Error in enhanced input validation: {e}")
            return False, {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "sanitized_input": user_input,
                "risk_level": "unknown"
            }
    
    def _validate_security(self, user_input: str) -> Dict[str, Any]:
        """Validate input for security threats"""
        security_result = {
            "risk_level": "low",
            "threats_detected": [],
            "details": {}
        }
        
        # SQL injection detection
        sql_threats = []
        for pattern in self.validation_rules["sql_injection_patterns"]:
            if re.search(pattern, user_input, re.IGNORECASE):
                sql_threats.append(f"SQL injection pattern detected: {pattern}")
        
        if sql_threats:
            security_result["threats_detected"].extend(sql_threats)
            security_result["risk_level"] = "high"
        
        # XSS detection
        xss_threats = []
        for pattern in self.validation_rules["xss_patterns"]:
            if re.search(pattern, user_input, re.IGNORECASE):
                xss_threats.append(f"XSS pattern detected: {pattern}")
        
        if xss_threats:
            security_result["threats_detected"].extend(xss_threats)
            security_result["risk_level"] = "high"
        
        # Sensitive data detection
        sensitive_threats = []
        for pattern in self.validation_rules["sensitive_data_patterns"]:
            if re.search(pattern, user_input):
                sensitive_threats.append("Potential sensitive data detected")
        
        if sensitive_threats:
            security_result["threats_detected"].extend(sensitive_threats)
            if security_result["risk_level"] == "low":
                security_result["risk_level"] = "medium"
        
        security_result["details"] = {
            "sql_threats": sql_threats,
            "xss_threats": xss_threats,
            "sensitive_threats": sensitive_threats
        }
        
        return security_result
    
    def _validate_business_rules(
        self, 
        user_input: str, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate input against business rules"""
        business_result = {
            "violations": [],
            "validated_fields": {}
        }
        
        if not context:
            return business_result
        
        # Validate specific fields based on context
        for field_name, field_value in context.items():
            if field_name in self.validation_rules["business_rules"]:
                field_rules = self.validation_rules["business_rules"][field_name]
                field_result = self._validate_field(field_value, field_rules, field_name)
                business_result["validated_fields"][field_name] = field_result
                
                if not field_result["is_valid"]:
                    business_result["violations"].extend(field_result["errors"])
        
        return business_result
    
    def _validate_field(self, value: str, rules: Dict[str, Any], field_name: str) -> Dict[str, Any]:
        """Validate a specific field against its rules"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Length validation
        if "min_length" in rules and len(value) < rules["min_length"]:
            result["is_valid"] = False
            result["errors"].append(f"{field_name} is too short (minimum {rules['min_length']} characters)")
        
        if "max_length" in rules and len(value) > rules["max_length"]:
            result["is_valid"] = False
            result["errors"].append(f"{field_name} is too long (maximum {rules['max_length']} characters)")
        
        # Pattern validation
        if "pattern" in rules and not re.match(rules["pattern"], value):
            result["is_valid"] = False
            result["errors"].append(f"{field_name} format is invalid")
        
        return result
    
    async def _validate_context(self, user_input: str, state: AgentState) -> Dict[str, Any]:
        """Validate input in the context of current conversation state"""
        context_result = {
            "is_contextually_appropriate": True,
            "context_warnings": []
        }
        
        try:
            # Check if input is appropriate for current agent
            current_agent = state.get("current_agent", "")
            if current_agent and not self._is_input_appropriate_for_agent(user_input, current_agent):
                context_result["context_warnings"].append(
                    f"Input may not be appropriate for {current_agent}"
                )
            
            # Check conversation flow
            if self._is_conversation_flow_broken(user_input, state):
                context_result["context_warnings"].append(
                    "Input may break conversation flow"
                )
            
            # Check for repetitive requests
            if await self._is_repetitive_request(user_input, state):
                context_result["context_warnings"].append(
                    "Similar request detected recently"
                )
            
        except Exception as e:
            print(f"Error in context validation: {e}")
        
        return context_result
    
    def _is_input_appropriate_for_agent(self, user_input: str, agent_name: str) -> bool:
        """Check if input is appropriate for the current agent"""
        agent_keywords = {
            "client_agent": ["client", "company", "customer", "contact"],
            "contract_agent": ["contract", "agreement", "terms", "billing"],
            "employee_agent": ["employee", "staff", "hr", "personnel"],
            "deliverable_agent": ["deliverable", "project", "milestone", "task"],
            "time_agent": ["time", "hours", "timesheet", "log"],
            "user_agent": ["user", "account", "profile", "permission"]
        }
        
        if agent_name not in agent_keywords:
            return True  # Unknown agent, assume appropriate
        
        keywords = agent_keywords[agent_name]
        user_input_lower = user_input.lower()
        
        # If input contains relevant keywords, it's appropriate
        return any(keyword in user_input_lower for keyword in keywords)
    
    def _is_conversation_flow_broken(self, user_input: str, state: AgentState) -> bool:
        """Check if input breaks natural conversation flow"""
        # Simple heuristic: check for abrupt topic changes
        if len(state.get("messages", [])) < 2:
            return False
        
        # This is a simplified check - in practice, you'd use more sophisticated NLP
        abrupt_change_indicators = [
            "forget that", "ignore previous", "start over", "new topic"
        ]
        
        return any(indicator in user_input.lower() for indicator in abrupt_change_indicators)
    
    async def _is_repetitive_request(self, user_input: str, state: AgentState) -> bool:
        """Check if this is a repetitive request"""
        try:
            # Get recent conversation history
            recent_messages = state.get("memory", {}).get("conversation_history", [])[-5:]
            
            # Simple similarity check
            for msg in recent_messages:
                if msg.get("role") == "user":
                    similarity = self._calculate_similarity(user_input, msg.get("content", ""))
                    if similarity > 0.8:  # 80% similarity threshold
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _validate_format(self, user_input: str) -> Dict[str, Any]:
        """Validate input format and structure"""
        format_result = {
            "is_valid": True,
            "errors": []
        }
        
        # Length validation
        rules = self.validation_rules["message_length"]
        if len(user_input) < rules["min"]:
            format_result["is_valid"] = False
            format_result["errors"].append("Input is too short")
        elif len(user_input) > rules["max"]:
            format_result["is_valid"] = False
            format_result["errors"].append("Input is too long")
        elif len(user_input) > rules["warning_threshold"]:
            # This would be a warning, not an error
            pass
        
        # Character validation
        if not user_input.strip():
            format_result["is_valid"] = False
            format_result["errors"].append("Input cannot be empty or only whitespace")
        
        return format_result
    
    def _sanitize_input(self, user_input: str) -> str:
        """Sanitize input by removing or escaping potentially harmful content"""
        sanitized = user_input
        
        # Remove potential XSS content
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # Escape HTML entities
        sanitized = sanitized.replace('<', '&lt;').replace('>', '&gt;')
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """Get a human-readable summary of validation results"""
        if validation_result["is_valid"]:
            if validation_result["warnings"]:
                return f"Input valid with {len(validation_result['warnings'])} warnings"
            else:
                return "Input valid"
        else:
            error_count = len(validation_result["errors"])
            warning_count = len(validation_result["warnings"])
            return f"Input invalid: {error_count} errors, {warning_count} warnings"
