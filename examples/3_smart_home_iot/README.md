# 🏠 Use Case 3: Smart Home IoT Automator

This example mimics a highly-advanced Home Assistant brain designed to maximize comfort and reduce energy waste securely.

## Scenario
The Brain receives constant telemetrics representing light levels, motion, temperature, and open/close door states.

1. **Prefrontal Cortex (Goals)**: "Keep Energy Usage under 500 kWh." 
2. **Predictive Cortex (Forecasting)**: An exponential smoothing model runs locally every minute to forecast tomorrow's energy usage based on today's thermostat habits.
3. **The Spike Incident**: 
   - A `room_temp` spike shows the living room hitting `82.5°F`. 
   - A `vision` spike triggers due to unexpected motion at the front door while the occupants are supposed to be out.
4. **Resolution**: 
   - **Temp Spikes** -> **Reflex**: An API call automatically fires to a smart-thermostat skill to turn on the AC.
   - **Motion Spikes + Nobody Home** -> **Cortex**: Routes as a security anomaly. GPT-4o analyzes the recent visual frames, decides if it's the mailman or an intruder, and potentially triggers the `alert_notify` skill to send an SMS.

## How to Run

1. **Start the Brain** using this specific configuration:
   ```bash
   # Make sure you are in the root of the ReflexArc project
   NSA_BRAIN_CONFIG=examples/3_smart_home_iot/brain.yaml python main.py
   ```

2. **Trigger Support Tickets**:
   Open a terminal and run the simulation script to send the IoT data over webhook interface:
   ```bash
   bash examples/3_smart_home_iot/simulate.sh
   ```

3. **Watch the Cascade**:
   Navigate to `http://localhost:8080` to see the predictive models and metric breaches in action.
