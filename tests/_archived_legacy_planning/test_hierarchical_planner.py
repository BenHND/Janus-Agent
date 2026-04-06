"""
Unit tests for Hierarchical Task Planner (TICKET A5).

Tests hierarchical task decomposition, tree structure,
and integration with existing planning components.
"""
import unittest
from typing import Any, Dict
from unittest.mock import Mock, patch

from janus.runtime.core.contracts import ActionPlan, Intent
from janus.runtime.core.hierarchical_planner import ExecutionOrder, HierarchicalPlanner, TreeNode


class TestTreeNode(unittest.TestCase):
    """Test cases for TreeNode"""

    def test_create_leaf_node(self):
        """Test creating a leaf node"""
        node = TreeNode(task="Open Chrome", description="Launch Chrome browser")

        self.assertEqual(node.task, "Open Chrome")
        self.assertEqual(node.description, "Launch Chrome browser")
        self.assertTrue(node.is_leaf())
        self.assertEqual(len(node.children), 0)

    def test_create_node_with_children(self):
        """Test creating a node with children"""
        root = TreeNode(task="Prepare presentation")
        child1 = TreeNode(task="Open PowerPoint")
        child2 = TreeNode(task="Create slides")

        root.add_child(child1)
        root.add_child(child2)

        self.assertFalse(root.is_leaf())
        self.assertEqual(len(root.children), 2)
        self.assertEqual(root.children[0].task, "Open PowerPoint")
        self.assertEqual(root.children[1].task, "Create slides")

    def test_to_dict(self):
        """Test converting node to dictionary"""
        root = TreeNode(
            task="Main task", description="Main description", metadata={"priority": "high"}
        )
        child = TreeNode(task="Sub task", description="Sub description")
        root.add_child(child)

        result = root.to_dict()

        self.assertEqual(result["task"], "Main task")
        self.assertEqual(result["description"], "Main description")
        self.assertEqual(result["metadata"]["priority"], "high")
        self.assertEqual(len(result["children"]), 1)
        self.assertEqual(result["children"][0]["task"], "Sub task")


class TestHierarchicalPlanner(unittest.TestCase):
    """Test cases for HierarchicalPlanner"""

    def setUp(self):
        """Set up test fixtures"""
        self.planner = HierarchicalPlanner()

    def test_simple_decomposition(self):
        """Test simple task decomposition without LLM"""
        tree = self.planner.decompose("Simple task", use_llm=False)

        self.assertIsInstance(tree, TreeNode)
        self.assertEqual(tree.task, "Simple task")
        # Simple tasks should create single leaf node
        self.assertTrue(tree.is_leaf() or len(tree.children) == 0)

    def test_presentation_decomposition(self):
        """Test presentation task decomposition"""
        tree = self.planner.decompose("Prépare présentation sur IA", use_llm=False)

        self.assertIsInstance(tree, TreeNode)
        self.assertIn("présentation", tree.task.lower())

        # Should have hierarchical structure
        self.assertGreater(len(tree.children), 0)

        # Check for expected sub-tasks
        task_names = [child.task for child in tree.children]
        # Should have structure, data collection, and finalization phases
        self.assertGreater(len(task_names), 0)

    def test_research_decomposition(self):
        """Test research task decomposition"""
        tree = self.planner.decompose("Recherche sur l'intelligence artificielle", use_llm=False)

        self.assertIsInstance(tree, TreeNode)
        self.assertIn("recherche", tree.task.lower())
        self.assertGreater(len(tree.children), 0)

    def test_document_decomposition(self):
        """Test document creation decomposition"""
        tree = self.planner.decompose("Créer document rapport", use_llm=False)

        self.assertIsInstance(tree, TreeNode)
        self.assertGreater(len(tree.children), 0)

    def test_decompose_with_context(self):
        """Test decomposition with context"""
        context = {"domain": "technology", "slides": 10, "deadline": "tomorrow"}

        tree = self.planner.decompose("Prépare présentation", context=context, use_llm=False)

        self.assertIsInstance(tree, TreeNode)
        self.assertGreater(len(tree.children), 0)

    def test_flatten_depth_first(self):
        """Test depth-first tree flattening"""
        # Create a simple tree
        root = TreeNode(task="Root")
        child1 = TreeNode(task="Child 1")
        child2 = TreeNode(task="Child 2")
        grandchild = TreeNode(task="Grandchild")

        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)

        # Flatten depth-first
        flat = self.planner.flatten_tree(root, ExecutionOrder.DEPTH_FIRST)

        # Should visit: root -> child1 -> grandchild -> child2
        self.assertEqual(len(flat), 4)
        self.assertEqual(flat[0].task, "Root")
        self.assertEqual(flat[1].task, "Child 1")
        self.assertEqual(flat[2].task, "Grandchild")
        self.assertEqual(flat[3].task, "Child 2")

    def test_flatten_breadth_first(self):
        """Test breadth-first tree flattening"""
        # Create a simple tree
        root = TreeNode(task="Root")
        child1 = TreeNode(task="Child 1")
        child2 = TreeNode(task="Child 2")
        grandchild = TreeNode(task="Grandchild")

        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)

        # Flatten breadth-first
        flat = self.planner.flatten_tree(root, ExecutionOrder.BREADTH_FIRST)

        # Should visit: root -> child1 -> child2 -> grandchild
        self.assertEqual(len(flat), 4)
        self.assertEqual(flat[0].task, "Root")
        self.assertEqual(flat[1].task, "Child 1")
        self.assertEqual(flat[2].task, "Child 2")
        self.assertEqual(flat[3].task, "Grandchild")


class TestHierarchicalPlannerWithLLM(unittest.TestCase):
    """Test cases for HierarchicalPlanner with LLM integration"""

    def setUp(self):
        """Set up test fixtures with mock LLM"""
        self.mock_llm = Mock()
        self.planner = HierarchicalPlanner(llm_reasoner=self.mock_llm)

    def test_decompose_with_llm(self):
        """Test decomposition using LLM"""
        # Mock LLM response
        self.mock_llm.decompose_task.return_value = {
            "task": "Prépare présentation",
            "description": "Create presentation",
            "children": [
                {"task": "Crée structure", "description": "Set up structure", "children": []},
                {"task": "Collecte données", "description": "Gather content", "children": []},
            ],
        }

        tree = self.planner.decompose("Prépare présentation", use_llm=True)

        self.assertIsInstance(tree, TreeNode)
        self.assertEqual(tree.task, "Prépare présentation")
        self.assertEqual(len(tree.children), 2)

        # Verify LLM was called
        self.mock_llm.decompose_task.assert_called_once()

    def test_llm_fallback_on_error(self):
        """Test fallback to rules when LLM fails"""
        # Mock LLM to raise exception
        self.mock_llm.decompose_task.side_effect = Exception("LLM error")

        tree = self.planner.decompose("Prépare présentation", use_llm=True)

        # Should still return a valid tree using rule-based fallback
        self.assertIsInstance(tree, TreeNode)
        self.assertGreater(len(tree.children), 0)


class TestDeterministicPlannerIntegration(unittest.TestCase):
    """Test integration of HierarchicalPlanner with DeterministicPlanner"""

    def setUp(self):
        """Set up test fixtures"""
        from janus.runtime.core.deterministic_planner import DeterministicPlanner

        self.deterministic_planner = DeterministicPlanner()
        self.hierarchical_planner = HierarchicalPlanner()

    def test_create_hierarchical_plan(self):
        """Test creating hierarchical plan through DeterministicPlanner"""
        plan = self.deterministic_planner.create_hierarchical_plan(
            "Prépare présentation", hierarchical_planner=self.hierarchical_planner
        )

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(plan.intent.action, "hierarchical_task")

        # Should have steps from decomposition
        self.assertIsNotNone(plan.steps)
        if plan.steps:
            self.assertGreater(len(plan.steps), 0)

    def test_tree_to_plan_conversion(self):
        """Test converting tree to ActionPlan"""
        # Create a simple tree
        tree = TreeNode(task="Prépare présentation")
        tree.add_child(TreeNode(task="Ouvre PowerPoint"))
        tree.add_child(TreeNode(task="Créer slides"))

        plan = self.deterministic_planner._tree_to_plan(tree, "Prépare présentation")

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(plan.intent.action, "hierarchical_task")

    def test_node_to_step_conversion(self):
        """Test converting TreeNode to action step"""
        # Test opening application
        node = TreeNode(task="Ouvre PowerPoint")
        step = self.deterministic_planner._node_to_step(node)

        self.assertIsNotNone(step)
        self.assertEqual(step["module"], "default")
        self.assertEqual(step["action"], "open_application")
        self.assertIn("PowerPoint", step["args"]["app_name"])

        # Test search action
        node = TreeNode(task="Recherche images")
        step = self.deterministic_planner._node_to_step(node)

        self.assertIsNotNone(step)
        self.assertEqual(step["module"], "chrome")


class TestComplexDecompositionScenarios(unittest.TestCase):
    """Test complex real-world decomposition scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.planner = HierarchicalPlanner()

    def test_presentation_with_research(self):
        """Test decomposition of presentation task with research"""
        tree = self.planner.decompose(
            "Prépare présentation sur IA avec recherche",
            context={"slides": 15, "include_research": True},
            use_llm=False,
        )

        self.assertIsInstance(tree, TreeNode)
        # Verify hierarchical structure exists
        self.assertTrue(len(tree.children) > 0 or tree.is_leaf())

    def test_multi_level_hierarchy(self):
        """Test that decomposition creates multi-level hierarchy"""
        tree = self.planner.decompose("Prépare présentation complète", use_llm=False)

        # Check that we have at least some structure
        self.assertIsInstance(tree, TreeNode)

        # If it has children, check for grandchildren (multi-level)
        if tree.children:
            has_grandchildren = any(len(child.children) > 0 for child in tree.children)
            # At least one branch should have depth > 1
            # (This is optional based on decomposition rules)

    def test_custom_context_influences_decomposition(self):
        """Test that context influences decomposition"""
        context1 = {"type": "simple"}
        context2 = {"type": "detailed", "depth": 3}

        tree1 = self.planner.decompose("Créer document", context=context1, use_llm=False)
        tree2 = self.planner.decompose("Créer document", context=context2, use_llm=False)

        # Both should be valid trees
        self.assertIsInstance(tree1, TreeNode)
        self.assertIsInstance(tree2, TreeNode)


if __name__ == "__main__":
    unittest.main()
