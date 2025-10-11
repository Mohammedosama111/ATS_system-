"""Deprecated module: token counting removed from system.

Left in place as a no-op to avoid import errors if any stale references remain.
Will be safe to delete once confirmed unused across all deployments.
"""

class TokenUsage:  # minimal placeholder
    def __init__(self, *_, **__):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

def compute_usage(*_, **__):  # no-op
    return TokenUsage()

def summarize_prompt(*parts, **_):
    return ""
