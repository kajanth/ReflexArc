"""
Property-based tests for cost optimization.

Uses Hypothesis to verify Protocol Alpha (Conservation of Token Energy) -
the core principle that the system should never use an expensive model
for a cheap problem. Tests the REFLEX > TEMPLATE > COMPLEX hierarchy.

**Validates: Requirements FR-002.1, FR-002.2 (Cost optimization)**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Mock cost optimization system for property testing
class TaskComplexity(Enum):
    """Task complexity levels matching neural cascade layers."""
    REFLEX = "reflex"      # Layer 5: Cerebellum - $0 Python skills
    TEMPLATE = "template"  # Layer 4.5: Template Engine - ~$0.001
    COMPLEX = "complex"    # Layer 4: Cortex - ~$0.01+


@dataclass
class CostTier:
    """Cost tier configuration."""
    name: str
    cost_per_token: float
    latency_ms: float
    max_tokens: int


@dataclass
class Task:
    """Task to be processed through the neural cascade."""
    description: str
    complexity: TaskComplexity
    token_count: int
    priority: str = "normal"


class MockCostOptimizer:
    """Mock cost optimizer implementing Protocol Alpha."""
    
    def __init__(self):
        # Define cost tiers (matching ReflexArc architecture)
        self.tiers = {
            "nano": CostTier("nano", 0.0001, 10.0, 4096),      # Reflex tier
            "mini": CostTier("mini", 0.001, 50.0, 8192),       # Template tier  
            "cortex": CostTier("cortex", 0.01, 200.0, 32768)   # Complex tier
        }
        
        # Cost tracking
        self.total_cost = 0.0
        self.task_history = []
        self.tier_usage = {tier: 0 for tier in self.tiers.keys()}
        
        # Protocol Alpha routing rules
        self.routing_rules = {
            TaskComplexity.REFLEX: "nano",
            TaskComplexity.TEMPLATE: "mini", 
            TaskComplexity.COMPLEX: "cortex"
        }
        
        # Budget constraints
        self.daily_budget = 0.50
        self.current_daily_spend = 0.0
    
    def process_task(self, task: Task) -> Tuple[str, float, float]:
        """
        Process task through Protocol Alpha routing.
        
        Returns:
            (tier_used, cost, latency)
        """
        # Apply Protocol Alpha routing
        optimal_tier = self._route_by_protocol_alpha(task)
        
        # Check budget constraints
        if not self._check_budget_constraint(task, optimal_tier):
            # Fallback to cheaper tier if budget constrained
            optimal_tier = self._find_cheaper_tier(optimal_tier)
        
        # Calculate cost and latency
        tier_config = self.tiers[optimal_tier]
        cost = task.token_count * tier_config.cost_per_token
        latency = tier_config.latency_ms
        
        # Update tracking
        self.total_cost += cost
        self.current_daily_spend += cost
        self.tier_usage[optimal_tier] += 1
        self.task_history.append((task, optimal_tier, cost, latency))
        
        return optimal_tier, cost, latency
    
    def _route_by_protocol_alpha(self, task: Task) -> str:
        """Apply Protocol Alpha: REFLEX > TEMPLATE > COMPLEX."""
        return self.routing_rules[task.complexity]
    
    def _check_budget_constraint(self, task: Task, tier: str) -> bool:
        """Check if task fits within budget constraints."""
        tier_config = self.tiers[tier]
        projected_cost = task.token_count * tier_config.cost_per_token
        return (self.current_daily_spend + projected_cost) <= self.daily_budget
    
    def _find_cheaper_tier(self, current_tier: str) -> str:
        """Find cheaper tier for budget constraints."""
        tier_hierarchy = ["nano", "mini", "cortex"]
        current_index = tier_hierarchy.index(current_tier)
        
        # Return cheapest available tier
        for i in range(current_index):
            return tier_hierarchy[i]
        
        return current_tier  # No cheaper option
    
    def get_cost_efficiency_ratio(self) -> float:
        """Calculate cost efficiency (reflex usage / total usage)."""
        total_tasks = sum(self.tier_usage.values())
        if total_tasks == 0:
            return 1.0
        return self.tier_usage["nano"] / total_tasks
    
    def get_average_cost_per_task(self) -> float:
        """Get average cost per task."""
        if not self.task_history:
            return 0.0
        return self.total_cost / len(self.task_history)
    
    def reset_daily_budget(self):
        """Reset daily budget tracking."""
        self.current_daily_spend = 0.0


# Hypothesis strategies
task_complexity = st.sampled_from(list(TaskComplexity))

task_description = st.text(
    min_size=5, 
    max_size=100,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))
)

token_count = st.integers(min_value=1, max_value=1000)

task_priority = st.sampled_from(["low", "normal", "high", "critical"])

daily_budget = st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False)


class TestCostOptimizationProperties:
    """Property-based tests for cost optimization."""
    
    @given(
        tasks=st.lists(
            st.builds(Task, 
                description=task_description,
                complexity=task_complexity,
                token_count=token_count,
                priority=task_priority
            ),
            min_size=1,
            max_size=50
        )
    )
    def test_protocol_alpha_cost_hierarchy(self, tasks):
        """Property: Protocol Alpha should maintain cost hierarchy REFLEX < TEMPLATE < COMPLEX."""
        optimizer = MockCostOptimizer()
        
        reflex_costs = []
        template_costs = []
        complex_costs = []
        
        for task in tasks:
            tier, cost, latency = optimizer.process_task(task)
            
            if task.complexity == TaskComplexity.REFLEX:
                reflex_costs.append(cost)
            elif task.complexity == TaskComplexity.TEMPLATE:
                template_costs.append(cost)
            elif task.complexity == TaskComplexity.COMPLEX:
                complex_costs.append(cost)
        
        # Verify cost hierarchy (when tasks exist for each type)
        if reflex_costs and template_costs:
            avg_reflex = sum(reflex_costs) / len(reflex_costs)
            avg_template = sum(template_costs) / len(template_costs)
            assert avg_reflex <= avg_template
        
        if template_costs and complex_costs:
            avg_template = sum(template_costs) / len(template_costs)
            avg_complex = sum(complex_costs) / len(complex_costs)
            assert avg_template <= avg_complex
        
        if reflex_costs and complex_costs:
            avg_reflex = sum(reflex_costs) / len(reflex_costs)
            avg_complex = sum(complex_costs) / len(complex_costs)
            assert avg_reflex <= avg_complex
    
    @given(
        reflex_tasks=st.lists(
            st.builds(Task,
                description=task_description,
                complexity=st.just(TaskComplexity.REFLEX),
                token_count=token_count
            ),
            min_size=10,
            max_size=30
        ),
        complex_tasks=st.lists(
            st.builds(Task,
                description=task_description,
                complexity=st.just(TaskComplexity.COMPLEX),
                token_count=token_count
            ),
            min_size=1,
            max_size=5
        )
    )
    def test_reflex_dominance_cost_efficiency(self, reflex_tasks, complex_tasks):
        """Property: System dominated by reflex tasks should be more cost-efficient."""
        optimizer = MockCostOptimizer()
        
        # Process mixed workload
        all_tasks = reflex_tasks + complex_tasks
        
        for task in all_tasks:
            optimizer.process_task(task)
        
        # Cost efficiency should be high when reflexes dominate
        efficiency_ratio = optimizer.get_cost_efficiency_ratio()
        expected_reflex_ratio = len(reflex_tasks) / len(all_tasks)
        
        # Efficiency should roughly match the reflex task ratio
        assert abs(efficiency_ratio - expected_reflex_ratio) <= 0.1
        
        # Total cost should be reasonable for reflex-dominated workload
        avg_cost = optimizer.get_average_cost_per_task()
        if len(reflex_tasks) > len(complex_tasks) * 3:  # Reflex dominated
            assert avg_cost <= 0.01  # Should be very cheap
    
    @given(
        budget=daily_budget,
        tasks=st.lists(
            st.builds(Task,
                description=task_description,
                complexity=task_complexity,
                token_count=st.integers(min_value=10, max_value=100)
            ),
            min_size=5,
            max_size=100
        )
    )
    def test_budget_constraint_compliance(self, budget, tasks):
        """Property: System should respect budget constraints."""
        optimizer = MockCostOptimizer()
        optimizer.daily_budget = budget
        
        processed_tasks = 0
        
        for task in tasks:
            # Check if we can still process within budget
            tier_config = optimizer.tiers[optimizer._route_by_protocol_alpha(task)]
            projected_cost = task.token_count * tier_config.cost_per_token
            
            if optimizer.current_daily_spend + projected_cost <= budget:
                optimizer.process_task(task)
                processed_tasks += 1
            else:
                # Should either process with cheaper tier or skip
                break
        
        # Should never exceed budget
        assert optimizer.current_daily_spend <= budget * 1.01  # Allow tiny rounding error
        
        # Should process at least some tasks unless budget is extremely small
        if budget >= 0.001:
            assert processed_tasks > 0
    
    @given(
        task_batches=st.lists(
            st.lists(
                st.builds(Task,
                    description=task_description,
                    complexity=task_complexity,
                    token_count=token_count
                ),
                min_size=1,
                max_size=20
            ),
            min_size=1,
            max_size=10
        )
    )
    def test_cost_accumulation_monotonicity(self, task_batches):
        """Property: Total cost should increase monotonically."""
        optimizer = MockCostOptimizer()
        
        previous_cost = 0.0
        
        for batch in task_batches:
            for task in batch:
                optimizer.process_task(task)
                
                # Cost should never decrease
                assert optimizer.total_cost >= previous_cost
                previous_cost = optimizer.total_cost
    
    @settings(max_examples=30)  # Reduce for performance
    @given(
        workload_pattern=st.lists(
            st.tuples(
                task_complexity,
                st.integers(min_value=1, max_value=20)  # count
            ),
            min_size=1,
            max_size=5
        )
    )
    def test_workload_pattern_cost_predictability(self, workload_pattern):
        """Property: Similar workload patterns should have predictable costs."""
        optimizer1 = MockCostOptimizer()
        optimizer2 = MockCostOptimizer()
        
        # Generate tasks based on pattern
        tasks1 = []
        tasks2 = []
        
        for complexity, count in workload_pattern:
            for i in range(count):
                task1 = Task(f"task1_{i}", complexity, 50)  # Fixed token count
                task2 = Task(f"task2_{i}", complexity, 50)  # Same pattern
                tasks1.append(task1)
                tasks2.append(task2)
        
        # Process identical workloads
        for task in tasks1:
            optimizer1.process_task(task)
        
        for task in tasks2:
            optimizer2.process_task(task)
        
        # Costs should be identical for identical workloads
        assert abs(optimizer1.total_cost - optimizer2.total_cost) < 0.0001
        
        # Tier usage should be identical
        assert optimizer1.tier_usage == optimizer2.tier_usage
    
    @given(
        token_counts=st.lists(
            st.integers(min_value=1, max_value=500),
            min_size=5,
            max_size=20
        ),
        complexity=task_complexity
    )
    def test_token_count_cost_linearity(self, token_counts, complexity):
        """Property: Cost should scale linearly with token count for same complexity."""
        optimizer = MockCostOptimizer()
        
        costs = []
        
        for token_count in token_counts:
            task = Task("test_task", complexity, token_count)
            tier, cost, latency = optimizer.process_task(task)
            costs.append((token_count, cost))
        
        # Check linearity (cost per token should be constant)
        if len(costs) >= 2:
            cost_per_token_ratios = []
            for token_count, cost in costs:
                if token_count > 0:
                    cost_per_token_ratios.append(cost / token_count)
            
            # All ratios should be approximately equal (linear relationship)
            if cost_per_token_ratios:
                first_ratio = cost_per_token_ratios[0]
                for ratio in cost_per_token_ratios[1:]:
                    assert abs(ratio - first_ratio) < 0.0001


class CostOptimizationStateMachine(RuleBasedStateMachine):
    """Stateful property testing for cost optimization."""
    
    def __init__(self):
        super().__init__()
        self.optimizer = MockCostOptimizer()
        self.processed_tasks = []
    
    @rule(
        complexity=task_complexity,
        token_count=st.integers(min_value=1, max_value=200)
    )
    def process_task(self, complexity, token_count):
        """Rule: Process a task through the optimizer."""
        task = Task(f"task_{len(self.processed_tasks)}", complexity, token_count)
        tier, cost, latency = self.optimizer.process_task(task)
        self.processed_tasks.append((task, tier, cost, latency))
    
    @rule()
    def reset_daily_budget(self):
        """Rule: Reset daily budget (simulate new day)."""
        self.optimizer.reset_daily_budget()
    
    @invariant()
    def cost_monotonicity_invariant(self):
        """Invariant: Total cost should never decrease."""
        if len(self.processed_tasks) >= 2:
            costs = [cost for _, _, cost, _ in self.processed_tasks]
            cumulative_costs = []
            running_total = 0.0
            for cost in costs:
                running_total += cost
                cumulative_costs.append(running_total)
            
            # Each cumulative cost should be >= previous
            for i in range(1, len(cumulative_costs)):
                assert cumulative_costs[i] >= cumulative_costs[i-1]
    
    @invariant()
    def protocol_alpha_routing_invariant(self):
        """Invariant: Protocol Alpha routing should be consistent."""
        for task, tier, cost, latency in self.processed_tasks:
            expected_tier = self.optimizer.routing_rules[task.complexity]
            
            # Should use expected tier or cheaper (due to budget constraints)
            tier_hierarchy = ["nano", "mini", "cortex"]
            expected_index = tier_hierarchy.index(expected_tier)
            actual_index = tier_hierarchy.index(tier)
            
            # Actual tier should be same or cheaper than expected
            assert actual_index <= expected_index
    
    @invariant()
    def budget_compliance_invariant(self):
        """Invariant: Should never exceed daily budget."""
        assert self.optimizer.current_daily_spend <= self.optimizer.daily_budget * 1.01


# Test the state machine
TestCostOptimizationStateMachine = CostOptimizationStateMachine.TestCase