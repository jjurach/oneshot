# Direct Executor Architecture and LangChain/LangGraph Integration Design

## Overview

The "direct" executor provider allows oneshot to make direct HTTP calls to OpenAI-compatible API endpoints, enabling integration with:

- Local models (Ollama, llama-cpp-python, etc.)
- Commercial APIs (OpenAI, Anthropic, Google, Groq, etc.)
- Self-hosted LLM services
- Custom model servers

This document outlines the current architecture and proposes LangChain/LangGraph integration for advanced capabilities like:

- Context augmentation and retrieval (RAG)
- Tool/function calling with predefined tools
- Multi-step reasoning chains
- State management across iterations

## Current Architecture

### Direct Provider Implementation

Located in: `src/oneshot/providers/__init__.py`

**Core Components:**

1. **ProviderConfig** - Configuration dataclass
   - `provider_type`: "direct" (vs "executor")
   - `endpoint`: API endpoint URL
   - `model`: Model name
   - `api_key`: Optional API key for authentication
   - `timeout`: Request timeout in seconds

2. **DirectProvider** - Implementation class
   - `generate(prompt)`: Synchronous API call
   - `generate_async(prompt)`: Asynchronous API call
   - `_prepare_request()`: Builds OpenAI-compatible request
   - `_extract_response()`: Parses API response

**OpenAI Compatibility:**

The DirectProvider expects OpenAI-compatible API format:

```python
Request:
POST /v1/chat/completions
{
  "model": "model-name",
  "messages": [{"role": "user", "content": "..."}]
}

Response:
{
  "choices": [{"message": {"content": "..."}}]
}
```

### Supported Endpoints

- **Ollama**: `http://localhost:11434/v1/chat/completions`
- **OpenAI**: `https://api.openai.com/v1/chat/completions`
- **Anthropic Claude (via bedrock)**: AWS endpoints
- **Google Generative AI**: `https://generativelanguage.googleapis.com/v1/models/...`
- **Groq**: `https://api.groq.com/openai/v1/chat/completions`
- **Local llama-cpp-python**: `http://localhost:8000/v1/chat/completions`

## Proposed LangChain/LangGraph Integration

### Phase 1: Tool Extension Framework

**Objective:** Enable oneshot to use tools/functions when calling LLMs

**Design:**

```python
class DirectProviderWithTools(DirectProvider):
    """Extended DirectProvider with tool calling capability."""

    def __init__(self, config: ProviderConfig, tools: List[Tool] = None):
        super().__init__(config)
        self.tools = tools or []

    def register_tool(self, tool: Tool):
        """Register a callable tool."""
        self.tools.append(tool)

    def _prepare_request_with_tools(self, prompt: str) -> Dict:
        """Prepare request with tools/functions for APIs that support it."""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "tools": self._convert_tools_to_openai_format(),
            "tool_choice": "auto"
        }
        return payload, headers

    def _convert_tools_to_openai_format(self) -> List[Dict]:
        """Convert Tool objects to OpenAI functions format."""
        # Maps custom Tool objects to OpenAI schema
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema
                }
            }
            for tool in self.tools
        ]

    def _handle_tool_calls(self, response: Dict) -> str:
        """Execute tool calls from LLM response."""
        # Parse tool_calls from response
        # Execute corresponding tools
        # Format results for next iteration
        pass
```

**Supported Tools:**

```python
@dataclass
class Tool:
    """Base tool definition."""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    callable: Callable

# Built-in tools:
- SearchTool (web search, local search)
- FileTool (read/write files, execute scripts)
- CalculatorTool (mathematical calculations)
- ShellTool (execute shell commands with sandboxing)
- DatabaseTool (query databases)
- APITool (make HTTP requests to external APIs)
```

### Phase 2: Context Augmentation (RAG)

**Objective:** Provide retrieved context from external sources to enhance LLM responses

**Design:**

```python
class ContextAugmentedDirectProvider(DirectProviderWithTools):
    """DirectProvider with context retrieval and augmentation."""

    def __init__(self, config: ProviderConfig, context_source: ContextSource = None):
        super().__init__(config)
        self.context_source = context_source

    def generate_augmented(self, prompt: str, context_queries: List[str] = None) -> str:
        """Generate with retrieved context."""
        # Determine what context is needed
        queries = context_queries or self._extract_context_queries(prompt)

        # Retrieve context from source
        context = self.context_source.retrieve(queries)

        # Build augmented prompt
        augmented_prompt = self._build_augmented_prompt(prompt, context)

        # Generate response
        return self.generate(augmented_prompt)

    def _build_augmented_prompt(self, original: str, context: List[str]) -> str:
        """Combine original prompt with retrieved context."""
        context_text = "\n".join(f"Source {i}: {c}" for i, c in enumerate(context))
        return f"""
Use the following context to answer the question:

{context_text}

Question: {original}
"""
```

**Supported Context Sources:**

```python
class ContextSource(ABC):
    """Abstract base for context retrieval."""

    @abstractmethod
    def retrieve(self, queries: List[str]) -> List[str]:
        """Retrieve context for given queries."""
        pass

# Implementations:
- LocalVectorStore (ChromaDB, Milvus, Faiss)
- WebSearch (DuckDuckGo, Google Custom Search)
- LocalFiles (directory scanning, markdown parsing)
- CodeRepository (git repo analysis, semantic search)
- Database (SQL queries, semantic search)
```

### Phase 3: LangGraph State Machine

**Objective:** Manage complex multi-step reasoning with state persistence

**Design:**

```python
class OnehotLangGraph:
    """LangGraph-based state machine for oneshot tasks."""

    def __init__(self, provider: DirectProvider):
        self.provider = provider
        self.graph = StateGraph(OnehotState)

    def build_graph(self):
        """Construct reasoning graph."""
        # Define nodes
        self.graph.add_node("worker", self.worker_node)
        self.graph.add_node("auditor", self.auditor_node)
        self.graph.add_node("tool_executor", self.tool_executor_node)
        self.graph.add_node("context_retriever", self.context_retriever_node)

        # Define edges with conditional routing
        self.graph.add_edge("START", "worker")
        self.graph.add_conditional_edges(
            "worker",
            self.route_after_worker,
            {
                "needs_tools": "tool_executor",
                "needs_context": "context_retriever",
                "audit": "auditor"
            }
        )
        self.graph.add_edge("tool_executor", "worker")
        self.graph.add_edge("context_retriever", "worker")
        self.graph.add_conditional_edges(
            "auditor",
            self.route_after_audit,
            {"done": "END", "reiterate": "worker"}
        )

        return self.graph.compile()

    def route_after_worker(self, state: OnehotState) -> str:
        """Determine next step after worker generates output."""
        # Check if worker requested tools
        if state.needs_tool_call:
            return "needs_tools"
        # Check if more context needed
        elif state.needs_context:
            return "needs_context"
        # Otherwise proceed to audit
        else:
            return "audit"
```

**State Definition:**

```python
@dataclass
class OnehotState:
    """State for oneshot reasoning process."""
    iteration: int
    prompt: str
    worker_output: str
    auditor_output: Optional[str]
    extracted_json: Optional[Dict]
    tool_calls: List[Dict]
    context_items: List[str]
    verdict: Optional[str]
    needs_tool_call: bool = False
    needs_context: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Phase 4: Context Augmentation Strategy

**When to Retrieve Context:**

1. **Explicit requests** - LLM asks for information via tool call
2. **Semantic similarity** - Prompt contains keywords matching indexed content
3. **Iteration feedback** - Auditor feedback indicates missing information
4. **Automatic** - First iteration of complex tasks

**Storage Format:**

Context retrieved is stored in session logs:

```json
{
  "metadata": {
    "context_sources": ["local_files", "web_search"]
  },
  "iterations": [
    {
      "iteration": 1,
      "context_retrieved": [
        {"source": "web_search", "query": "...", "result": "..."},
        {"source": "local_files", "query": "...", "result": "..."}
      ],
      "worker_output": "...",
      "auditor_output": "..."
    }
  ]
}
```

## Integration Roadmap

### Current (Implemented)
- ✅ DirectProvider for API calls
- ✅ OpenAI-compatible endpoint support
- ✅ Session logging with metadata
- ✅ Configurable logs directory

### Phase 1 (Tool Extension)
- [ ] Implement Tool base class
- [ ] Add tool registration system
- [ ] OpenAI function calling support
- [ ] Error handling for tool execution
- [ ] Tool result parsing

### Phase 2 (Context Augmentation)
- [ ] ContextSource abstraction
- [ ] Vector store integration (ChromaDB)
- [ ] Web search integration
- [ ] Local file indexing
- [ ] Context prompt building

### Phase 3 (LangGraph)
- [ ] StateGraph nodes definition
- [ ] Conditional routing logic
- [ ] State persistence in logs
- [ ] Tool call parsing
- [ ] Context retrieval triggering

### Phase 4 (Advanced Features)
- [ ] Multi-turn conversation management
- [ ] Plan generation and execution
- [ ] Recursive task decomposition
- [ ] Error recovery strategies

## API Examples

### Basic Usage (Current)
```python
from oneshot.providers import DirectProvider, ProviderConfig

config = ProviderConfig(
    provider_type="direct",
    endpoint="http://localhost:11434/v1/chat/completions",
    model="llama-pro"
)
provider = DirectProvider(config)
response = provider.generate("What is 2+2?")
```

### With Tools (Phase 1)
```python
from oneshot.providers import DirectProviderWithTools
from oneshot.tools import Tool, ShellTool, SearchTool

tools = [
    ShellTool(sandbox=True, allowed_commands=["ls", "grep"]),
    SearchTool()
]

provider = DirectProviderWithTools(config, tools=tools)
response = provider.generate("Find Python files and count lines")
```

### With Context (Phase 2)
```python
from oneshot.providers import ContextAugmentedDirectProvider
from oneshot.context import LocalFileContextSource

context_source = LocalFileContextSource("./docs")

provider = ContextAugmentedDirectProvider(config, context_source=context_source)
response = provider.generate_augmented("Explain our architecture")
```

### With LangGraph (Phase 3)
```python
from oneshot.langgraph_integration import OnehotLangGraph

graph_manager = OnehotLangGraph(provider)
compiled_graph = graph_manager.build_graph()

# Graph handles state, tool calls, context retrieval automatically
state = compiled_graph.invoke({
    "iteration": 1,
    "prompt": "Complex task requiring tools and context"
})
```

## Testing Strategy

### Unit Tests
- Test OpenAI format conversion
- Test response parsing
- Test error handling
- Test tool registration
- Test context retrieval

### Integration Tests
- Test with real Ollama instance
- Test with OpenAI API
- Test tool execution
- Test context augmentation
- Test LangGraph state transitions

### E2E Tests
- Complete oneshot workflows with tools
- Context-augmented reasoning
- Multi-iteration state management
- Error recovery

## Performance Considerations

1. **API Call Caching** - Cache responses for identical prompts
2. **Context Retrieval** - Batch queries, reuse embeddings
3. **Tool Execution** - Parallel execution where safe
4. **State Serialization** - Efficient JSON for session logs
5. **Memory Management** - Limit context window growth

## Security Considerations

1. **Tool Sandboxing** - Restrict shell commands, file access
2. **API Key Management** - Secure storage, no logging
3. **Context Privacy** - No sensitive data in logs
4. **Tool Validation** - Verify tool outputs before using
5. **Rate Limiting** - Prevent API quota abuse

## Future Enhancements

1. **Multi-Provider Chains** - Route between different LLMs
2. **Parallel Execution** - Run multiple worker/auditor pairs
3. **Caching Layer** - Redis-backed response cache
4. **Monitoring** - Prometheus metrics for performance tracking
5. **Custom Prompts** - Pluggable system prompts per executor
