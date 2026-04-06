# PERF-001 — Observation Budget

**Status:** ✅ Implemented  
**Priority:** P0  
**Date:** December 2024

---

## 📋 Summary

Implementation of strict context budget control for LLM prompts to prevent excessive injection of SOM (Set-of-Marks), memory, and tools, which causes performance loss and quality degradation.

---

## 🎯 Problem Statement

### Issues
- Excessive injection of SOM (Set-of-Marks) elements
- Unbounded memory/action history in prompts
- Large tool/action schemas included in every request
- No metrics to track context size
- LLM prompts growing beyond optimal size
- Reduced LLM performance and increased errors

### Impact
- Slower LLM inference time
- Increased token costs
- Higher rate of format errors in LLM responses
- Degraded decision quality

---

## ✅ Solution

### ContextAssembler Class

New `janus/reasoning/context_assembler.py` module providing:

1. **Token-based budgeting** for all context components
2. **Automatic shrinking** when budgets exceeded
3. **Component-specific limits**:
   - SOM (Set-of-Marks): 800 tokens / 50 elements
   - Memory (action history): 400 tokens / 10 items
   - Tools (action schema): 600 tokens
   - System state: 200 tokens
   - Total: 2000 tokens

4. **Smart shrinking policies**:
   - SOM: Limit number of elements
   - Memory: Keep most recent items
   - Tools: Truncate with notice
   - Emergency shrinking if significantly over budget

5. **Comprehensive metrics**:
   - Token counts per component
   - Element/item counts
   - Shrinking flags
   - Budget status

---

## 🏗️ Architecture

### BudgetConfig

```python
@dataclass
class BudgetConfig:
    max_som_tokens: int = 800          # Set-of-Marks elements
    max_memory_tokens: int = 400       # Action history
    max_tools_tokens: int = 600        # Tool/action schema
    max_system_state_tokens: int = 200 # System state
    max_total_tokens: int = 2000       # Total budget
    
    max_som_elements: int = 50         # Max SOM elements
    max_memory_items: int = 10         # Max history items
```

### ContextMetrics

```python
@dataclass
class ContextMetrics:
    # Token counts
    som_tokens: int = 0
    memory_tokens: int = 0
    tools_tokens: int = 0
    system_state_tokens: int = 0
    total_tokens: int = 0
    
    # Element counts
    som_elements: int = 0
    memory_items: int = 0
    
    # Shrinking applied
    som_shrunk: bool = False
    memory_shrunk: bool = False
    tools_shrunk: bool = False
    
    # Budget status
    over_budget: bool = False
    budget_exceeded_by: int = 0
```

### ContextAssembler

```python
class ContextAssembler:
    def assemble_context(
        self,
        visual_context: str,
        action_history: List[Any],
        schema_section: str,
        system_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assemble context with budget enforcement.
        
        Returns:
            - visual_context: Budgeted SOM
            - action_history: Budgeted history
            - schema_section: Budgeted schema
            - system_state: Budgeted state
            - metrics: Assembly metrics
        """
```

---

## 🔧 Implementation Details

### Integration with ReasonerLLM

The `ContextAssembler` is integrated into `ReasonerLLM._build_burst_prompt()`:

```python
class ReasonerLLM:
    def __init__(self, ...):
        # PERF-001: Context assembler for budget control
        self.context_assembler = ContextAssembler(config=BudgetConfig())
    
    def _build_burst_prompt(self, ...):
        # Assemble context with budget enforcement
        budgeted_context = self.context_assembler.assemble_context(
            visual_context=visual_context,
            action_history=action_history,
            schema_section=schema_section,
            system_state=system_state
        )
        
        # Use budgeted components in prompt
        budgeted_visual = budgeted_context["visual_context"]
        budgeted_history = budgeted_context["action_history"]
        # ...
```

### Token Estimation

Uses simple but effective token estimation:
- ~4 characters per token
- Plus word boundary counting
- Good enough for budget enforcement

```python
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(text) // 4 + text.count(' ') // 2
```

### Shrinking Policies

#### SOM Shrinking
1. Keep header lines (non-element)
2. Limit element lines to `max_som_elements`
3. Emergency shrink to half if needed

#### Memory Shrinking
1. Keep most recent `max_memory_items`
2. If still over budget, reduce to half
3. Minimum 3 items kept

#### Tools Shrinking
1. Truncate schema proportionally
2. Add "... (schema truncated)" notice

#### System State
1. Keep only essential fields: `active_app`, `url`, `window_title`, `domain`
2. Truncate long values to 200 chars

---

## 📊 Metrics & Monitoring

### Logged Metrics

```python
logger.debug(
    f"Context budget: {metrics.total_tokens} tokens "
    f"(SOM:{metrics.som_tokens}, Mem:{metrics.memory_tokens}, "
    f"Tools:{metrics.tools_tokens}, State:{metrics.system_state_tokens})"
)
```

### Warnings

```python
if metrics.over_budget:
    logger.warning(
        f"⚠️ Context over budget by {metrics.budget_exceeded_by} tokens. "
        f"Shrinking applied: SOM={metrics.som_shrunk}, "
        f"Memory={metrics.memory_shrunk}, Tools={metrics.tools_shrunk}"
    )
```

---

## 🧪 Testing

Comprehensive test suite in `tests/test_perf_001_context_assembler.py`:

- ✅ Default and custom budget configuration
- ✅ Empty context handling
- ✅ Small context under budget
- ✅ SOM over budget shrinking
- ✅ Memory over budget limiting
- ✅ Schema over budget truncation
- ✅ Total budget exceeded with emergency shrinking
- ✅ System state budgeting
- ✅ Element counting
- ✅ Metrics tracking and reset

---

## ✅ Acceptance Criteria

### Completed

- [x] **ContextAssembler created** with budget management
- [x] **Budget limits** for memory, SOM, and tools
- [x] **Size metrics** for token counting
- [x] **Shrink policy** when budget exceeded
- [x] **Integrated** into ReasonerLLM
- [x] **Comprehensive tests** written
- [x] **Documentation** updated

### Verification

- [x] **Prompt under threshold**: Total tokens ≤ 2000
- [x] **SOM ≤ N elements**: Max 50 elements enforced
- [x] **Metrics tracked**: All components measured
- [x] **Shrinking works**: Over-budget contexts reduced

### Expected Benefits

- ⏱️ **Reduced LLM time**: Smaller prompts = faster inference
- ✅ **Fewer format errors**: Better LLM response quality
- 📊 **Observable**: Metrics track budget usage
- 🎯 **Consistent**: Enforced limits prevent unbounded growth

---

## 🔄 Migration Path

### Before PERF-001

```python
# No budget control
prompt = f"""
VISUAL ELEMENTS:
{visual_context}  # Could be 5000+ tokens

HISTORY:
{all_history}  # Unbounded

SCHEMA:
{full_schema}  # Complete schema every time
"""
```

### After PERF-001

```python
# Budget-controlled assembly
budgeted = context_assembler.assemble_context(...)

prompt = f"""
VISUAL ELEMENTS:
{budgeted["visual_context"]}  # ≤ 800 tokens, ≤ 50 elements

HISTORY:
{format_history(budgeted["action_history"])}  # ≤ 400 tokens, ≤ 10 items

SCHEMA:
{budgeted["schema_section"]}  # ≤ 600 tokens
"""
```

---

## 📁 Files Modified

### New Files
- `janus/reasoning/context_assembler.py` - ContextAssembler implementation
- `tests/test_perf_001_context_assembler.py` - Test suite
- `docs/architecture/PERF-001-observation-budget.md` - This documentation

### Modified Files
- `janus/reasoning/reasoner_llm.py` - Integrated ContextAssembler
  - Import ContextAssembler and BudgetConfig
  - Initialize assembler in `__init__`
  - Use in `_build_burst_prompt`

---

## 🔮 Future Enhancements

### Potential Improvements

1. **Dynamic budgets** based on task complexity
2. **Prioritization** of most relevant SOM elements
3. **Semantic compression** using embeddings
4. **Budget per component** configurable via settings
5. **A/B testing** to optimize budget values
6. **LLM-specific budgets** for different models

### Configuration

Could be exposed in `settings.py`:

```python
class Settings:
    # PERF-001: Context budget configuration
    context_budget_som_tokens: int = 800
    context_budget_memory_tokens: int = 400
    context_budget_tools_tokens: int = 600
    context_budget_total_tokens: int = 2000
```

---

## 📚 References

- **CORE-FOUNDATION-002**: Burst OODA mode (uses context assembly)
- **ARCH-004**: Canonical SystemState
- **Set-of-Marks**: Visual grounding system

---

**Last Updated**: December 2024  
**Author**: GitHub Copilot + BenHND  
**Status**: ✅ Implemented and Tested
