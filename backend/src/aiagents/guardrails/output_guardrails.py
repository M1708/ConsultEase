from typing import Any, Dict, List
import json

class OutputGuardrails:
    @staticmethod
    def validate_agent_output(output: Any) -> Any:
        """Validate agent output before returning to user"""
        if isinstance(output, dict):
            # Remove any internal system fields
            sensitive_keys = ['_internal', 'debug', 'raw_response', 'system_prompt']
            for key in sensitive_keys:
                output.pop(key, None)
        
        return output
    
    @staticmethod
    def sanitize_data_exposure(data: Dict[str, Any], user_role: str = 'user') -> Dict[str, Any]:
        """Sanitize data based on user role and permissions"""
        if user_role == 'admin':
            return data
        
        # Remove sensitive fields for non-admin users
        sensitive_fields = ['created_by', 'updated_by', 'internal_notes']
        sanitized = data.copy()
        
        for field in sensitive_fields:
            sanitized.pop(field, None)
        
        return sanitized

def output_validation_guardrail(output: Any) -> Any:
    """Output validation guardrail for OpenAI Agents"""
    return OutputGuardrails.validate_agent_output(output)