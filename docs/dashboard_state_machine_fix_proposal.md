# Dashboard State Machine Fix Proposal

## 1. Summary of Findings

After multiple attempts to fix the batch-update behavior by modifying the `ReplayViewerEngine`, a log analysis proved that the engine is now working correctly. The latest version of the engine uses an event queue to process a continuous stream of small event chunks, which are sent to the dashboard in real-time.

However, the dashboard UI did not reflect this corrected behavior. A detailed log comparison showed that while the engine was sending a constant stream of granular update events (e.g., `wo_status_changed`), the dashboard was not processing them after its initial load. The absence of corresponding log messages from the dashboard process confirmed it was ignoring these events.

## 2. Root Cause Hypothesis

The root cause is a bug in the dashboard's internal state machine. The `WorkOrderDashboard` class in `work_order_dashboard.py` uses a boolean flag, `self._is_rebuilding_state`, to control its behavior.

1.  This flag is set to `True` when a `STATE_RESET` event is received. This is intended to stop the dashboard from processing incremental updates while it awaits a full `STATE_SNAPSHOT` to rebuild its state.
2.  It is supposed to be set back to `False` after the `STATE_SNAPSHOT` has been successfully processed.

The evidence strongly suggests that this flag is not being correctly reset to `False` after the initial state is loaded. Because the flag remains `True`, the dashboard stays in a permanent "rebuilding" mode, causing it to ignore all subsequent granular events.

## 3. Proposed Solution

The fix must be implemented entirely within `src/subsystems/visualization/work_order_dashboard.py`.

1.  **Analyze Control Flow:** A careful review of the `_handle_state_reset` and `_handle_state_snapshot` methods is required.
2.  **Identify Logical Flaw:** The analysis must pinpoint why `self._is_rebuilding_state` is not being reset to `False`. There may be a duplicate or misplaced line of code from a previous merge or refactor that is causing the final state-rebuilt logic to be unreachable.
3.  **Correct the Logic:** Modify the `_handle_state_snapshot` method to ensure `self._is_rebuilding_state = False` is executed reliably as the final step of the state rebuild process.

## 4. Expected Outcome

Once the fix is applied, the dashboard will correctly transition out of the "rebuilding" state after loading the initial snapshot. This will "unblock" the granular event handlers (`_handle_wo_status_changed`, etc.), allowing the dashboard to process the continuous stream of events from the engine and update the UI in real-time, as intended.

## 5. Post-Implementation Note

The proposed solution was implemented and the dashboard's state machine is now working correctly. The `_is_rebuilding_state` flag is now correctly reset to `False` after the state is rebuilt from a snapshot.

Further improvements have been made to the simulation and dashboard:

-   A new `picked` status has been added to the work order lifecycle for more granular tracking.
-   The frequency of `work_order_update` events has been increased to every step of an agent's movement, providing a much smoother and more accurate real-time view.