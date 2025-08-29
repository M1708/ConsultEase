"""
Phase 2 Output Validator Implementation

Comprehensive output validation and verification:
- Rule-based validation system
- Content safety and filtering
- Format and structure validation
- Custom validation rules
"""

import re
import json
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationType(Enum):
    """Types of validation"""
    FORMAT = "format"
    CONTENT = "content"
    SAFETY = "safety"
    BUSINESS_LOGIC = "business_logic"
    SCHEMA = "schema"

@dataclass
class ValidationIssue:
    """Individual validation issue"""
    rule_name: str
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of validation process"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 1.0  # 0.0 to 1.0, where 1.0 is perfect
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue"""
        self.issues.append(issue)
        
        # Adjust validity and score based on severity
        if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False
        
        # Reduce score based on severity
        severity_penalties = {
            ValidationSeverity.INFO: 0.01,
            ValidationSeverity.WARNING: 0.05,
            ValidationSeverity.ERROR: 0.2,
            ValidationSeverity.CRITICAL: 0.5
        }
        self.score = max(0.0, self.score - severity_penalties.get(issue.severity, 0.1))
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)

class ValidationRule(ABC):
    """Abstract base class for validation rules"""
    
    def __init__(
        self,
        name: str,
        description: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        validation_type: ValidationType = ValidationType.CONTENT
    ):
        self.name = name
        self.description = description
        self.severity = severity
        self.validation_type = validation_type
    
    @abstractmethod
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        """Validate data and return list of issues"""
        pass

class RegexValidationRule(ValidationRule):
    """Validation rule based on regular expressions"""
    
    def __init__(
        self,
        name: str,
        pattern: str,
        field: Optional[str] = None,
        should_match: bool = True,
        **kwargs
    ):
        super().__init__(name, f"Regex validation: {pattern}", **kwargs)
        self.pattern = re.compile(pattern)
        self.field = field
        self.should_match = should_match
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        """Validate using regex pattern"""
        issues = []
        
        # Extract field value if specified
        if self.field:
            if isinstance(data, dict) and self.field in data:
                value = str(data[self.field])
            else:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Field '{self.field}' not found",
                    field=self.field
                ))
                return issues
        else:
            value = str(data)
        
        # Check pattern match
        matches = bool(self.pattern.search(value))
        
        if self.should_match and not matches:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Value does not match required pattern: {self.pattern.pattern}",
                field=self.field,
                value=value
            ))
        elif not self.should_match and matches:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Value matches forbidden pattern: {self.pattern.pattern}",
                field=self.field,
                value=value
            ))
        
        return issues

class LengthValidationRule(ValidationRule):
    """Validation rule for string/list length"""
    
    def __init__(
        self,
        name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        field: Optional[str] = None,
        **kwargs
    ):
        super().__init__(name, f"Length validation: {min_length}-{max_length}", **kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.field = field
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        """Validate length constraints"""
        issues = []
        
        # Extract field value if specified
        if self.field:
            if isinstance(data, dict) and self.field in data:
                value = data[self.field]
            else:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Field '{self.field}' not found",
                    field=self.field
                ))
                return issues
        else:
            value = data
        
        # Get length
        try:
            length = len(value)
        except TypeError:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Value does not have length property",
                field=self.field,
                value=value
            ))
            return issues
        
        # Check constraints
        if self.min_length is not None and length < self.min_length:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Length {length} is below minimum {self.min_length}",
                field=self.field,
                value=value,
                suggestion=f"Increase length to at least {self.min_length}"
            ))
        
        if self.max_length is not None and length > self.max_length:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Length {length} exceeds maximum {self.max_length}",
                field=self.field,
                value=value,
                suggestion=f"Reduce length to at most {self.max_length}"
            ))
        
        return issues

class RequiredFieldsRule(ValidationRule):
    """Validation rule for required fields"""
    
    def __init__(
        self,
        name: str,
        required_fields: List[str],
        **kwargs
    ):
        super().__init__(name, f"Required fields: {', '.join(required_fields)}", **kwargs)
        self.required_fields = required_fields
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        """Validate required fields are present"""
        issues = []
        
        if not isinstance(data, dict):
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message="Data must be a dictionary to check required fields",
                value=data
            ))
            return issues
        
        for field in self.required_fields:
            if field not in data or data[field] is None:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Required field '{field}' is missing or null",
                    field=field,
                    suggestion=f"Provide a value for '{field}'"
                ))
        
        return issues

class JSONValidationRule(ValidationRule):
    """Validation rule for JSON format"""
    
    def __init__(
        self,
        name: str,
        field: Optional[str] = None,
        **kwargs
    ):
        super().__init__(name, "JSON format validation", validation_type=ValidationType.FORMAT, **kwargs)
        self.field = field
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        """Validate JSON format"""
        issues = []
        
        # Extract field value if specified
        if self.field:
            if isinstance(data, dict) and self.field in data:
                value = data[self.field]
            else:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Field '{self.field}' not found",
                    field=self.field
                ))
                return issues
        else:
            value = data
        
        # Try to parse as JSON
        if isinstance(value, str):
            try:
                json.loads(value)
            except json.JSONDecodeError as e:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Invalid JSON format: {str(e)}",
                    field=self.field,
                    value=value,
                    suggestion="Ensure the value is valid JSON"
                ))
        
        return issues

class SafetyValidationRule(ValidationRule):
    """Validation rule for content safety"""
    
    def __init__(
        self,
        name: str,
        forbidden_patterns: List[str],
        field: Optional[str] = None,
        **kwargs
    ):
        super().__init__(name, "Content safety validation", validation_type=ValidationType.SAFETY, **kwargs)
        self.forbidden_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in forbidden_patterns]
        self.field = field
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        """Validate content safety"""
        issues = []
        
        # Extract field value if specified
        if self.field:
            if isinstance(data, dict) and self.field in data:
                value = str(data[self.field])
            else:
                return issues  # Field not found, skip safety check
        else:
            value = str(data)
        
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if pattern.search(value):
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Content contains forbidden pattern: {pattern.pattern}",
                    field=self.field,
                    value=value,
                    suggestion="Remove or modify the flagged content"
                ))
        
        return issues

class CustomValidationRule(ValidationRule):
    """Custom validation rule with user-defined function"""
    
    def __init__(
        self,
        name: str,
        validation_func: Callable[[Any, Optional[Dict[str, Any]]], List[ValidationIssue]],
        **kwargs
    ):
        super().__init__(name, "Custom validation rule", **kwargs)
        self.validation_func = validation_func
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        """Validate using custom function"""
        try:
            return self.validation_func(data, context)
        except Exception as e:
            return [ValidationIssue(
                rule_name=self.name,
                severity=ValidationSeverity.ERROR,
                message=f"Custom validation failed: {str(e)}",
                value=data
            )]

class OutputValidator:
    """
    Comprehensive output validation system
    
    Features:
    - Multiple validation rule types
    - Configurable severity levels
    - Detailed validation results
    - Custom validation rules
    """
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self.validation_history: List[ValidationResult] = []
    
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule"""
        self.rules.append(rule)
        logger.info(f"Added validation rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a validation rule by name"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        logger.info(f"Removed validation rule: {rule_name}")
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate data against all rules"""
        result = ValidationResult(is_valid=True)
        
        # Apply all validation rules
        for rule in self.rules:
            try:
                issues = rule.validate(data, context)
                for issue in issues:
                    result.add_issue(issue)
            except Exception as e:
                # Rule execution failed
                result.add_issue(ValidationIssue(
                    rule_name=rule.name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Rule execution failed: {str(e)}"
                ))
                logger.error(f"Validation rule '{rule.name}' failed: {e}")
        
        # Store validation history
        self.validation_history.append(result)
        
        # Keep only recent history
        if len(self.validation_history) > 1000:
            self.validation_history = self.validation_history[-1000:]
        
        return result
    
    def validate_agent_output(self, agent_output: Dict[str, Any]) -> ValidationResult:
        """Validate agent output with common rules"""
        # Add common agent output validation rules if not already present
        common_rules = [
            RequiredFieldsRule("agent_output_required", ["content"]),
            LengthValidationRule("content_length", min_length=1, max_length=10000, field="content"),
            SafetyValidationRule("content_safety", [
                r"<script.*?>.*?</script>",  # Script tags
                r"javascript:",              # JavaScript URLs
                r"on\w+\s*=",               # Event handlers
            ], field="content")
        ]
        
        # Add rules if they don't exist
        existing_rule_names = {rule.name for rule in self.rules}
        for rule in common_rules:
            if rule.name not in existing_rule_names:
                self.add_rule(rule)
        
        return self.validate(agent_output)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        if not self.validation_history:
            return {}
        
        total_validations = len(self.validation_history)
        valid_count = sum(1 for result in self.validation_history if result.is_valid)
        
        # Calculate average score
        avg_score = sum(result.score for result in self.validation_history) / total_validations
        
        # Count issues by severity
        issue_counts = {severity.value: 0 for severity in ValidationSeverity}
        for result in self.validation_history:
            for issue in result.issues:
                issue_counts[issue.severity.value] += 1
        
        return {
            "total_validations": total_validations,
            "valid_count": valid_count,
            "invalid_count": total_validations - valid_count,
            "success_rate": valid_count / total_validations,
            "average_score": avg_score,
            "issue_counts": issue_counts,
            "active_rules": len(self.rules)
        }
    
    def get_rule_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for each rule"""
        rule_stats = {}
        
        for rule in self.rules:
            rule_stats[rule.name] = {
                "type": rule.validation_type.value,
                "severity": rule.severity.value,
                "triggers": 0,
                "issues_found": 0
            }
        
        # Count rule triggers and issues
        for result in self.validation_history:
            triggered_rules = set()
            for issue in result.issues:
                rule_name = issue.rule_name
                if rule_name in rule_stats:
                    rule_stats[rule_name]["issues_found"] += 1
                    triggered_rules.add(rule_name)
            
            # Count triggers (rules that were executed)
            for rule_name in triggered_rules:
                rule_stats[rule_name]["triggers"] += 1
        
        return rule_stats

# Global validator instance
_output_validator: Optional[OutputValidator] = None

def get_output_validator() -> OutputValidator:
    """Get global output validator instance"""
    global _output_validator
    if _output_validator is None:
        _output_validator = OutputValidator()
    return _output_validator

# Convenience functions for common validation rules
def create_email_validation_rule(field: str = "email") -> RegexValidationRule:
    """Create email validation rule"""
    return RegexValidationRule(
        name=f"{field}_email_format",
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        field=field,
        validation_type=ValidationType.FORMAT,
        severity=ValidationSeverity.ERROR
    )

def create_phone_validation_rule(field: str = "phone") -> RegexValidationRule:
    """Create phone number validation rule"""
    return RegexValidationRule(
        name=f"{field}_phone_format",
        pattern=r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',
        field=field,
        validation_type=ValidationType.FORMAT,
        severity=ValidationSeverity.ERROR
    )

def create_sql_injection_rule(field: Optional[str] = None) -> SafetyValidationRule:
    """Create SQL injection prevention rule"""
    return SafetyValidationRule(
        name=f"sql_injection_{field or 'global'}",
        forbidden_patterns=[
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
            r"(?i)(\-\-|\#|\/\*|\*\/)",
            r"(?i)(exec|execute|sp_|xp_)",
        ],
        field=field,
        severity=ValidationSeverity.CRITICAL
    )
