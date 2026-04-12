import os
from typing import Dict, Optional
from datetime import datetime, timedelta
from logger import get_logger

logger = get_logger("metrics")

TOKEN_PRICING = {
    "gemini-2.5-pro-preview-0506": {
        "input": 1.25,
        "output": 10.0,
        "unit": "per_million"
    },
    "gemini-2.5-flash": {
        "input": 0.15,
        "output": 0.60,
        "unit": "per_million"
    },
    "gemini-2.0-flash": {
        "input": 0.075,
        "output": 0.30,
        "unit": "per_million"
    },
    "meta-llama/llama-4-scout": {
        "input": 0.50,
        "output": 2.50,
        "unit": "per_million"
    },
    "meta-llama/llama-3.3-70b-instruct": {
        "input": 0.88,
        "output": 0.88,
        "unit": "per_million"
    },
    "google/gemma-3n-e4": {
        "input": 0.10,
        "output": 0.10,
        "unit": "per_million"
    },
    "google/gemma-3-27b-it": {
        "input": 0.20,
        "output": 0.20,
        "unit": "per_million"
    },
}

DAILY_BUDGET_LIMIT = 2.0


class CostTracker:
    def __init__(self):
        self.run_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "models_used": {},
            "start_time": datetime.now()
        }
    
    def track_request(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Track an AI API request and calculate cost."""
        self.run_stats["total_requests"] += 1
        self.run_stats["successful_requests"] += 1
        self.run_stats["total_input_tokens"] += input_tokens
        self.run_stats["total_output_tokens"] += output_tokens
        
        pricing = TOKEN_PRICING.get(model)
        if pricing:
            input_cost = (input_tokens / 1_000_000) * pricing["input"]
            output_cost = (output_tokens / 1_000_000) * pricing["output"]
            request_cost = input_cost + output_cost
            self.run_stats["total_cost"] += request_cost
            
            if model not in self.run_stats["models_used"]:
                self.run_stats["models_used"][model] = {"requests": 0, "cost": 0.0}
            self.run_stats["models_used"][model]["requests"] += 1
            self.run_stats["models_used"][model]["cost"] += request_cost
            
            logger.debug(f"    {model}: {input_tokens} in, {output_tokens} out, ${request_cost:.4f}")
    
    def track_failure(self, model: str) -> None:
        """Track a failed API request."""
        self.run_stats["total_requests"] += 1
        self.run_stats["failed_requests"] += 1
        
        if model not in self.run_stats["models_used"]:
            self.run_stats["models_used"][model] = {"requests": 0, "cost": 0.0, "failures": 0}
        if "failures" not in self.run_stats["models_used"][model]:
            self.run_stats["models_used"][model]["failures"] = 0
        self.run_stats["models_used"][model]["failures"] += 1
    
    def get_current_cost(self) -> float:
        """Get current run's total cost."""
        return self.run_stats["total_cost"]
    
    def is_over_budget(self) -> bool:
        """Check if we've exceeded the daily budget."""
        return self.run_stats["total_cost"] >= DAILY_BUDGET_LIMIT
    
    def should_continue(self) -> bool:
        """Determine if pipeline should continue based on budget."""
        remaining = DAILY_BUDGET_LIMIT - self.run_stats["total_cost"]
        if remaining <= 0:
            logger.warning(f"Budget exhausted (${self.run_stats['total_cost']:.2f}/{DAILY_BUDGET_LIMIT}), stopping early")
            return False
        
        if remaining < 0.50:
            logger.warning(f"Low budget remaining (${remaining:.2f}), may stop early")
        
        return True
    
    def get_summary(self) -> Dict:
        """Get run summary for logging."""
        duration = (datetime.now() - self.run_stats["start_time"]).total_seconds()
        return {
            "duration_seconds": round(duration, 1),
            "total_requests": self.run_stats["total_requests"],
            "successful": self.run_stats["successful_requests"],
            "failed": self.run_stats["failed_requests"],
            "total_input_tokens": self.run_stats["total_input_tokens"],
            "total_output_tokens": self.run_stats["total_output_tokens"],
            "total_cost_usd": round(self.run_stats["total_cost"], 4),
            "models": self.run_stats["models_used"]
        }
    
    def log_summary(self) -> None:
        """Log the cost summary."""
        summary = self.get_summary()
        logger.info(f"Cost Summary: ${summary['total_cost_usd']} | {summary['total_requests']} requests | {summary['duration_seconds']}s")
        
        for model, stats in summary["models"].items():
            logger.info(f"  {model}: {stats.get('requests', 0)} req, ${round(stats.get('cost', 0), 4)}")


cost_tracker = CostTracker()


def estimate_tokens(text: str) -> int:
    """Rough token estimation (approx 4 chars per token)."""
    return len(text) // 4


def track_api_call(model: str, input_text: str, output_text: str) -> None:
    """Convenience function to track an API call."""
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    cost_tracker.track_request(model, input_tokens, output_tokens)