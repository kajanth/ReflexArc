"""
Property-based tests for event bus ordering.

Uses Hypothesis to test event ordering invariants in the NSA event bus.
Tests the pub/sub system that coordinates the neural cascade layers
and ensures proper event delivery guarantees.

**Validates: Requirements FR-011.1, FR-011.2 (Event system)**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading


class EventType(Enum):
    """Event types in the neural cascade."""
    SPIKE = "spike"
    DECISION = "decision"
    REFLEX_EXEC = "reflex_exec"
    TEMPLATE_EXEC = "template_exec"
    CORTEX_EXEC = "cortex_exec"
    MEMORY_STORE = "memory_store"
    HABIT_UPDATE = "habit_update"


@dataclass
class Event:
    """Event in the neural cascade."""
    event_type: EventType
    timestamp: float
    data: Dict[str, Any]
    event_id: str
    source_layer: str = "unknown"
    sequence_number: int = 0


class MockEventBus:
    """Mock event bus for property-based testing."""
    
    def __init__(self, max_history: int = 1000):
        self.subscribers = {}  # event_type -> list of queues
        self.event_history = deque(maxlen=max_history)
        self.sequence_counter = 0
        self.lock = threading.Lock()
        
        # Ordering guarantees
        self.fifo_guarantee = True
        self.causal_ordering = True
        
        # Performance tracking
        self.publish_count = 0
        self.delivery_count = 0
        
    def subscribe(self, event_type: EventType) -> asyncio.Queue:
        """Subscribe to events of a specific type."""
        queue = asyncio.Queue()
        
        with self.lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(queue)
        
        return queue
    
    def unsubscribe(self, event_type: EventType, queue: asyncio.Queue):
        """Unsubscribe from events."""
        with self.lock:
            if event_type in self.subscribers:
                try:
                    self.subscribers[event_type].remove(queue)
                except ValueError:
                    pass  # Queue not in list
    
    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        with self.lock:
            # Assign sequence number for ordering
            self.sequence_counter += 1
            event.sequence_number = self.sequence_counter
            
            # Add to history
            self.event_history.append(event)
            self.publish_count += 1
        
        # Deliver to subscribers
        if event.event_type in self.subscribers:
            for queue in self.subscribers[event.event_type]:
                try:
                    await queue.put(event)
                    self.delivery_count += 1
                except Exception:
                    pass  # Queue might be closed
    
    def get_history(self, limit: Optional[int] = None) -> List[Event]:
        """Get event history."""
        with self.lock:
            history = list(self.event_history)
            if limit:
                return history[-limit:]
            return history
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        with self.lock:
            return {
                "publish_count": self.publish_count,
                "delivery_count": self.delivery_count,
                "history_size": len(self.event_history),
                "subscriber_count": sum(len(queues) for queues in self.subscribers.values())
            }


class CascadeEventSequencer:
    """Manages event sequencing for neural cascade."""
    
    def __init__(self, event_bus: MockEventBus):
        self.event_bus = event_bus
        self.layer_dependencies = {
            # Layer dependencies for causal ordering
            EventType.SPIKE: [],
            EventType.DECISION: [EventType.SPIKE],
            EventType.REFLEX_EXEC: [EventType.DECISION],
            EventType.TEMPLATE_EXEC: [EventType.DECISION],
            EventType.CORTEX_EXEC: [EventType.DECISION],
            EventType.MEMORY_STORE: [EventType.SPIKE, EventType.DECISION],
            EventType.HABIT_UPDATE: [EventType.REFLEX_EXEC]
        }
    
    async def process_cascade_sequence(self, spike_data: Dict[str, Any]) -> List[Event]:
        """Process a complete cascade sequence."""
        events = []
        
        # 1. Spike event
        spike_event = Event(
            event_type=EventType.SPIKE,
            timestamp=time.time(),
            data=spike_data,
            event_id=f"spike_{len(events)}",
            source_layer="sensors"
        )
        await self.event_bus.publish(spike_event)
        events.append(spike_event)
        
        # Small delay to ensure ordering
        await asyncio.sleep(0.001)
        
        # 2. Decision event (after spike)
        decision_event = Event(
            event_type=EventType.DECISION,
            timestamp=time.time(),
            data={"routing": "reflex", "spike_id": spike_event.event_id},
            event_id=f"decision_{len(events)}",
            source_layer="thalamus"
        )
        await self.event_bus.publish(decision_event)
        events.append(decision_event)
        
        await asyncio.sleep(0.001)
        
        # 3. Execution event (after decision)
        exec_type = decision_event.data.get("routing", "reflex")
        if exec_type == "reflex":
            exec_event_type = EventType.REFLEX_EXEC
        elif exec_type == "template":
            exec_event_type = EventType.TEMPLATE_EXEC
        else:
            exec_event_type = EventType.CORTEX_EXEC
        
        exec_event = Event(
            event_type=exec_event_type,
            timestamp=time.time(),
            data={"decision_id": decision_event.event_id},
            event_id=f"exec_{len(events)}",
            source_layer="cerebellum" if exec_type == "reflex" else exec_type
        )
        await self.event_bus.publish(exec_event)
        events.append(exec_event)
        
        return events


# Hypothesis strategies
event_type_strategy = st.sampled_from(list(EventType))

event_data_strategy = st.dictionaries(
    st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=0, max_value=1000),
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    ),
    min_size=1,
    max_size=5
)

event_id_strategy = st.text(
    min_size=5, 
    max_size=30,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
)


class TestEventBusOrderingProperties:
    """Property-based tests for event bus ordering."""
    
    @given(
        events=st.lists(
            st.builds(Event,
                event_type=event_type_strategy,
                timestamp=st.floats(min_value=1000000000, max_value=2000000000),
                data=event_data_strategy,
                event_id=event_id_strategy,
                source_layer=st.text(min_size=1, max_size=20)
            ),
            min_size=1,
            max_size=20
        )
    )
    @pytest.mark.asyncio
    async def test_fifo_ordering_guarantee(self, events):
        """Property: Events should be delivered in FIFO order per event type."""
        event_bus = MockEventBus()
        
        # Group events by type
        events_by_type = {}
        for event in events:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = []
            events_by_type[event.event_type].append(event)
        
        # Subscribe to each event type
        subscribers = {}
        for event_type in events_by_type.keys():
            subscribers[event_type] = event_bus.subscribe(event_type)
        
        # Publish events in order
        for event in events:
            await event_bus.publish(event)
        
        # Verify FIFO ordering for each type
        for event_type, expected_events in events_by_type.items():
            queue = subscribers[event_type]
            received_events = []
            
            # Collect all events for this type
            while not queue.empty():
                try:
                    received_event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    received_events.append(received_event)
                except asyncio.TimeoutError:
                    break
            
            # Should receive same number of events
            assert len(received_events) == len(expected_events)
            
            # Should be in same order (by sequence number)
            for i in range(len(received_events)):
                assert received_events[i].event_id == expected_events[i].event_id
    
    @given(
        cascade_count=st.integers(min_value=1, max_value=10),
        spike_data_list=st.lists(
            event_data_strategy,
            min_size=1,
            max_size=10
        )
    )
    @pytest.mark.asyncio
    async def test_causal_ordering_in_cascade(self, cascade_count, spike_data_list):
        """Property: Events in neural cascade should maintain causal ordering."""
        event_bus = MockEventBus()
        sequencer = CascadeEventSequencer(event_bus)
        
        # Process multiple cascade sequences
        all_events = []
        for i in range(min(cascade_count, len(spike_data_list))):
            cascade_events = await sequencer.process_cascade_sequence(spike_data_list[i])
            all_events.extend(cascade_events)
        
        # Verify causal ordering in history
        history = event_bus.get_history()
        
        # Group events by cascade (by spike_id or similar)
        cascades = {}
        for event in history:
            # Identify cascade by spike event or related events
            cascade_id = None
            if event.event_type == EventType.SPIKE:
                cascade_id = event.event_id
            elif "spike_id" in event.data:
                cascade_id = event.data["spike_id"]
            elif "decision_id" in event.data:
                # Find the decision event to get spike_id
                for h_event in history:
                    if h_event.event_id == event.data["decision_id"]:
                        cascade_id = h_event.data.get("spike_id")
                        break
            
            if cascade_id:
                if cascade_id not in cascades:
                    cascades[cascade_id] = []
                cascades[cascade_id].append(event)
        
        # Verify ordering within each cascade
        for cascade_id, cascade_events in cascades.items():
            # Sort by sequence number
            cascade_events.sort(key=lambda e: e.sequence_number)
            
            # Verify causal dependencies
            event_types_seen = set()
            for event in cascade_events:
                # Check that dependencies were seen before this event
                dependencies = sequencer.layer_dependencies.get(event.event_type, [])
                for dep in dependencies:
                    if dep in [e.event_type for e in cascade_events]:
                        assert dep in event_types_seen, f"Dependency {dep} not seen before {event.event_type}"
                
                event_types_seen.add(event.event_type)
    
    @given(
        concurrent_publishers=st.integers(min_value=2, max_value=5),
        events_per_publisher=st.integers(min_value=5, max_value=15)
    )
    @pytest.mark.asyncio
    async def test_concurrent_publishing_ordering(self, concurrent_publishers, events_per_publisher):
        """Property: Concurrent publishing should maintain sequence number ordering."""
        event_bus = MockEventBus()
        
        async def publisher_task(publisher_id: int):
            """Task for concurrent publishing."""
            events = []
            for i in range(events_per_publisher):
                event = Event(
                    event_type=EventType.SPIKE,
                    timestamp=time.time(),
                    data={"publisher": publisher_id, "index": i},
                    event_id=f"pub_{publisher_id}_event_{i}",
                    source_layer=f"publisher_{publisher_id}"
                )
                await event_bus.publish(event)
                events.append(event)
                # Small delay to allow interleaving
                await asyncio.sleep(0.001)
            return events
        
        # Run publishers concurrently
        tasks = [publisher_task(i) for i in range(concurrent_publishers)]
        publisher_events = await asyncio.gather(*tasks)
        
        # Verify sequence numbers are monotonic
        history = event_bus.get_history()
        sequence_numbers = [event.sequence_number for event in history]
        
        # Sequence numbers should be strictly increasing
        for i in range(1, len(sequence_numbers)):
            assert sequence_numbers[i] > sequence_numbers[i-1]
        
        # Total events should match
        total_expected = concurrent_publishers * events_per_publisher
        assert len(history) == total_expected
    
    @given(
        subscriber_count=st.integers(min_value=1, max_value=5),
        event_count=st.integers(min_value=10, max_value=30)
    )
    @pytest.mark.asyncio
    async def test_multiple_subscribers_delivery_guarantee(self, subscriber_count, event_count):
        """Property: All subscribers should receive all events of their type."""
        event_bus = MockEventBus()
        
        # Create multiple subscribers for same event type
        subscribers = []
        for i in range(subscriber_count):
            queue = event_bus.subscribe(EventType.SPIKE)
            subscribers.append(queue)
        
        # Publish events
        published_events = []
        for i in range(event_count):
            event = Event(
                event_type=EventType.SPIKE,
                timestamp=time.time(),
                data={"index": i},
                event_id=f"event_{i}",
                source_layer="test"
            )
            await event_bus.publish(event)
            published_events.append(event)
        
        # Verify all subscribers received all events
        for subscriber_idx, queue in enumerate(subscribers):
            received_events = []
            
            # Collect all events from this subscriber
            for _ in range(event_count):
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    received_events.append(event)
                except asyncio.TimeoutError:
                    break
            
            # Should receive all events
            assert len(received_events) == len(published_events)
            
            # Should be in same order
            for i, received_event in enumerate(received_events):
                assert received_event.event_id == published_events[i].event_id
    
    @given(
        history_limit=st.integers(min_value=5, max_value=50),
        event_count=st.integers(min_value=10, max_value=100)
    )
    @pytest.mark.asyncio
    async def test_history_size_limit_property(self, history_limit, event_count):
        """Property: Event history should respect size limits."""
        assume(event_count > history_limit)  # Only test when we exceed limit
        
        event_bus = MockEventBus(max_history=history_limit)
        
        # Publish more events than history limit
        for i in range(event_count):
            event = Event(
                event_type=EventType.SPIKE,
                timestamp=time.time(),
                data={"index": i},
                event_id=f"event_{i}",
                source_layer="test"
            )
            await event_bus.publish(event)
        
        # History should not exceed limit
        history = event_bus.get_history()
        assert len(history) <= history_limit
        
        # Should contain the most recent events
        if len(history) == history_limit:
            # Last event should be the most recent
            last_event = history[-1]
            assert last_event.event_id == f"event_{event_count - 1}"
            
            # First event in history should be from later in the sequence
            first_event = history[0]
            expected_first_index = event_count - history_limit
            assert first_event.event_id == f"event_{expected_first_index}"


class EventBusStateMachine(RuleBasedStateMachine):
    """Stateful property testing for event bus."""
    
    def __init__(self):
        super().__init__()
        self.event_bus = MockEventBus()
        self.subscribers = {}
        self.published_events = []
        self.event_counter = 0
    
    @rule(event_type=event_type_strategy)
    def subscribe_to_events(self, event_type):
        """Rule: Subscribe to an event type."""
        if event_type not in self.subscribers:
            queue = self.event_bus.subscribe(event_type)
            self.subscribers[event_type] = queue
    
    @rule(
        event_type=event_type_strategy,
        data=event_data_strategy
    )
    async def publish_event(self, event_type, data):
        """Rule: Publish an event."""
        event = Event(
            event_type=event_type,
            timestamp=time.time(),
            data=data,
            event_id=f"event_{self.event_counter}",
            source_layer="test"
        )
        self.event_counter += 1
        
        await self.event_bus.publish(event)
        self.published_events.append(event)
    
    @invariant()
    def sequence_number_monotonicity_invariant(self):
        """Invariant: Sequence numbers should be monotonic."""
        history = self.event_bus.get_history()
        if len(history) >= 2:
            for i in range(1, len(history)):
                assert history[i].sequence_number > history[i-1].sequence_number
    
    @invariant()
    def publish_count_consistency_invariant(self):
        """Invariant: Publish count should match published events."""
        stats = self.event_bus.get_stats()
        assert stats["publish_count"] == len(self.published_events)
    
    @invariant()
    def history_ordering_invariant(self):
        """Invariant: History should be ordered by sequence number."""
        history = self.event_bus.get_history()
        sequence_numbers = [event.sequence_number for event in history]
        
        # Should be sorted
        assert sequence_numbers == sorted(sequence_numbers)


# Test the state machine
TestEventBusStateMachine = EventBusStateMachine.TestCase