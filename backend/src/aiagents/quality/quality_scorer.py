"""
Phase 2 Quality Scorer Implementation

Comprehensive quality scoring and assessment:
- Multi-dimensional quality metrics
- Configurable scoring algorithms
- Quality trend analysis
- Performance benchmarking
"""

import time
import statistics
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class QualityDimension(Enum):
    """Quality assessment dimensions"""
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    CONSISTENCY = "consistency"
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    USABILITY = "usability"

class ScoreAggregation(Enum):
    """Score aggregation methods"""
    WEIGHTED_AVERAGE = "weighted_average"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    MEDIAN = "median"
    HARMONIC_MEAN = "harmonic_mean"

@dataclass
class QualityScore:
    """Individual quality score for a dimension"""
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    confidence: float = 1.0  # 0.0 to 1.0
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityMetrics:
    """Comprehensive quality assessment"""
    overall_score: float
    dimension_scores: Dict[QualityDimension, QualityScore]
    aggregation_method: ScoreAggregation
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_score(self, dimension: QualityDimension) -> Optional[float]:
        """Get score for a specific dimension"""
        if dimension in self.dimension_scores:
            return self.dimension_scores[dimension].score
        return None
    
    def get_weighted_score(self, weights: Dict[QualityDimension, float]) -> float:
        """Calculate weighted score using custom weights"""
        total_weight = 0.0
        weighted_sum = 0.0
        
        for dimension, weight in weights.items():
            if dimension in self.dimension_scores:
                score = self.dimension_scores[dimension].score
                confidence = self.dimension_scores[dimension].confidence
                effective_weight = weight * confidence
                weighted_sum += score * effective_weight
                total_weight += effective_weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0

class QualityScorer(ABC):
    """Abstract base class for quality scorers"""
    
    def __init__(self, name: str, dimension: QualityDimension):
        self.name = name
        self.dimension = dimension
    
    @abstractmethod
    async def score(self, data: Any, context: Optional[Dict[str, Any]] = None) -> QualityScore:
        """Score the quality of data for this dimension"""
        pass

class AccuracyScorer(QualityScorer):
    """Scorer for accuracy assessment"""
    
    def __init__(self, name: str = "accuracy_scorer"):
        super().__init__(name, QualityDimension.ACCURACY)
    
    async def score(self, data: Any, context: Optional[Dict[str, Any]] = None) -> QualityScore:
        """Score accuracy based on various factors"""
        score = 1.0
        confidence = 0.8
        explanation = "Accuracy assessment"
        
        # Check for factual consistency indicators
        if isinstance(data, dict) and "content" in data:
            content = str(data["content"]).lower()
            
            # Look for uncertainty indicators
            uncertainty_phrases = [
                "i think", "maybe", "possibly", "might be", "could be",
                "not sure", "uncertain", "unclear", "probably"
            ]
            
            uncertainty_count = sum(1 for phrase in uncertainty_phrases if phrase in content)
            if uncertainty_count > 0:
                score -= min(0.3, uncertainty_count * 0.1)
                explanation += f" (found {uncertainty_count} uncertainty indicators)"
            
            # Check for contradictions
            contradiction_patterns = [
                ("yes", "no"), ("true", "false"), ("correct", "incorrect"),
                ("right", "wrong"), ("valid", "invalid")
            ]
            
            for pos, neg in contradiction_patterns:
                if pos in content and neg in content:
                    score -= 0.2
                    explanation += " (potential contradiction detected)"
                    break
        
        return QualityScore(
            dimension=self.dimension,
            score=max(0.0, score),
            confidence=confidence,
            explanation=explanation
        )

class RelevanceScorer(QualityScorer):
    """Scorer for relevance assessment"""
    
    def __init__(self, name: str = "relevance_scorer"):
        super().__init__(name, QualityDimension.RELEVANCE)
    
    async def score(self, data: Any, context: Optional[Dict[str, Any]] = None) -> QualityScore:
        """Score relevance based on context matching"""
        score = 0.8  # Default moderate relevance
        confidence = 0.7
        explanation = "Relevance assessment"
        
        if context and "query" in context and isinstance(data, dict) and "content" in data:
            query = str(context["query"]).lower()
            content = str(data["content"]).lower()
            
            # Simple keyword matching
            query_words = set(query.split())
            content_words = set(content.split())
            
            if query_words and content_words:
                overlap = len(query_words.intersection(content_words))
                overlap_ratio = overlap / len(query_words)
                
                score = min(1.0, 0.5 + overlap_ratio)
                confidence = 0.9
                explanation = f"Keyword overlap: {overlap}/{len(query_words)} ({overlap_ratio:.2%})"
        
        return QualityScore(
            dimension=self.dimension,
            score=score,
            confidence=confidence,
            explanation=explanation
        )

class CompletenessScorer(QualityScorer):
    """Scorer for completeness assessment"""
    
    def __init__(self, name: str = "completeness_scorer"):
        super().__init__(name, QualityDimension.COMPLETENESS)
    
    async def score(self, data: Any, context: Optional[Dict[str, Any]] = None) -> QualityScore:
        """Score completeness based on expected content"""
        score = 1.0
        confidence = 0.8
        explanation = "Completeness assessment"
        
        if isinstance(data, dict):
            # Check for required fields
            required_fields = ["content"]
            missing_fields = [field for field in required_fields if field not in data or not data[field]]
            
            if missing_fields:
                score -= len(missing_fields) * 0.3
                explanation += f" (missing fields: {', '.join(missing_fields)})"
            
            # Check content length
            if "content" in data:
                content_length = len(str(data["content"]))
                if content_length < 10:
                    score -= 0.4
                    explanation += " (content too short)"
                elif content_length < 50:
                    score -= 0.2
                    explanation += " (content somewhat short)"
        
        return QualityScore(
            dimension=self.dimension,
            score=max(0.0, score),
            confidence=confidence,
            explanation=explanation
        )

class ClarityScorer(QualityScorer):
    """Scorer for clarity assessment"""
    
    def __init__(self, name: str = "clarity_scorer"):
        super().__init__(name, QualityDimension.CLARITY)
    
    async def score(self, data: Any, context: Optional[Dict[str, Any]] = None) -> QualityScore:
        """Score clarity based on readability factors"""
        score = 1.0
        confidence = 0.7
        explanation = "Clarity assessment"
        
        if isinstance(data, dict) and "content" in data:
            content = str(data["content"])
            
            # Check for overly complex sentences
            sentences = content.split('.')
            long_sentences = [s for s in sentences if len(s.split()) > 30]
            if long_sentences:
                score -= min(0.3, len(long_sentences) * 0.1)
                explanation += f" ({len(long_sentences)} overly long sentences)"
            
            # Check for jargon or complex words
            complex_indicators = [
                "utilize", "facilitate", "implement", "methodology", "paradigm",
                "synergy", "leverage", "optimize", "streamline", "comprehensive"
            ]
            
            jargon_count = sum(1 for word in complex_indicators if word.lower() in content.lower())
            if jargon_count > 3:
                score -= 0.2
                explanation += f" (high jargon usage: {jargon_count} terms)"
            
            # Check for unclear pronouns
            unclear_pronouns = ["it", "this", "that", "they", "them"]
            pronoun_density = sum(content.lower().count(pronoun) for pronoun in unclear_pronouns)
            word_count = len(content.split())
            
            if word_count > 0 and pronoun_density / word_count > 0.1:
                score -= 0.15
                explanation += " (high pronoun density)"
        
        return QualityScore(
            dimension=self.dimension,
            score=max(0.0, score),
            confidence=confidence,
            explanation=explanation
        )

class SafetyScorer(QualityScorer):
    """Scorer for safety assessment"""
    
    def __init__(self, name: str = "safety_scorer"):
        super().__init__(name, QualityDimension.SAFETY)
    
    async def score(self, data: Any, context: Optional[Dict[str, Any]] = None) -> QualityScore:
        """Score safety based on content analysis"""
        score = 1.0
        confidence = 0.9
        explanation = "Safety assessment"
        
        if isinstance(data, dict) and "content" in data:
            content = str(data["content"]).lower()
            
            # Check for potentially harmful content
            harmful_patterns = [
                r"<script", r"javascript:", r"onclick=", r"onerror=",  # XSS
                r"union.*select", r"drop.*table", r"delete.*from",    # SQL injection
                r"exec\(", r"eval\(", r"system\(",                   # Code execution
            ]
            
            import re
            for pattern in harmful_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    score -= 0.5
                    explanation += f" (detected harmful pattern: {pattern})"
                    confidence = 1.0
                    break
            
            # Check for inappropriate content indicators
            inappropriate_terms = [
                "password", "secret", "token", "api_key", "private_key"
            ]
            
            for term in inappropriate_terms:
                if term in content:
                    score -= 0.3
                    explanation += f" (contains sensitive term: {term})"
                    break
        
        return QualityScore(
            dimension=self.dimension,
            score=max(0.0, score),
            confidence=confidence,
            explanation=explanation
        )

class QualityAssessmentEngine:
    """
    Comprehensive quality assessment engine
    
    Features:
    - Multiple quality dimensions
    - Configurable scoring algorithms
    - Quality trend analysis
    - Performance benchmarking
    """
    
    def __init__(
        self,
        scorers: Optional[List[QualityScorer]] = None,
        default_weights: Optional[Dict[QualityDimension, float]] = None,
        aggregation_method: ScoreAggregation = ScoreAggregation.WEIGHTED_AVERAGE
    ):
        self.scorers = scorers or self._get_default_scorers()
        self.default_weights = default_weights or self._get_default_weights()
        self.aggregation_method = aggregation_method
        self.assessment_history: List[QualityMetrics] = []
    
    def _get_default_scorers(self) -> List[QualityScorer]:
        """Get default set of quality scorers"""
        return [
            AccuracyScorer(),
            RelevanceScorer(),
            CompletenessScorer(),
            ClarityScorer(),
            SafetyScorer()
        ]
    
    def _get_default_weights(self) -> Dict[QualityDimension, float]:
        """Get default weights for quality dimensions"""
        return {
            QualityDimension.ACCURACY: 0.25,
            QualityDimension.RELEVANCE: 0.20,
            QualityDimension.COMPLETENESS: 0.15,
            QualityDimension.CLARITY: 0.15,
            QualityDimension.SAFETY: 0.25
        }
    
    async def assess_quality(
        self,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        weights: Optional[Dict[QualityDimension, float]] = None
    ) -> QualityMetrics:
        """Assess quality across all dimensions"""
        dimension_scores = {}
        
        # Run all scorers
        for scorer in self.scorers:
            try:
                score = await scorer.score(data, context)
                dimension_scores[scorer.dimension] = score
            except Exception as e:
                logger.error(f"Quality scorer '{scorer.name}' failed: {e}")
                # Create a low-confidence neutral score
                dimension_scores[scorer.dimension] = QualityScore(
                    dimension=scorer.dimension,
                    score=0.5,
                    confidence=0.1,
                    explanation=f"Scorer failed: {str(e)}"
                )
        
        # Calculate overall score
        effective_weights = weights or self.default_weights
        overall_score = self._aggregate_scores(dimension_scores, effective_weights)
        
        # Create quality metrics
        metrics = QualityMetrics(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            aggregation_method=self.aggregation_method,
            metadata={
                "weights_used": effective_weights,
                "scorers_count": len(self.scorers),
                "assessment_time": time.time()
            }
        )
        
        # Store in history
        self.assessment_history.append(metrics)
        
        # Keep only recent history
        if len(self.assessment_history) > 1000:
            self.assessment_history = self.assessment_history[-1000:]
        
        return metrics
    
    def _aggregate_scores(
        self,
        dimension_scores: Dict[QualityDimension, QualityScore],
        weights: Dict[QualityDimension, float]
    ) -> float:
        """Aggregate dimension scores into overall score"""
        if not dimension_scores:
            return 0.0
        
        if self.aggregation_method == ScoreAggregation.WEIGHTED_AVERAGE:
            total_weight = 0.0
            weighted_sum = 0.0
            
            for dimension, quality_score in dimension_scores.items():
                weight = weights.get(dimension, 1.0)
                confidence = quality_score.confidence
                effective_weight = weight * confidence
                weighted_sum += quality_score.score * effective_weight
                total_weight += effective_weight
            
            return weighted_sum / total_weight if total_weight > 0 else 0.0
        
        elif self.aggregation_method == ScoreAggregation.MINIMUM:
            return min(score.score for score in dimension_scores.values())
        
        elif self.aggregation_method == ScoreAggregation.MAXIMUM:
            return max(score.score for score in dimension_scores.values())
        
        elif self.aggregation_method == ScoreAggregation.MEDIAN:
            scores = [score.score for score in dimension_scores.values()]
            return statistics.median(scores)
        
        elif self.aggregation_method == ScoreAggregation.HARMONIC_MEAN:
            scores = [max(0.001, score.score) for score in dimension_scores.values()]  # Avoid division by zero
            return len(scores) / sum(1/score for score in scores)
        
        else:
            # Default to simple average
            return sum(score.score for score in dimension_scores.values()) / len(dimension_scores)
    
    def get_quality_trends(self, window_size: int = 50) -> Dict[str, Any]:
        """Get quality trends over recent assessments"""
        if len(self.assessment_history) < 2:
            return {}
        
        recent_assessments = self.assessment_history[-window_size:]
        
        # Overall score trend
        overall_scores = [assessment.overall_score for assessment in recent_assessments]
        overall_trend = self._calculate_trend(overall_scores)
        
        # Dimension trends
        dimension_trends = {}
        for dimension in QualityDimension:
            scores = []
            for assessment in recent_assessments:
                if dimension in assessment.dimension_scores:
                    scores.append(assessment.dimension_scores[dimension].score)
            
            if scores:
                dimension_trends[dimension.value] = self._calculate_trend(scores)
        
        return {
            "overall_trend": overall_trend,
            "dimension_trends": dimension_trends,
            "assessment_count": len(recent_assessments),
            "time_span": recent_assessments[-1].timestamp - recent_assessments[0].timestamp
        }
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend statistics for a series of values"""
        if len(values) < 2:
            return {"direction": "stable", "change": 0.0}
        
        # Simple linear trend
        n = len(values)
        x = list(range(n))
        
        # Calculate slope using least squares
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine trend direction
        if abs(slope) < 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "improving"
        else:
            direction = "declining"
        
        return {
            "direction": direction,
            "slope": slope,
            "change": values[-1] - values[0],
            "average": y_mean,
            "min": min(values),
            "max": max(values)
        }
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get comprehensive quality statistics"""
        if not self.assessment_history:
            return {}
        
        overall_scores = [assessment.overall_score for assessment in self.assessment_history]
        
        # Dimension statistics
        dimension_stats = {}
        for dimension in QualityDimension:
            scores = []
            confidences = []
            
            for assessment in self.assessment_history:
                if dimension in assessment.dimension_scores:
                    score_obj = assessment.dimension_scores[dimension]
                    scores.append(score_obj.score)
                    confidences.append(score_obj.confidence)
            
            if scores:
                dimension_stats[dimension.value] = {
                    "average": statistics.mean(scores),
                    "median": statistics.median(scores),
                    "min": min(scores),
                    "max": max(scores),
                    "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
                    "average_confidence": statistics.mean(confidences),
                    "sample_count": len(scores)
                }
        
        return {
            "total_assessments": len(self.assessment_history),
            "overall_average": statistics.mean(overall_scores),
            "overall_median": statistics.median(overall_scores),
            "overall_min": min(overall_scores),
            "overall_max": max(overall_scores),
            "overall_std_dev": statistics.stdev(overall_scores) if len(overall_scores) > 1 else 0,
            "dimension_statistics": dimension_stats,
            "assessment_period": {
                "start": self.assessment_history[0].timestamp,
                "end": self.assessment_history[-1].timestamp,
                "duration": self.assessment_history[-1].timestamp - self.assessment_history[0].timestamp
            }
        }

# Global quality assessment engine
_quality_engine: Optional[QualityAssessmentEngine] = None

def get_quality_engine() -> QualityAssessmentEngine:
    """Get global quality assessment engine"""
    global _quality_engine
    if _quality_engine is None:
        _quality_engine = QualityAssessmentEngine()
    return _quality_engine

async def assess_agent_output_quality(
    agent_output: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> QualityMetrics:
    """Convenience function to assess agent output quality"""
    engine = get_quality_engine()
    return await engine.assess_quality(agent_output, context)
