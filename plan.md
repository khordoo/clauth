# CLAUTH CLI Modernization Plan

## Current UX Assessment
- Visual language mixes Typer `secho`, Rich markup, plain `print`, and emoji, resulting in inconsistent tone and alignment across commands.
- Figlet banner plus dense paragraphs overwhelm small terminals and diverge from contemporary minimalist CLI aesthetics.
- Step messaging (e.g., "Step 1/3") lacks consistent framing or persistent context, making flows feel linear but unguided.
- Interactive menus rely on default InquirerPy styling; instructions repeat per prompt, pointer symbols shift, and spacing is uneven.
- Status/progress feedback alternates between raw `console.status`, bare `print`, and manual newlines; there is no single success/warning/error pattern.
- Screen transitions are ad-hoc: `clear_screen()` is only used before launching Claude, leaving earlier steps to scroll off-screen and bury essential feedback.

## Proposed Design System

### Color Palette
Create `clauth/ui/theme.py` with semantic tokens so every command shares the same palette.

| Token | Purpose | Suggested Value |
| --- | --- | --- |
| `background` | Terminal base | terminal default |
| `text_primary` | Standard copy | `"white"` |
| `text_muted` | Helper copy | `"grey70"` |
| `accent` | Primary highlight | `"medium_purple3"` (`#6C5CE7`) |
| `accent_alt` | Secondary accent for menus | `"deep_sky_blue2"` |
| `success` | Positive feedback | `"spring_green2"` |
| `warning` | Warnings | `"gold3"` |
| `error` | Errors | `"light_salmon1"` |
| `border` | Panel borders | reuse `accent` |
| `dim` | Dividers, breadcrumbs | `"grey50"` |

Expose helper such as `theme.style("accent")` to keep Rich components and InquirerPy styling synchronized.

### Typography, Voice & Spacing
- **Tone**: Confident, helpful, and concise. Prefer short, directive sentences ("Select an authentication method") and avoid filler chatter. Reserve emojis for rare celebratory moments.
- **Headings**: `Text("Heading", style="bold accent")` with sentence case titles conveying intent ("Configure authentication").
- **Body copy**: `Text(..., style="text_primary")` with informative but terse phrasing. Keep helper text in `text_muted` and prefix with verbs like "Default:" or "Tip:".
- **Spacing**: Use `Padding((0, 1))` on panels/cards to maintain breathing room and insert a single blank line between major sections. Wrap copy around 72 characters using `textwrap.fill` to keep 80×24 terminals readable.

### Structural Components
Implement initial primitives in `clauth/ui/components.py`:
- `render_banner(title, subtitle, bullets=None)`: Rich `Panel` with accent border and optional bullet list for prerequisites or highlights.
- `render_card(title, body, footer=None)`: General-purpose block (config summaries, prompts) using `box.ROUNDED` and consistent padding.
- `render_status(message, level)`: Success/warning/error output with matching ASCII icons (`✔`, `!`, `✖`) and optional footer hint.

Defer advanced primitives (step indicators, tables) to later phases once the core experience is in place.

## Component Usage Guidelines

### Banners & Welcome Screens
- Replace the Figlet art with `render_banner("CLAUTH", "Configure Claude + Bedrock in minutes", bullets=[...])`.
- Display banner and step indicator (once implemented) together at the start of `clauth init`. Use `console.screen()` to draw once without scrolling.

### Menus & Multi-step Flows
- Precede each prompt with a short `render_card` summarizing context.
- Configure InquirerPy with shared `style` from the theme; pointer `»`, selected color `accent_alt`, instructions placed in a muted footer rather than repeating per question.
- Note: InquirerPy prompts are blocking, so they cannot coexist with an active Rich `Live` layout. Render contextual cards, invoke the prompt, then redraw summaries after the prompt completes.

### Interactive Prompts
- Wrap text input prompts using Rich `Prompt.ask` (or Typer prompt wrappers) with themed styles and validation feedback.
- When defaults exist, show them once before the prompt (`console.print("Default region: us-east-1", style=theme.text_muted)`), then accept or override.
- For confirmation prompts, use `render_card` with explicit action + `render_status(level="warning")` to emphasize destructive operations.

### Status & Messages
- Route all status output through `render_status`; drop raw `print`/`typer.echo` for consistent formatting.
- After long operations, collapse spinner output into a summary card (e.g., "Models discovered") accompanied by bullet highlights instead of raw lists.
- Success messages include next-step hint in muted footer (`Next: run claude to start the IDE`).

### Errors & Warnings
- Use `render_status(level="error")` with concise cause and remediation line. For non-blocking issues, use `warning` level and group warnings at the end of the relevant step.
- Provide `--debug` flag to reveal raw stack traces separately, keeping the primary flow clean.

## Interaction & Flow Improvements
- Establish navigation pattern:
  - **Clear screen**: Only between major phases (e.g., post-setup when launching Claude CLI).
  - **Live layout updates**: Within multi-step wizards once Rich `Live` integration is added.
  - **Static stacking**: For single-shot commands (e.g., `delete`, `config show`) to preserve execution logs.
- Introduce `WizardScreen` helper (Polish phase) that owns banner, step indicator, content area, and summary sidebar.
- Between steps, keep a sidebar-style summary card of prior selections so context persists even after `console.clear()` events.
- When launching external commands (AWS CLI), show a dedicated `render_card` labeled "Running aws configure" and stream stdout into it for transparency.

## Progress & Feedback
- For AWS discovery tasks, use Rich `Progress(transient=True)` or spinner helpers named consistently with gerund phrases ("Discovering models", "Validating credentials").
- Provide `ui.spinner("Authenticating")` context manager that switches to `render_status(success/failure)` automatically on exit.
- When auto-starting Claude CLI, display a final summary card and keep it visible even after launching (unless the terminal must be fully cleared for subprocess output).

## Advanced UX Considerations
- Keyboard navigation: standardize `↑/↓` for movement, `Enter` select, `Esc` cancel; render once per interactive card in muted footer.
- Terminal sizing: constrain panel widths to `min(console.width - 4, 78)` and enable soft wrap so 80×24 remains readable.
- Minimize flicker by batching updates with `Live` or `Console.screen` contexts; avoid repeated `console.clear()` within loops.
- Handle resize by checking `console.size` before major renders; with future Textual adoption, rely on its responsive layout.
- Provide non-interactive fallback (`--no-interactive`) that outputs the same cards sequentially for CI or scripted usage (Advanced phase).

## Implementation Roadmap

### MVP (High-impact, fast wins)
1. Create `clauth/ui/theme.py` with shared color tokens and helpers.
2. Add `render_banner`, `render_card`, and `render_status` primitives; wire them to a shared Rich `Console` wrapper.
3. Refactor `clauth init` welcome and status messaging to use the new components (banner replacement, unified success/error messages).
4. Update `config show` and other read-only commands to render output via `render_card` + `render_status` for immediate consistency.

### Polish (Structure & flow consistency)
1. Introduce `WizardScreen` helper and step indicators for multi-step flows.
2. Standardize prompt context cards, default value hints, and post-prompt summaries.
3. Implement spinner/progress helpers with consistent gerund phrasing and transient cleanup.
4. Consolidate destructive actions (e.g., `delete`) into warning banners and detailed summary cards.

### Advanced (Resilience & accessibility)
1. Add optional Rich `Live` layouts for persistent breadcrumbs and sidebars once prompt integration constraints are solved.
2. Implement terminal resize awareness and non-interactive mode output parity.
3. Expand component library (tables, step indicators, breadcrumbs) and document accessibility checks (color contrast, screen reader cues where feasible).
4. Update CI/automation docs with screenshots/GIFs and scripted usage guidelines.

## Example Pseudocode
```python
from clauth.ui import ui

ui.render_banner(
    title="Welcome to CLAUTH",
    subtitle="Configure Claude Code with AWS Bedrock in minutes",
    bullets=["Requires AWS CLI v2", "Needs Claude Code CLI"],
)

ui.render_status("Step 1 of 3 · Authenticate with AWS", level="info")
method = ui.select(
    title="Authentication Method",
    options=[
        ("sso", "AWS IAM Identity Center (SSO)"),
        ("iam", "IAM User Access Keys"),
        ("skip", "Skip – already configured"),
    ],
    footer="↑/↓ move · Enter select · Esc cancel",
)

with ui.spinner("Discovering models"):
    model_ids, model_arns = aws.list_bedrock_profiles(...)

ui.render_card(
    title="Model Selection",
    body="Default model: bedrock-instance-claude-v2\nFast model: bedrock-instance-claude-haiku",
    footer="Next: configure auto-start preferences",
)

ui.render_status("Setup complete. Run `claude` to launch the IDE.", level="success")
```
