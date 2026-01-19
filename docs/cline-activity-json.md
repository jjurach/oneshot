# Cline Activity JSON Output

In the context of Cline (formerly Claude Dev), the `--output-format json` (often piped or streamed as JSON Lines) is designed to make the agent's internal state and communication "machine-readable" for automation and CLI integration.

## The ClineMessage Schema

The information streamed is not a "global standard" (like a W3C spec), but it is a documented internal schema specific to the Cline ecosystem. It follows a JSON Lines (JSONL) pattern where each discrete event is a self-contained JSON object on a new line.

| Field    | Type    | Description                                                               |
| :------- | :------ | :------------------------------------------------------------------------ |
| `type`     | `string`  | The category: `"ask"` (requires input) or `"say"` (informational).          |
| `text`     | `string`  | The human-readable content of the message.                                |
| `ts`       | `number`  | Unix epoch timestamp in milliseconds.                                     |
| `say / ask`| `string`  | The specific sub-type (e.g., `"text"`, `"command"`, `"tool_use"`, `"api_req_started"`). |
| `partial`  | `boolean` | `true` if this is a chunk of a streaming message; `false` or omitted if final. |
| `reasoning`| `string`  | Internal "Chain of Thought" from the LLM (often omitted in final views).    |

## Where is it defined in the Source Code?

If you are looking at the Cline GitHub repository, the logic that decides which properties are packed into these JSON objects is located in the Task Management and CLI Handling modules.

**Primary Logic:**
- `src/cli/main.go` and `src/task/manager.go` (if looking at the Go-based CLI)
- `src/core/Cline.ts` (in the TypeScript core)

**The "Decision" Module:**
The formatting logic usually resides in a "view" or "formatter" helper. Specifically, look for:
- `src/shared/WebviewMessage.ts` – Defines the TypeScript interfaces for messages.
- `src/api/transform/` – Where raw LLM responses are parsed into the "Say/Ask" format.

**Property Selection:**
The properties are decided by the `ClineMessage` interface. When the CLI flag is set, the `taskManager` bypasses the "Rich" (terminal UI) formatter and passes the raw message object to a JSON encoder.

## How to Interpret the Stream (Clues for the User)

To help a user (or another script) interpret this information, look for these three key "markers" in the stream:
- The "Partial... (The rest of this point was truncated in the original, so I'll leave it as is to avoid fabricating content.)