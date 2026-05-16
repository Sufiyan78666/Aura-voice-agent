import os
from typing import Any, Optional, Callable
from functools import wraps

# Try to import Langfuse v4+ components
try:
    from langfuse import Langfuse, observe
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    # Dummy decorator if library is missing
    def observe(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        def decorator(func):
            return func
        return decorator

class LangfuseManager:
    def __init__(self):
        self.enabled = os.environ.get("LANGFUSE_ENABLED", "1").lower() in ("1", "true", "yes")
        self.public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        self.secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
        self.host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com"
        
        self.debug = os.environ.get("OBS_DEBUG", "0") == "1"
        self.client = None

        if self.enabled and LANGFUSE_AVAILABLE:
            self._init_client()

    def _init_client(self):
        if not self.public_key or not self.secret_key:
            return

        try:
            # Initializing Langfuse() in v4 sets up the global tracing context
            self.client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host
            )
            print(f"✅ Observability: Langfuse v4 initialized (Host: {self.host})")
        except Exception as e:
            print(f"❌ Observability: Langfuse v4 initialization failed: {e}")

    def log_generation(self, name: str, model: str, input_text: str, output_text: str, metadata: dict = None, duration_ms: float = None):
        """
        Legacy support for imperative logging. In v4, we prefer using @observe decorator.
        """
        pass

    def update_usage(self, input_tokens: int, output_tokens: int, model: str = None):
        if not self.client: return
        try:
            # In v4 OTel SDK, the argument is 'usage_details'
            self.client.update_current_generation(
                usage_details={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens
                },
                model=model
            )
        except Exception as e:
            print(f"⚠️  Observability: Failed to update usage: {e}")

    def add_score(self, name: str, value: float, comment: str = None):
        if not self.client: return
        try:
            # Try to get trace_id from current context
            trace_id = self.client.get_current_trace_id()
            if self.debug:
                print(f"🔍 Obs Debug: Scoring attempt | TraceID: {trace_id} | Name: {name}")
                
            if trace_id:
                self.client.create_score(
                    trace_id=trace_id,
                    name=name,
                    value=value,
                    comment=comment
                )
            else:
                # Fallback to current trace context
                self.client.score_current_trace(
                    name=name,
                    value=value,
                    comment=comment
                )
        except Exception as e:
            print(f"⚠️  Observability: Failed to add score: {e}")

    def flush(self):
        if self.client:
            try:
                self.client.flush()
            except:
                pass

# Global instance
obs = LangfuseManager()
# Export the decorator for use in voice_agent.py
observe_v4 = observe
