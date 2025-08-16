from typing import Any, Dict
from pydantic import BaseModel, validator
import re

class InputGuardrails:
    @staticmethod
    def sanitize_user_input(user_input: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(user_input, str):
            raise ValueError("Input must be a string")
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload=',
            r'onerror=',
            r'eval\(',
            r'exec\(',
            r'system\(',
            r'rm\s+-rf',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+.*SET'
        ]
        
        sanitized = user_input
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Limit length and normalize whitespace
        sanitized = sanitized.strip()[:2000]
        
        if not sanitized:
            raise ValueError("Input cannot be empty after sanitization")
        
        return sanitized
    
    @staticmethod
    def validate_business_context(context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business context for agent operations"""
        required_fields = ['user_id', 'session_id']
        
        for field in required_fields:
            if field not in context:
                raise ValueError(f"Missing required context field: {field}")
        
        # Validate user_id format (assuming UUID)
        if not re.match(r'^[0-9a-f-]{36}$', context.get('user_id', '')):
            context['user_id'] = 'anonymous'
        
        return context

def input_sanitization_guardrail(user_input: str) -> str:
    """Input guardrail for OpenAI Agents"""
    return InputGuardrails.sanitize_user_input(user_input)

def business_context_guardrail(context: Dict[str, Any]) -> Dict[str, Any]:
    """Business context validation guardrail"""
    return InputGuardrails.validate_business_context(context)