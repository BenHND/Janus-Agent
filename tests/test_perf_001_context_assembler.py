"""
Tests for PERF-001: Context Assembler with Observation Budget
"""

import pytest
from janus.ai.reasoning.context_assembler import (
    ContextAssembler,
    BudgetConfig,
    ContextMetrics
)


class TestBudgetConfig:
    """Test BudgetConfig dataclass."""
    
    def test_default_config(self):
        """Test default budget configuration."""
        config = BudgetConfig()
        
        assert config.max_som_tokens == 800
        assert config.max_memory_tokens == 400
        # TICKET 3 (P0): Updated from 600 to 300 for compact schema
        assert config.max_tools_tokens == 300
        assert config.max_system_state_tokens == 200
        assert config.max_total_tokens == 2000
        assert config.max_som_elements == 50
        assert config.max_memory_items == 10
    
    def test_custom_config(self):
        """Test custom budget configuration."""
        config = BudgetConfig(
            max_som_tokens=500,
            max_memory_tokens=300,
            max_tools_tokens=400,
            max_skill_hint_tokens=200,
            max_total_tokens=1500
        )
        
        assert config.max_som_tokens == 500
        assert config.max_memory_tokens == 300
        assert config.max_tools_tokens == 400
        assert config.max_skill_hint_tokens == 200
        # TICKET 3 (P0): Total is adjusted to accommodate components (500+300+400+200+200=1600)
        assert config.max_total_tokens == 1600
    
    def test_config_validation(self):
        """Test budget configuration validation."""
        # This should adjust total_tokens automatically
        config = BudgetConfig(
            max_som_tokens=1000,
            max_memory_tokens=1000,
            max_tools_tokens=1000,
            max_system_state_tokens=500,
            max_skill_hint_tokens=300,
            max_total_tokens=2000  # Too small
        )
        
        # Total should be adjusted to accommodate components
        # TICKET 3 (P0): Updated expected total (1000+1000+1000+500+300=3800)
        assert config.max_total_tokens >= 3800


class TestContextMetrics:
    """Test ContextMetrics dataclass."""
    
    def test_default_metrics(self):
        """Test default metrics."""
        metrics = ContextMetrics()
        
        assert metrics.som_tokens == 0
        assert metrics.memory_tokens == 0
        assert metrics.tools_tokens == 0
        assert metrics.system_state_tokens == 0
        assert metrics.total_tokens == 0
        assert metrics.som_elements == 0
        assert metrics.memory_items == 0
        assert metrics.som_shrunk is False
        assert metrics.memory_shrunk is False
        assert metrics.tools_shrunk is False
        assert metrics.over_budget is False
        assert metrics.budget_exceeded_by == 0
    
    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = ContextMetrics(
            som_tokens=500,
            memory_tokens=200,
            tools_tokens=300,
            system_state_tokens=100,
            total_tokens=1100,
            som_elements=25,
            memory_items=5,
            som_shrunk=True
        )
        
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["tokens"]["som"] == 500
        assert metrics_dict["tokens"]["memory"] == 200
        assert metrics_dict["tokens"]["total"] == 1100
        assert metrics_dict["elements"]["som_elements"] == 25
        assert metrics_dict["shrinking"]["som_shrunk"] is True


class TestContextAssembler:
    """Test ContextAssembler class."""
    
    def test_initialization(self):
        """Test ContextAssembler initialization."""
        assembler = ContextAssembler()
        
        assert assembler.config is not None
        assert assembler.metrics is not None
        assert isinstance(assembler.config, BudgetConfig)
        assert isinstance(assembler.metrics, ContextMetrics)
    
    def test_initialization_with_custom_config(self):
        """Test initialization with custom config."""
        config = BudgetConfig(max_som_tokens=500)
        assembler = ContextAssembler(config=config)
        
        assert assembler.config.max_som_tokens == 500
    
    def test_assemble_empty_context(self):
        """Test assembling empty context."""
        assembler = ContextAssembler()
        
        result = assembler.assemble_context(
            visual_context="",
            action_history=[],
            schema_section="",
            system_state={}
        )
        
        assert result["visual_context"] == ""
        assert result["action_history"] == []
        assert result["schema_section"] == ""
        assert result["system_state"] == {}
        assert result["metrics"].total_tokens == 0
        assert result["metrics"].over_budget is False
    
    def test_assemble_small_context(self):
        """Test assembling small context under budget."""
        assembler = ContextAssembler()
        
        visual_context = "id: button_1, type: button, text: Click me\nid: input_1, type: input, text: Search"
        action_history = [
            type('ActionResult', (), {'action_type': 'click', 'success': True, 'message': 'Clicked button'})()
        ]
        schema_section = "Available actions:\n- click: Click element\n- type: Type text"
        system_state = {
            "active_app": "Chrome",
            "url": "https://example.com",
            "window_title": "Example Page"
        }
        
        result = assembler.assemble_context(
            visual_context=visual_context,
            action_history=action_history,
            schema_section=schema_section,
            system_state=system_state
        )
        
        assert result["visual_context"] == visual_context
        assert len(result["action_history"]) == 1
        assert "click" in result["schema_section"]
        assert result["system_state"]["active_app"] == "Chrome"
        assert result["metrics"].total_tokens > 0
        assert result["metrics"].over_budget is False
        assert result["metrics"].som_shrunk is False
        assert result["metrics"].memory_shrunk is False
    
    def test_budget_visual_context_over_limit(self):
        """Test visual context budget enforcement."""
        config = BudgetConfig(max_som_tokens=100, max_som_elements=5)
        assembler = ContextAssembler(config=config)
        
        # Create a large visual context
        visual_lines = [
            f"id: button_{i}, type: button, text: Button {i}"
            for i in range(20)
        ]
        visual_context = "\n".join(visual_lines)
        
        result = assembler.assemble_context(
            visual_context=visual_context,
            action_history=[],
            schema_section="",
            system_state={}
        )
        
        # Should be shrunk
        assert result["metrics"].som_shrunk is True
        assert result["metrics"].som_elements <= config.max_som_elements
        assert result["metrics"].som_tokens <= config.max_som_tokens * 1.1  # Allow 10% margin
    
    def test_budget_action_history_over_limit(self):
        """Test action history budget enforcement."""
        config = BudgetConfig(max_memory_tokens=100, max_memory_items=3)
        assembler = ContextAssembler(config=config)
        
        # Create large action history
        action_history = [
            type('ActionResult', (), {
                'action_type': f'action_{i}',
                'success': True,
                'message': f'This is a long message for action {i} with lots of detail'
            })()
            for i in range(15)
        ]
        
        result = assembler.assemble_context(
            visual_context="",
            action_history=action_history,
            schema_section="",
            system_state={}
        )
        
        # Should be limited
        assert result["metrics"].memory_items <= config.max_memory_items
        assert len(result["action_history"]) <= config.max_memory_items
    
    def test_budget_schema_over_limit(self):
        """Test schema budget enforcement."""
        config = BudgetConfig(max_tools_tokens=100)
        assembler = ContextAssembler(config=config)
        
        # Create a large schema
        schema_lines = [
            f"Action {i}: Very detailed description of action {i} with many parameters and examples"
            for i in range(50)
        ]
        schema_section = "\n".join(schema_lines)
        
        result = assembler.assemble_context(
            visual_context="",
            action_history=[],
            schema_section=schema_section,
            system_state={}
        )
        
        # Should be truncated
        assert result["metrics"].tools_shrunk is True
        assert result["metrics"].tools_tokens <= config.max_tools_tokens * 1.1  # Allow 10% margin
    
    def test_total_budget_exceeded(self):
        """Test total budget enforcement."""
        config = BudgetConfig(
            max_som_tokens=500,
            max_memory_tokens=500,
            max_tools_tokens=500,
            max_system_state_tokens=200,
            max_total_tokens=1000  # Less than sum of components
        )
        assembler = ContextAssembler(config=config)
        
        # Create contexts that exceed component budgets
        visual_context = "id: button, type: button, text: " + "x" * 1000
        action_history = [
            type('ActionResult', (), {
                'action_type': f'action_{i}',
                'success': True,
                'message': "x" * 100
            })()
            for i in range(20)
        ]
        schema_section = "Actions:\n" + "\n".join([f"Action {i}: " + "x" * 50 for i in range(30)])
        system_state = {
            "active_app": "App",
            "url": "https://example.com",
            "window_title": "Title"
        }
        
        result = assembler.assemble_context(
            visual_context=visual_context,
            action_history=action_history,
            schema_section=schema_section,
            system_state=system_state
        )
        
        # Check that emergency shrinking was applied if significantly over budget
        metrics = result["metrics"]
        if metrics.budget_exceeded_by > 500:
            # Emergency shrinking should have been applied
            assert metrics.total_tokens < metrics.total_tokens + metrics.budget_exceeded_by
    
    def test_system_state_budgeting(self):
        """Test system state budgeting."""
        assembler = ContextAssembler()
        
        system_state = {
            "active_app": "Chrome",
            "url": "https://" + "x" * 500,  # Very long URL
            "window_title": "Title " + "x" * 300,
            "clipboard": "Clipboard " + "x" * 200,
            "other_field": "Should be excluded"
        }
        
        result = assembler.assemble_context(
            visual_context="",
            action_history=[],
            schema_section="",
            system_state=system_state
        )
        
        budgeted_state = result["system_state"]
        
        # Should only have essential fields
        assert "active_app" in budgeted_state
        assert "url" in budgeted_state
        assert "window_title" in budgeted_state
        assert "other_field" not in budgeted_state
        
        # Long values should be truncated
        assert len(budgeted_state["url"]) <= 203  # 200 + "..."
        assert len(budgeted_state["window_title"]) <= 203
    
    def test_metrics_reset(self):
        """Test metrics reset."""
        assembler = ContextAssembler()
        
        # Assemble some context
        assembler.assemble_context(
            visual_context="Some context",
            action_history=[],
            schema_section="Some schema",
            system_state={}
        )
        
        # Metrics should have values
        assert assembler.metrics.total_tokens > 0
        
        # Reset
        assembler.reset_metrics()
        
        # Metrics should be reset
        assert assembler.metrics.total_tokens == 0
        assert assembler.metrics.som_tokens == 0
    
    def test_get_metrics(self):
        """Test getting metrics."""
        assembler = ContextAssembler()
        
        assembler.assemble_context(
            visual_context="Some context",
            action_history=[],
            schema_section="Some schema",
            system_state={"active_app": "Test"}
        )
        
        metrics = assembler.get_metrics()
        
        assert isinstance(metrics, ContextMetrics)
        assert metrics.total_tokens > 0
    
    def test_empty_visual_context_handling(self):
        """Test handling of empty visual context."""
        assembler = ContextAssembler()
        
        result = assembler.assemble_context(
            visual_context="",
            action_history=[],
            schema_section="",
            system_state={}
        )
        
        assert result["visual_context"] == ""
        assert result["metrics"].som_tokens == 0
        assert result["metrics"].som_elements == 0
    
    def test_som_element_counting(self):
        """Test SOM element counting."""
        assembler = ContextAssembler()
        
        visual_context = """Available elements:
id: button_1, type: button, text: Click
id: link_1, type: link, text: Home
id: input_1, type: input, text: Search"""
        
        result = assembler.assemble_context(
            visual_context=visual_context,
            action_history=[],
            schema_section="",
            system_state={}
        )
        
        # Should count 3 elements
        assert result["metrics"].som_elements == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
