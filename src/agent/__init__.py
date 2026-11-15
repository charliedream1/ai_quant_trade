"""Compatible domain exports loaded only when requested."""

from importlib import import_module

EXPORTS = {
    "GenericAgentRuntime": (".generic_agent_runtime", "GenericAgentRuntime"),
    "LLMClient": (".llm_client", "LLMClient"),
    "RAGService": (".rag", "RAGService"),
}

__all__ = ["GenericAgentRuntime", "LLMClient", "RAGService"]


def __getattr__(name):
    if name not in EXPORTS:
        raise AttributeError(name)
    module, symbol = EXPORTS[name]
    value = getattr(import_module(module, __name__), symbol)
    globals()[name] = value
    return value
