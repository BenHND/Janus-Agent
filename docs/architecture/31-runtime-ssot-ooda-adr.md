# 31. ADR: Janus Runtime SSOT (OODA)

**Status:** ✅ Complete (Phase 2)  
**Date:** December 2024  
**Ticket:** ARCH-001  
**Decision Makers:** Development Team  
**Implementation:** Complete - V3 engines removed, ActionCoordinator is sole runtime

---

## Context and Problem Statement

Janus currently has **multiple execution engines** that process user commands and execute action plans:

1. **ActionCoordinator** (`janus/core/action_coordinator.py`)
   - OODA/ReAct loop implementation
   - Dynamic decision-making with LLM
   - Burst mode support (2-6 actions per LLM call)
   - Used by: JanusAgent (primary API)
   - Well-documented in architecture docs

2. **ExecutionEngineV3** (`janus/core/execution_engine_v3.py`)
   - Static plan execution with retry logic
   - Context management and validation
   - Used by: Legacy Pipeline paths, various tests
   - Support for parallel execution

3. **AgentExecutorV3** (`janus/core/agent_executor_v3.py`)
   - Pre-validation with ValidatorAgent
   - Vision recovery and replanning
   - Used by: Pipeline (legacy fallback), tests
   - Wraps ExecutionEngineV3 with additional features

Additionally, there are **multiple action schemas** that define the structure of actions:

1. **module_action_schema.py**: Complete schema with 8 universal modules, risk metadata, parameter validation
2. **action_schema.py**: Legacy unified action schema (from TICKET-003)

This creates several problems:

- **Implicit Conversions**: Silent conversions between schemas based on entry point
- **Behavior Divergence**: Same command behaves differently via CLI vs API vs JanusAgent
- **Maintenance Burden**: Bug fixes must be applied to multiple execution paths
- **Testing Complexity**: Tests use different engines, making it hard to ensure consistency
- **Developer Confusion**: New developers don't know which engine to use
- **Poor Debugging**: Bugs are harder to trace across multiple execution paths

## Decision Drivers

- **Single Source of Truth**: One execution path for production
- **Consistency**: Same behavior across all entry points (CLI, API, JanusAgent)
- **Traceability**: Clear logging and metrics for execution path usage
- **Performance**: OODA loop with burst mode is more efficient
- **Maintainability**: Single codebase to maintain and improve
- **Schema Clarity**: One official schema with comprehensive validation
- **Backward Compatibility**: Ability to fallback to V3 for debugging

## Considered Options

### Option 1: Consolidate on ActionCoordinator (OODA) ✅ **SELECTED**

**Pros:**
- ✅ Already the default in JanusAgent (primary API)
- ✅ OODA/ReAct loop is more adaptive and robust
- ✅ Burst mode reduces LLM calls (2-6 actions per call)
- ✅ Better stagnation detection and recovery
- ✅ Comprehensive state observation via SystemBridge
- ✅ Well-documented in architecture docs
- ✅ Uses module_action_schema.py (complete schema)
- ✅ Better alignment with modern AI agent patterns

**Cons:**
- ⚠️ Need to migrate legacy Pipeline paths
- ⚠️ Some tests still rely on ExecutionEngineV3
- ⚠️ Loss of parallel execution feature (from ExecutionEngineV3)

**Migration Effort:** Medium (update tests and legacy paths)

### Option 2: Consolidate on ExecutionEngineV3/AgentExecutorV3

**Pros:**
- ✅ More tests already use this path
- ✅ Supports parallel step execution
- ✅ Well-tested retry and recovery logic

**Cons:**
- ❌ Static plan execution (less adaptive)
- ❌ Requires pre-generated plans (more LLM calls)
- ❌ No burst mode optimization
- ❌ Would require migrating JanusAgent (primary API)
- ❌ Not aligned with modern OODA/ReAct patterns

**Migration Effort:** High (JanusAgent is the primary API)

### Option 3: Keep Both with Clear Separation

**Pros:**
- ✅ Flexibility for different use cases
- ✅ No immediate migration needed

**Cons:**
- ❌ Doesn't solve the core problem (multiple execution paths)
- ❌ Continued maintenance burden
- ❌ Still have behavior divergence issues
- ❌ Confusion about which to use

**Migration Effort:** Low, but doesn't solve the problem

## Decision Outcome

**Chosen option: "Option 1 - Consolidate on ActionCoordinator (OODA)"**

ActionCoordinator will be the **official and sole production runtime** for Janus.

### Rationale

1. **Modern Architecture**: OODA loop is the industry-standard pattern for AI agents
2. **Performance**: Burst mode significantly reduces LLM calls
3. **Robustness**: Better error recovery with stagnation detection
4. **Consistency**: JanusAgent already uses it as default
5. **Schema Clarity**: Uses module_action_schema.py exclusively

## Implementation Plan

### Phase 1: Deprecation & Flag Introduction ✅ COMPLETE

1. ✅ Create this ADR
2. ✅ Add `settings.execution.engine` flag: "ooda" (default) | "v3_legacy"
3. ✅ Update ExecutionEngineV3 to log deprecation warnings
4. ✅ Update AgentExecutorV3 to log deprecation warnings
5. ✅ Add metrics for V3 usage tracking
6. ✅ Update documentation

### Phase 2: Complete Migration ✅ COMPLETE

1. ✅ Remove ExecutionEngineV3 and AgentExecutorV3 classes
2. ✅ Remove V3-specific services (execution_service, vision_recovery_service, replanning_service, context_management_service, precondition_service)
3. ✅ Update Pipeline to remove V3 executor properties
4. ✅ Remove `settings.execution.engine` flag (only ActionCoordinator remains)
5. ✅ Simplify execution_metrics.py (single engine tracking)
6. ✅ Update documentation to reflect completion

### Phase 3: Test Cleanup (Optional, Future)

1. Update or remove legacy tests that used V3 engines
2. Archive examples that referenced V3
3. Final documentation cleanup

## Official Contracts

### Runtime SSOT

- **Production Runtime**: `ActionCoordinator` (OODA/ReAct loop)
- **Legacy Sandbox**: `ExecutionEngineV3` / `AgentExecutorV3` (explicit flag only)

### Schema SSOT

- **Official Schema**: `module_action_schema.py`
  - 8 universal modules (system, browser, messaging, crm, files, ui, code, llm)
  - Risk metadata (LOW, MEDIUM, HIGH)
  - Parameter validation
  - Comprehensive action definitions

### Execution Path SSOT

```
User Input
    ↓
JanusAgent (primary API)
    ↓
ActionCoordinator (OODA loop)
    ├─ Observe: SystemBridge + VisionEngine
    ├─ Orient: Context + History
    ├─ Decide: ReasonerLLM (burst mode)
    └─ Act: AgentRegistry
```

## Validation Rules

### No Silent Schema Conversions

- ❌ **BLOCKED**: Converting between action_schema.py and module_action_schema.py without logging
- ✅ **ALLOWED**: Using module_action_schema.py exclusively
- ⚠️ **LOGGED**: Any use of V3 engines must log a warning

### Explicit V3 Usage Only

- ❌ **BLOCKED in PROD**: Using ExecutionEngineV3/AgentExecutorV3 without `settings.execution.engine = "v3_legacy"`
- ✅ **ALLOWED in DEV/TEST**: V3 engines with explicit flag
- 📊 **METRICS**: V3 usage tracked for deprecation planning

### Consistency Enforcement

- ✅ **TESTED**: Same command via CLI/API/JanusAgent produces same results
- ✅ **TESTED**: Schema validation rejects invalid actions consistently
- ✅ **LOGGED**: Execution path for every command

## Consequences

### Positive

- ✅ **Single Source of Truth**: Clear execution path for all commands
- ✅ **Better Performance**: Burst mode reduces LLM calls
- ✅ **Easier Debugging**: Single execution engine to trace
- ✅ **Consistency**: Same behavior across all entry points
- ✅ **Modern Architecture**: Aligned with OODA/ReAct industry patterns
- ✅ **Clear Schema**: module_action_schema.py as the only schema

### Negative

- ⚠️ **Migration Effort**: Tests and legacy code need updates
- ⚠️ **Loss of Parallel Execution**: ExecutionEngineV3's parallel feature not in OODA
- ⚠️ **Temporary Complexity**: During transition, both engines coexist

### Neutral

- 🔄 **Backward Compatibility**: V3 available via explicit flag for debugging
- 📚 **Documentation Update**: All docs reference ActionCoordinator as default

## Acceptance Criteria

- [x] ADR document created
- [ ] `settings.execution.engine` flag implemented
- [ ] Deprecation warnings added to ExecutionEngineV3
- [ ] Deprecation warnings added to AgentExecutorV3
- [ ] Metrics tracking V3 usage
- [ ] Tests verify CLI/API/JanusAgent consistency
- [ ] Documentation updated in /docs
- [ ] FEATURES_AUDIT.md updated
- [ ] Production deployment blocks V3 without explicit flag
- [ ] No silent schema conversions (assertions added)

## References

- [ActionCoordinator Documentation](14-action-coordinator.md)
- [JanusAgent API Documentation](15-janus-agent-api.md)
- [Burst OODA Mode](29-burst-ooda-mode.md)
- [Module Action Schema](../archive/developer/v3-agent-architecture.md)
- [OODA Loop Implementation](13-dynamic-react-loop.md)

---

**Last Updated:** December 2024  
**Next Review:** After Phase 1 implementation (Q1 2025)
