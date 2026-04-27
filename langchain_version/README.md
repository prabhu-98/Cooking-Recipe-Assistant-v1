# LangChain Version — Cooking Recipe Assistant
# This is an ALTERNATIVE implementation using the LangChain framework.
# The main project (parent directory) uses a custom agentic loop.

## How to Run

```bash
cd langchain_version
python langchain_agent.py
```

## Key Differences: Custom vs LangChain

| Aspect | Custom (Main Project) | LangChain (This Folder) |
|:-------|:---------------------|:-----------------------|
| Tool Definition | Hand-written JSON schemas (TOOLS list) | `@tool` decorator auto-generates schemas |
| LLM Client | Raw `Groq()` SDK | `ChatGroq()` LangChain wrapper |
| Agentic Loop | Manual `while` loop (~40 lines) | `AgentExecutor` (1 line: `.invoke()`) |
| Tool Execution | Manual `TOOL_MAP` dispatch | AgentExecutor handles automatically |
| Memory | Manual `messages` list | `chat_history` via MessagesPlaceholder |
| Dependencies | 6 packages | 10+ packages (langchain, langchain-groq, etc.) |
| Transparency | Full visibility of every step | Abstracted behind framework |
| Control | Complete control over retry logic | Limited to AgentExecutor options |

## Why the Main Project Uses Custom Code Instead of LangChain

1. **Fewer dependencies** — 6 vs 10+ packages
2. **Full transparency** — Every step of the agentic loop is visible and debuggable
3. **Demonstrates understanding** — Shows HOW tool-calling works, not just that we can call a library
4. **More control** — Custom retry logic for Groq's tool_use_failed errors
5. **Simpler** — For 7 tools and one agent, LangChain is overkill
