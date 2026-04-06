# Archived Legacy Planning Tests

**TICKET-ARCH-007**: These tests were archived as part of the architectural refactoring from static planning to dynamic ReAct loop.

## Why These Tests Were Archived

The Janus project has transitioned from a **Static Planning** architecture to a **Dynamic ReAct/OODA Loop** architecture (see [docs/architecture/13-dynamic-react-loop.md](../../docs/architecture/13-dynamic-react-loop.md)).

### Old Architecture (Static Planning)
- Generated complete execution plans upfront with `generate_structured_plan()`
- Returned multiple steps: `[step1, step2, step3, ...]`
- Failed when UI changed unexpectedly
- Contained site-specific heuristics (YouTube, Google, Spotify, etc.)

### New Architecture (Dynamic ReAct Loop)
- Returns ONE action at a time with `decide_next_action()`
- Adapts to current screen state
- Generic approach - works on any interface
- No hardcoded service logic

## Tests Archived

These tests validated the old static planning behavior and contained hardcoded service names that violated the new generic architecture principles:

1. **test_ticket001_safari_youtube_search.py** - Tested YouTube-specific workflows with hardcoded domain logic
2. **test_use_case_1_forgive_burial.py** - Tested YouTube media playback with hardcoded YouTube URLs and search patterns
3. **test_ticket102_planner_agent.py** - Tested the old PlannerAgent that wrapped the deprecated generate_structured_plan method

Additionally, the following test classes were removed from active test files:
- **TestReasonerLLMUseCase1** from `test_reasoner_llm.py` - 6 tests for YouTube-specific consumption and search verbs

## Replacement Tests

The functionality previously tested by these files is now covered by:

- `test_arch_001_decide_next_action.py` - Unit tests for decide_next_action method
- `test_arch_003_ooda_loop.py` - OODA loop integration tests  
- `test_arch_007_ooda_scenarios.py` - Comprehensive scenario-based tests

## Notes

These archived tests are kept for historical reference but should NOT be run as part of the test suite. They test deprecated functionality that no longer exists in the codebase.

If you need to understand how a particular workflow worked in the old architecture, you can review these tests. However, new tests should follow the OODA loop pattern.
