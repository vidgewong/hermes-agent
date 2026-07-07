## 1. Card Data Model (gateway/cards.py)

- [x] 1.1 Create `gateway/cards.py` with dataclass definitions: `CardHeader`, `CardMarkdown`, `CardDivider`, `CardActions`, `CardListItem`, `CardNote`, `CardSelect`, `CardButton`, `InteractiveCard`
- [x] 1.2 Implement `InteractiveCard.builder()` fluent API with methods: `title`, `markdown`, `divider`, `actions`, `actions_equal`, `list_item`, `note`, `select`, `build`
- [x] 1.3 Add unit tests for card builder (`tests/gateway/test_cards.py`)

## 2. Feishu Card Renderer

- [x] 2.1 Implement `_render_card_to_feishu(card: InteractiveCard, session_key: str) -> dict` in feishu adapter that converts Card IR to Feishu Schema 1.0 JSON
- [x] 2.2 Handle all element type mappings: markdown→markdown tag, divider→hr, actions→action/column_set, list_item→column_set with weighted columns, note→note, select→select_static
- [x] 2.3 Inject `session_key` into every button/select value dict for callback routing
- [x] 2.4 Add unit tests for renderer output (`tests/plugins/test_feishu_card_renderer.py`)

## 3. AskUser/Clarify Interactive Card

- [x] 3.1 Override `send_clarify` in `FeishuAdapter` to build and send an interactive card (blue header + ListItem options + note) for single-select mode
- [x] 3.2 Handle open-ended mode (no choices): send card with question markdown + note + call `mark_awaiting_text`
- [x] 3.3 Add `clarify:` prefix handler in `_on_card_action_trigger` that calls `resolve_gateway_clarify` and returns green confirmation card
- [x] 3.4 Add operator validation — reject clarify callbacks from non-session-owner with toast error
- [x] 3.5 Ensure text fallback coexistence: also call `mark_awaiting_text` for single-select so typed replies still work
- [x] 3.6 Add integration tests for clarify card flow (`tests/plugins/test_feishu_clarify_card.py`)

## 4. Streaming Progress Card

- [x] 4.1 Implement `FeishuStreamCard` state machine class with lifecycle: create → stream → finish (status: thinking/working/done/error)
- [x] 4.2 Implement CardKit v1 card creation (`POST /open-apis/cardkit/v1/cards`) with Schema 2.0 JSON (streaming_mode, collapsible_panel, element_id)
- [x] 4.3 Implement streaming text update (`PUT /cardkit/v1/cards/{card_id}/elements/{element_id}/content`) with throttling (1500ms / 30 chars)
- [x] 4.4 Implement tool call panel updates: add entries to collapsible panel, update counts, show success/failure dots
- [x] 4.5 Implement header status color transitions (blue→green/red) on turn completion
- [x] 4.6 Implement size limit handling: progressive compaction when >28KB, degradation to plain markdown card
- [x] 4.7 Implement graceful degradation path: fallback to standard card + PATCH when CardKit v1 unavailable (permission error)
- [x] 4.8 Hook streaming card into agent turn lifecycle (gateway stream_dispatch or delivery layer)
- [x] 4.9 Add tests for streaming card state machine (`tests/plugins/test_feishu_stream_card.py`)

## 5. Refactor Existing Approval Card

- [x] 5.1 Rewrite `send_exec_approval` to use `InteractiveCard.builder()` + `_render_card_to_feishu` instead of hardcoded JSON dict
- [x] 5.2 Migrate approval button values to unified prefix format (`perm:approve_once`, `perm:deny`, etc.) while keeping backward compat for `hermes_action` key
- [x] 5.3 Verify existing approval card tests still pass after refactor

## 6. Callback Router Unification

- [x] 6.1 Extend `_on_card_action_trigger` to dispatch by action value prefix: `perm:` → approval, `clarify:` → ask-user, `stream:` → progress card interaction
- [x] 6.2 Maintain backward compatibility with existing `hermes_action` / `hermes_update_prompt_action` key-based routing
- [x] 6.3 Add routing tests covering all prefix paths (`tests/plugins/test_feishu_card_routing.py`)
