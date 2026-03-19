## Kimi (Moonshot) – Prompting Guidance for Gerald

This file teaches you how to get the best results when using Kimi models via OpenClaw. Read this when:

- You are routed to a `moonshot/kimi-*` model, or
- The human explicitly asks you to “use Kimi” or “switch to Kimi”.

Keep this guidance in mind alongside `KIMI-SETUP.md` (which covers API keys and gateway config).

---

## 1. Core principle – be explicit and detailed

Kimi cannot read your mind. The less it has to guess, the better the results.

- **State the task clearly** (summarize, draft email, write code, analyze logs, etc.).
- **Include key constraints** (tone, audience, length limit, format).
- **Provide all relevant context** (inputs, prior discussion, reference docs).

When a Kimi response is off:

- If it is **too long**: ask for a brief answer or a hard token/word/paragraph limit.
- If it is **too simple**: ask for “expert-level” or “senior-level” reasoning.
- If the **format is wrong**: show an example of the exact format you want.

---

## 2. Use roles and system prompts intentionally

Kimi responds better when you explicitly give it a role and high‑level behavior.

- **For Gerald**: when you call Kimi, ensure the system message clearly sets:
  - The role (e.g., “You are Gerald, an AI operator for OpenClaw…” or a more specific expert role).
  - Safety and style constraints.
  - Any domain‑specific expectations (e.g., “optimize for correctness over speed”, “prefer concise bullet summaries”, etc.).

**Pattern: role + user**

- System: “You are Kimi, an assistant for \<domain\>. You will provide safe, helpful, and accurate answers. Prefer concise, structured output.”
- User: the concrete task (with context, examples, and constraints).

Use the system prompt to:

- Set non‑negotiable rules (safety, refusal behavior, style defaults).
- Pin Kimi to a specific persona (e.g., senior engineer, sales coach, analyst).

---

## 3. Structure inputs with delimiters

Kimi handles multi‑part inputs better if you clearly separate the parts. Use:

- Triple quotes (`"""..."""`)
- XML‑style tags (`<article>...</article>`)
- Section headings (`## Input`, `## Instructions`, etc.)

When routing data from tools or files:

- Wrap each logical unit (article, transcript, log chunk) in clear delimiters.
- In the system message, describe exactly how to treat each delimited section (e.g., “You will receive two articles separated by `<article>` tags. First summarize each, then compare them.”).

This is especially important when:

- Comparing or ranking multiple items.
- Mixing **instructions** and **raw data** (tell Kimi which is which).

---

## 4. Spell out step‑by‑step behavior

For multi‑step tasks, Kimi performs better when you explicitly list the steps you want it to follow.

Examples of good step patterns:

- “Follow these steps:
  1. Read the user’s text (inside triple quotes).
  2. Produce a one‑sentence summary prefixed with `Summary:`.
  3. Translate that summary into English prefixed with `Translation:`.”

Guidelines:

- Put step lists in the **system** or lead‑in instruction so they apply to the whole turn.
- Use numbered steps and clear prefixes in the desired output.
- For more complex orchestrations, have Kimi **first classify** the task, then branch into more specific instructions based on that classification.

---

## 5. Use examples (“few‑shot” prompting)

When the style or behavior you want is hard to describe, show Kimi a couple of examples and ask it to imitate them.

Patterns:

- System: “Respond in a consistent style.”
- User: “Here is an example input and the kind of answer I want: … Now answer the new query in the same style.”

Tips:

- Keep examples short but representative.
- Highlight the parts of the output that matter (structure, tone, level of detail).
- Reuse the same examples when you want consistent behavior across requests.

---

## 6. Control length and structure

Kimi will usually respect **high‑level** length and structure constraints.

Good constraints:

- “Two sentences.”
- “One short paragraph.”
- “3–5 bullet points.”
- “Under 500 words.”

Less reliable:

- Exact word counts (“exactly 53 words”) – treat these as soft constraints.

When using Kimi via Gerald:

- Ask for output formats that are easy for Gerald to post‑process (e.g., JSON, bullet lists with stable labels, markdown tables when appropriate).
- Prefer **fixed schemas** (e.g., “Respond as JSON with fields `summary`, `actions`, `risks`.”) when the result will be parsed by tools.

---

## 7. Ground Kimi in reference text

Kimi works best when anchored to specific, trustworthy sources.

Best practice:

- Provide reference text (docs, transcripts, logs) and explicitly tell Kimi:
  - To **base its answer only** on that text, and
  - What to do if the answer is missing (e.g., “Say `I can't find the answer in the provided text.`”).

When you (Gerald) call Kimi with external sources:

- Clearly separate **instructions** from **reference text** using delimiters.
- Limit each call to the minimum relevant context to avoid diluting the signal.
- Encourage Kimi to quote or point to specific parts of the reference text when justifying answers.

---

## 8. Break down complex / long‑horizon work

For big tasks (long dialogs, books, large documents, multi‑step workflows), split work into stages:

- **Classification first**: Have Kimi classify the user’s request (e.g., “bug report”, “feature request”, “troubleshooting”, etc.), then apply tailored instructions per class.
- **Summarization over time**:
  - For long conversations, summarize earlier segments once a threshold is reached and pass the running summary forward as part of the system message.
  - For long documents, summarize chapter‑by‑chapter, then summarize the summaries to build a hierarchy.

For Gerald:

- Use Kimi to:
  - Summarize long histories (chat logs, meeting transcripts) into a concise state you can carry forward.
  - Chunk large inputs (e.g., chapters, sections) and aggregate results.
- Be explicit when asking for “summary of summaries” vs. “fresh read of full text”.

---

## 9. Using Kimi’s vision capabilities (images & video)

Kimi vision models (including `moonshot-v1-*-vision-preview` and `kimi-k2.5`) can understand images and, for `kimi-k2.5`, video content as well.

High‑level rules for Gerald:

- Use vision when the task **depends on visual content** (screenshots, diagrams, UI mocks, whiteboards, photos, or short videos).
- Always respect file size and resolution guidelines to avoid unnecessary token and latency costs.
- Be strict about using the **structured content format** for images/videos (do not JSON‑stringify the content array).

### Supplying images via base64

When the human or a tool gives you an image file:

- Encode it as base64 and set `type: "image_url"` with:
  - `image_url.url = "data:image/<ext>;base64,<BASE64_BYTES>"`
- Put the image and any text instructions together in the same user message as a **list**:
  - `{"role": "user", "content": [ { "type": "image_url", ... }, { "type": "text", "text": "Describe the content..." } ] }`

Key pitfalls to avoid:

- **Do not** serialize the list to a string and drop it into `content`; Kimi expects `content` to be a JSON array of parts, not a JSON string.
- Keep resolution at or below **4k** (4096×2160). Larger images cost more tokens and time without improving understanding.

### Supplying images/videos via upload (file IDs)

For large or frequently reused media:

- Upload the file once (image or video) and reference it with `ms://<file-id>`:
  - Images: `type: "image_url"`, `image_url.url: "ms://<file-id>"`
  - Video: `type: "video_url"`, `video_url.url: "ms://<file-id>"`
- Use uploads when:
  - The media is large (especially video).
  - You expect to reference the same media multiple times across turns.

Guidelines:

- Recommended max resolution:
  - Images: ≤ 4k.
  - Video: ≤ 2k (2048×1080).
- Follow Moonshot’s file size limits and request body limit (~100MB per request).

### Costs, tokens, and limitations

- Vision tokens are calculated dynamically:
  - More pixels and more video key frames → more tokens.
  - Use the estimate‑tokens API when you need to predict cost.
- Pricing follows the same model as the `moonshot-v1` series; see Moonshot’s pricing docs.
- Supported formats:
  - Images: `png`, `jpeg`, `webp`, `gif`
  - Video: `mp4`, `mpeg`, `mov`, `avi`, `x-flv`, `mpg`, `webm`, `wmv`, `3gpp`
- Not supported:
  - Raw HTTP/HTTPS image URLs in `image_url.url` – use base64 or `ms://<file-id>` instead.

When using vision with `kimi-k2.5`, prefer leaving advanced sampling parameters (temperature, top_p, penalties, `n`, `thinking`) at their documented defaults; non‑default values may be rejected.

---

## 10. Using Kimi’s built‑in web search (`$web_search`)

Kimi provides a built‑in internet search tool called `$web_search`. It is implemented **inside** Kimi and uses the standard tool‑call flow:

- You declare a tool with:
  - `type: "builtin_function"`
  - `function.name: "$web_search"`
- Kimi decides when to call `$web_search` and returns a `tool_calls` message with JSON arguments.
- Your code (or Gerald) **does not run the search itself** – you simply pass those arguments back to Kimi as a `tool` role message, and Kimi performs the actual search and summarization.

**Key behaviors to remember:**

- `$web_search` can be mixed with your own tools (`type: "function"`) in the same `tools` list.
- The `search_impl` handler on your side can just `return arguments` unchanged when using Kimi’s built‑in search.
- If you later want to replace Kimi’s search with your own, you:
  - Redefine the tool (new `function.name`, description, parameters).
  - Change `search_impl` to actually call your own search + crawl code, keeping the same signature.

### Token usage and cost

Web search can be **token‑heavy**:

- Search results content is included in `prompt_tokens`.
- Kimi exposes `usage.total_tokens` inside the `$web_search` arguments so you can see how many tokens the search results contributed.
- After the full run, `completion.usage` reports:
  - `prompt_tokens` (including search results),
  - `completion_tokens`,
  - `total_tokens`.

Best practices for Gerald:

- Treat web search as an **expensive capability**:
  - Only enable it when the task truly needs fresh web knowledge.
  - Prefer narrower queries and fewer results when possible.
- Surface or log search token usage when helpful, so the human can see cost patterns.

### Model choice with web search

Because `$web_search` can dramatically increase token counts:

- Prefer a **dynamic, large‑context model** such as `kimi-k2-turbo-preview` when web search is enabled to reduce the risk of “input token length too long” errors.
- If a smaller‑context model fails due to context window limits when search is on, suggest switching to `kimi-k2-turbo-preview` for that interaction.

### Combining `$web_search` with other tools

- You can declare both:
  - `type: "builtin_function", function.name: "$web_search"`
  - and your own `type: "function"` tools in the same request.
- Kimi may interleave:
  - Web search calls (`$web_search`) and
  - Your own tools (e.g., DB lookups, internal APIs).

When orchestrating tools:

- Let Kimi decide **when** web search is needed based on instructions (e.g., “Use web search only when the answer is likely to depend on up‑to‑date external information.”).
- Encourage it to:
  - Check local / internal sources first (your tools, documents) when freshness is not required.
  - Use `$web_search` as a fallback or complement, not the default for everything.

---

## 11. When Kimi is a good choice

You should favor Kimi when:

- The task needs **strong general‑purpose reasoning** across English and Chinese.
- You want **structured outputs** from complex or noisy inputs (long docs, transcripts).
- You’re doing **multi‑step analysis** where clear instructions and reference text are available.

If the human or OpenClaw defaults to another model but explicitly opts into Kimi, **read this file once for the session and follow it** for subsequent Kimi calls.

---

## 12. Adapting this guidance as we learn

This file is a living doc. When we learn new patterns about how Kimi behaves in production:

- Add short, concrete rules (e.g., “For code explanations, always ask for line ranges and language up front.”).
- Prefer **simple, reusable patterns** over one‑off tricks.
- Keep examples current with the Kimi versions configured in OpenClaw.

When in doubt, err on the side of:

- Clear roles
- Structured inputs
- Explicit steps
- Grounding in reference text

