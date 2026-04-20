#!/usr/bin/env python3
"""Test to identify the height calculation bug."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

print("\n" + "=" * 70)
print(" NEW MESSAGE HEIGHT BUG DIAGNOSIS")
print("=" * 70)

from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget
import inspect

print("\nProblem Analysis:")
print("-" * 70)

print("\n1. _on_rows_inserted is called when new message added:")
source = inspect.getsource(AgentChatListWidget._on_rows_inserted)
print("   ✓ It calls _rebuild_positions_cache(force=True) immediately")

print("\n2. _rebuild_positions_cache calls get_item_size_hint:")
source = inspect.getsource(AgentChatListWidget._rebuild_positions_cache)
print("   ✓ Uses: option.rect = self.list_view.viewport().rect()")
print("   ✓ If viewport not laid out yet, rect.width() could be 0 or very small")

print("\n3. _refresh_visible_widgets creates widgets:")
source = inspect.getsource(AgentChatListWidget._refresh_visible_widgets)
print("   ✓ Uses: widget_width = max(1, self.list_view.viewport().width())")

print("\n" + "=" * 70)
print(" THE BUG: WIDTH MISMATCH")
print("=" * 70)

print("\nScenario:")
print("--------")
print("1. New message added")
print("2. _on_rows_inserted triggered")
print("3. _rebuild_positions_cache called:")
print("   - option.rect.width() = 0 (viewport not laid out)")
print("   - calc_width = max(400, 0) = 400")
print("   - Height calculated based on width 400")
print("   - Cached with key 400")
print("4. _refresh_visible_widgets called:")
print("   - widget_width = max(1, viewport.width()) = 800")
print("   - Looking for cache with key 800")
print("   - Cache miss! Recalculating height with width 800")
print("   - NEW height != OLD height from step 3!")
print("5. Position cache has OLD height, widget has NEW height")
print("   → Display is WRONG! Widgets overlap or have gaps!")

print("\n" + "=" * 70)
print(" SOLUTION")
print("=" * 70)

print("\nOption 1: Don't rebuild cache in _on_rows_inserted")
print("  → Only mark as dirty, let _refresh_visible_widgets handle it")

print("\nOption 2: Ensure consistent width calculation")
print("  → Always use viewport().width() directly")
print("  → Remove MIN_SIZING_WIDTH for cache key")

print("\nOption 3: Defer cache rebuild until after viewport is ready")
print("  → Check viewport size before rebuilding")
print("  → Force layout if viewport is too small")

print("\nRecommended: Option 1 + Option 3")
print("  → Don't rebuild immediately")
print("  → Let _refresh_visible_widgets handle it with proper viewport")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" NEXT STEPS")
    print("=" * 70)
    print("\n1. Remove immediate cache rebuild from _on_rows_inserted")
    print("2. Only invalidate cache (mark as dirty)")
    print("3. Let _refresh_visible_widgets handle rebuild at right time")
    print("4. Ensure viewport is properly laid out before rebuilding")
