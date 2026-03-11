import asyncio
import time
from brain_core import NSAOrchestrator

async def main():
    brain = NSAOrchestrator()
    pred = brain.predictive_cortex
    
    # Mock the CPU measurer to simulate a clear rising trend toward 90% threshold
    # 60, 68, 76, 84 ... trend is +8 per sample, threshold is 90
    cpu_values = [40, 50, 60, 68, 76, 84]
    measure_idx = 0
    
    def fake_cpu_measure():
        nonlocal measure_idx
        val = cpu_values[min(measure_idx, len(cpu_values)-1)]
        measure_idx += 1
        return val
        
    pred.channels["cpu_percent"].measurer = fake_cpu_measure
    
    print("=============================================")
    print("👁️ Testing Anticipatory Sensing Pipeline...")
    print("=============================================")
    
    # Feed values to build the trend
    for i in range(5):
        val = fake_cpu_measure()
        measure_idx -= 1 # Rewind so predict_cycle can sample it
        print(f"\n--- Cycle {i+1}: Forcing CPU Measurement to {val}% ---")
        
        await pred.predict_cycle()
        
        ch = pred.channels["cpu_percent"]
        print(f"  Channel State: {ch.status} (trend: {ch.trend:.2f}, conf: {ch.confidence:.2f})")
        pred_str = f"{ch.predicted_value:.2f}%" if ch.predicted_value is not None else "N/A"
        print(f"  Predicted Value: {pred_str} (Threshold: {ch.threshold}%)")
        
        await asyncio.sleep(1)
        
    print("\n✅ Test execution completed. Watch logs above for pre-allocation and phantom spikes.")

if __name__ == "__main__":
    asyncio.run(main())
