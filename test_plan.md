# Test Plan

## Goal

- Split and maintain clear **unit/integration** test strategy.
- Ensure **every code file** under `agent/`, `app/`, `server/`, `utils/` has unit-test coverage.

## Coverage Rule

- `✅` means file is covered by **specialized unit tests** in `tests/unit/...`
- `📋` means file is covered by **AST-only** validation (`tests/unit/test_meta/test_all_source_files_ast.py`)
- Priority: Add specialized tests for files marked `📋` that have complex logic

## Specialized Test Coverage Summary

| Category | Specialized Tests | AST-Only | Total |
|----------|------------------|----------|-------|
| agent/ | 33 | 92 | 125 |
| app/ | 23 | 231 | 254 |
| server/ | 5 | 28 | 33 |
| utils/ | 7 | 17 | 24 |
| **Total** | **68** | **368** | **436** |

## File Coverage Matrix

### agent/

- [x] `agent/__init__.py` 📋
- [x] `agent/chat/__init__.py` 📋
- [x] `agent/chat/agent_chat_message.py` ✅
- [x] `agent/chat/agent_chat_signals.py` 📋
- [x] `agent/chat/agent_chat_types.py` ✅
- [x] `agent/chat/content/__init__.py` ✅
- [x] `agent/chat/content/button_content.py` ✅
- [x] `agent/chat/content/code_content.py` ✅
- [x] `agent/chat/content/content_status.py` ✅
- [x] `agent/chat/content/crew_member_activity_content.py` ✅
- [x] `agent/chat/content/crew_member_read_content.py` ✅
- [x] `agent/chat/content/data_content.py` ✅
- [x] `agent/chat/content/error_content.py` ✅
- [x] `agent/chat/content/file_content.py` ✅
- [x] `agent/chat/content/form_content.py` ✅
- [x] `agent/chat/content/link_content.py` ✅
- [x] `agent/chat/content/llm_output_content.py` ✅
- [x] `agent/chat/content/media_content.py` ✅
- [x] `agent/chat/content/metadata_content.py` ✅
- [x] `agent/chat/content/plan_content.py` ✅
- [x] `agent/chat/content/progress_content.py` ✅
- [x] `agent/chat/content/skill_content.py` ✅
- [x] `agent/chat/content/structure_content.py` ✅
- [x] `agent/chat/content/text_content.py` ✅
- [x] `agent/chat/content/thinking_content.py` ✅
- [x] `agent/chat/content/todo_write_content.py` 📋
- [x] `agent/chat/content/tool_content.py` 📋
- [x] `agent/chat/content/typing_content.py` 📋
- [x] `agent/chat/history/__init__.py` 📋
- [x] `agent/chat/history/agent_chat_history_listener.py` 📋
- [x] `agent/chat/history/agent_chat_history_service.py` 📋
- [x] `agent/chat/history/agent_chat_storage.py` ✅
- [x] `agent/chat/history/global_sequence_manager.py` ✅
- [x] `agent/core/__init__.py` 📋
- [x] `agent/core/filmeto_constants.py` 📋
- [x] `agent/core/filmeto_crew.py` 📋
- [x] `agent/core/filmeto_instance.py` 📋
- [x] `agent/core/filmeto_plan.py` 📋
- [x] `agent/core/filmeto_routing.py` ✅
- [x] `agent/core/filmeto_utils.py` 📋
- [x] `agent/crew/__init__.py` 📋
- [x] `agent/crew/crew_member.py` 📋
- [x] `agent/crew/crew_member_history_service.py` 📋
- [x] `agent/crew/crew_service.py` 📋
- [x] `agent/crew/crew_title.py` 📋
- [x] `agent/event/__init__.py` 📋
- [x] `agent/event/agent_event.py` 📋
- [x] `agent/filmeto_agent.py` 📋
- [x] `agent/plan/__init__.py` 📋
- [x] `agent/plan/plan_models.py` ✅
- [x] `agent/plan/plan_service.py` ✅
- [x] `agent/plan/plan_signals.py` 📋
- [x] `agent/prompt/__init__.py` 📋
- [x] `agent/prompt/prompt_service.py` 📋
- [x] `agent/react/__init__.py` 📋
- [x] `agent/react/actions.py` ✅
- [x] `agent/react/constants.py` ✅
- [x] `agent/react/json_utils.py` ✅
- [x] `agent/react/parser.py` ✅
- [x] `agent/react/react.py` 📋
- [x] `agent/react/react_service.py` 📋
- [x] `agent/react/status.py` 📋
- [x] `agent/react/todo.py` 📋
- [x] `agent/react/types.py` 📋
- [x] `agent/router/__init__.py` 📋
- [x] `agent/router/message_router_service.py` ✅
- [x] `agent/router/message_target.py` ✅
- [x] `agent/skill/__init__.py` 📋
- [x] `agent/skill/skill_chat.py` 📋
- [x] `agent/skill/skill_models.py` 📋
- [x] `agent/skill/skill_service.py` ✅
- [x] `agent/skill/system/delete_scene/scripts/delete_single_scene.py` 📋
- [x] `agent/skill/system/delete_screen_play/scripts/delete_screen_play.py` 📋
- [x] `agent/skill/system/read_scene/scripts/read_single_scene.py` 📋
- [x] `agent/skill/system/rewrite_screen_play/scripts/rewrite_screenplay.py` 📋
- [x] `agent/skill/system/write_scene/scripts/write_single_scene.py` 📋
- [x] `agent/soul/__init__.py` 📋
- [x] `agent/soul/soul.py` 📋
- [x] `agent/soul/soul_service.py` 📋
- [x] `agent/soul/system/__init__.py` 📋
- [x] `agent/tool/__init__.py` 📋
- [x] `agent/tool/base_tool.py` 📋
- [x] `agent/tool/system/__init__.py` 📋
- [x] `agent/tool/system/crew_member/__init__.py` 📋
- [x] `agent/tool/system/crew_member/crew_member_tool.py` 📋
- [x] `agent/tool/system/execute_generated_code/__init__.py` 📋
- [x] `agent/tool/system/execute_generated_code/execute_generated_code.py` 📋
- [x] `agent/tool/system/execute_skill/__init__.py` 📋
- [x] `agent/tool/system/execute_skill/execute_skill.py` 📋
- [x] `agent/tool/system/execute_skill_script/__init__.py` 📋
- [x] `agent/tool/system/execute_skill_script/execute_skill_script.py` 📋
- [x] `agent/tool/system/plan/__init__.py` 📋
- [x] `agent/tool/system/plan/plan_tool.py` 📋
- [x] `agent/tool/system/screen_play/__init__.py` 📋
- [x] `agent/tool/system/screen_play/screen_play_tool.py` 📋
- [x] `agent/tool/system/speak_to/__init__.py` 📋
- [x] `agent/tool/system/speak_to/speak_to_tool.py` 📋
- [x] `agent/tool/system/story_board/__init__.py` 📋
- [x] `agent/tool/system/story_board/story_board_tool.py` 📋
- [x] `agent/tool/system/timeline_item/__init__.py` 📋
- [x] `agent/tool/system/timeline_item/timeline_item_tool.py` 📋
- [x] `agent/tool/system/todo/__init__.py` 📋
- [x] `agent/tool/system/todo/todo_tool.py` 📋
- [x] `agent/tool/system/video_timeline/__init__.py` 📋
- [x] `agent/tool/system/video_timeline/video_timeline_tool.py` 📋
- [x] `agent/tool/tool_context.py` 📋
- [x] `agent/tool/tool_loader.py` 📋
- [x] `agent/tool/tool_service.py` 📋
- [x] `agent/utils.py` 📋

### app/

- [x] `app/__init__.py` 📋
- [x] `app/app.py` 📋
- [x] `app/constants.py` 📋
- [x] `app/data/__init__.py` 📋
- [x] `app/data/character.py` ✅
- [x] `app/data/drawing.py` ✅
- [x] `app/data/layer.py` ✅
- [x] `app/data/project.py` ✅
- [x] `app/data/prompt.py` ✅
- [x] `app/data/resource.py` ✅
- [x] `app/data/screen_play/__init__.py` 📋
- [x] `app/data/screen_play/scene_paths.py` ✅
- [x] `app/data/screen_play/screen_play_formatter.py` ✅
- [x] `app/data/screen_play/screen_play_manager.py` ✅
- [x] `app/data/screen_play/screen_play_manager_factory.py` ✅
- [x] `app/data/screen_play/screen_play_scene.py` ✅
- [x] `app/data/settings.py` ✅
- [x] `app/data/story_board/__init__.py` 📋
- [x] `app/data/story_board/shot_task_executor.py` ✅
- [x] `app/data/story_board/shot_task_manager.py` ✅
- [x] `app/data/story_board/story_board_manager.py` ✅
- [x] `app/data/story_board/story_board_shot.py` ✅
- [x] `app/data/task.py` ✅
- [x] `app/data/timeline.py` ✅
- [x] `app/data/workflow.py` ✅
- [x] `app/data/workspace.py` ✅
- [x] `app/plugins/__init__.py` 📋
- [x] `app/plugins/plugin_config_manager.py` 📋
- [x] `app/plugins/plugins.py` 📋
- [x] `app/plugins/service_registry.py` 📋
- [x] `app/plugins/tools/__init__.py` 📋
- [x] `app/plugins/tools/image2image/__init__.py` 📋
- [x] `app/plugins/tools/image2image/image2image.py` 📋
- [x] `app/plugins/tools/image2video/__init__.py` 📋
- [x] `app/plugins/tools/image2video/image2video.py` 📋
- [x] `app/plugins/tools/imageedit/__init__.py` 📋
- [x] `app/plugins/tools/imageedit/imageedit.py` 📋
- [x] `app/plugins/tools/speak2video/speak2video.py` 📋
- [x] `app/plugins/tools/text2image/__init__.py` 📋
- [x] `app/plugins/tools/text2image/text2image.py` 📋
- [x] `app/plugins/tools/text2music/text2music.py` 📋
- [x] `app/plugins/tools/text2speak/text2speak.py` 📋
- [x] `app/plugins/tools/text2video/text2video.py` 📋
- [x] `app/spi/__init__.py` 📋
- [x] `app/spi/model.py` 📋
- [x] `app/spi/service.py` 📋
- [x] `app/spi/tool.py` 📋
- [x] `app/ui/__init__.py` 📋
- [x] `app/ui/base_widget.py` 📋
- [x] `app/ui/canvas/__init__.py` 📋
- [x] `app/ui/canvas/canvas.py` 📋
- [x] `app/ui/canvas/canvas_editor.py` 📋
- [x] `app/ui/canvas/canvas_layer.py` 📋
- [x] `app/ui/canvas/canvas_pixmap.py` 📋
- [x] `app/ui/canvas/canvas_preview.py` 📋
- [x] `app/ui/chat/__init__.py` 📋
- [x] `app/ui/chat/agent_chat.py` ✅
- [x] `app/ui/chat/agent_chat_members.py` 📋
- [x] `app/ui/chat/list/__init__.py` 📋
- [x] `app/ui/chat/list/agent_chat_list_items.py` 📋
- [x] `app/ui/chat/list/agent_chat_list_model.py` 📋
- [x] `app/ui/chat/list/agent_chat_list_widget.py` 📋
- [x] `app/ui/chat/list/builders/__init__.py` 📋
- [x] `app/ui/chat/list/builders/message_builder.py` 📋
- [x] `app/ui/chat/list/builders/message_converter.py` 📋
- [x] `app/ui/chat/list/handlers/__init__.py` 📋
- [x] `app/ui/chat/list/handlers/qml_handler.py` 📋
- [x] `app/ui/chat/list/handlers/stream_event_handler.py` 📋
- [x] `app/ui/chat/list/managers/__init__.py` 📋
- [x] `app/ui/chat/list/managers/history_manager.py` 📋
- [x] `app/ui/chat/list/managers/metadata_resolver.py` 📋
- [x] `app/ui/chat/list/managers/scroll_manager.py` 📋
- [x] `app/ui/chat/list/managers/skill_manager.py` 📋
- [x] `app/ui/chat/plan/__init__.py` 📋
- [x] `app/ui/chat/plan/plan_view_model.py` 📋
- [x] `app/ui/chat/plan/plan_widget.py` 📋
- [x] `app/ui/chat/private_chat_widget.py` 📋
- [x] `app/ui/components/avatar_widget.py` 📋
- [x] `app/ui/core/__init__.py` 📋
- [x] `app/ui/core/base_service.py` 📋
- [x] `app/ui/core/base_worker.py` 📋
- [x] `app/ui/core/event_bus.py` ✅
- [x] `app/ui/core/task_manager.py` 📋
- [x] `app/ui/dialog/__init__.py` 📋
- [x] `app/ui/dialog/custom_dialog.py` 📋
- [x] `app/ui/dialog/dialog_view_model.py` 📋
- [x] `app/ui/dialog/left_panel_dialog.py` 📋
- [x] `app/ui/dialog/mac_button.py` 📋
- [x] `app/ui/drawing_tools/__init__.py` 📋
- [x] `app/ui/drawing_tools/drawing_setting.py` 📋
- [x] `app/ui/drawing_tools/drawing_tool.py` 📋
- [x] `app/ui/drawing_tools/drawing_tools.py` 📋
- [x] `app/ui/drawing_tools/settings/__init__.py` 📋
- [x] `app/ui/drawing_tools/settings/brush_type_setting.py` 📋
- [x] `app/ui/drawing_tools/settings/color_setting.py` 📋
- [x] `app/ui/drawing_tools/settings/opacity_setting.py` 📋
- [x] `app/ui/drawing_tools/settings/shape_type_setting.py` 📋
- [x] `app/ui/drawing_tools/settings/size_setting.py` 📋
- [x] `app/ui/drawing_tools/tools/__init__.py` 📋
- [x] `app/ui/drawing_tools/tools/adjust_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/brush_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/eraser_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/move_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/pen_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/select_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/shape_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/text_tool.py` 📋
- [x] `app/ui/drawing_tools/tools/zoom_tool.py` 📋
- [x] `app/ui/editor/__init__.py` 📋
- [x] `app/ui/editor/editor_tool_strip.py` 📋
- [x] `app/ui/editor/main_editor.py` 📋
- [x] `app/ui/export_video/__init__.py` 📋
- [x] `app/ui/export_video/export_video_widget.py` 📋
- [x] `app/ui/frame_selector/__init__.py` 📋
- [x] `app/ui/frame_selector/frame_selector.py` 📋
- [x] `app/ui/layers/__init__.py` 📋
- [x] `app/ui/layers/layer_item_widget.py` 📋
- [x] `app/ui/layers/layers_widget.py` 📋
- [x] `app/ui/layout/__init__.py` 📋
- [x] `app/ui/layout/flow_layout.py` 📋
- [x] `app/ui/media_selector/__init__.py` 📋
- [x] `app/ui/media_selector/media_selector.py` 📋
- [x] `app/ui/panels/__init__.py` 📋
- [x] `app/ui/panels/actor/__init__.py` 📋
- [x] `app/ui/panels/actor/actor_card.py` 📋
- [x] `app/ui/panels/actor/actor_edit_dialog.py` 📋
- [x] `app/ui/panels/actor/actor_panel.py` 📋
- [x] `app/ui/panels/actor/actor_panel_view_model.py` 📋
- [x] `app/ui/panels/agent/__init__.py` 📋
- [x] `app/ui/panels/agent/agent_panel.py` 📋
- [x] `app/ui/panels/attachments/__init__.py` 📋
- [x] `app/ui/panels/attachments/attachments_panel.py` 📋
- [x] `app/ui/panels/base_panel.py` 📋
- [x] `app/ui/panels/camera/__init__.py` 📋
- [x] `app/ui/panels/camera/camera_panel.py` 📋
- [x] `app/ui/panels/chat_history/__init__.py` 📋
- [x] `app/ui/panels/chat_history/chat_history_panel.py` 📋
- [x] `app/ui/panels/members/__init__.py` 📋
- [x] `app/ui/panels/members/members_panel.py` 📋
- [x] `app/ui/panels/members/members_view_model.py` 📋
- [x] `app/ui/panels/members/members_widget.py` 📋
- [x] `app/ui/panels/messages/__init__.py` 📋
- [x] `app/ui/panels/messages/messages_panel.py` 📋
- [x] `app/ui/panels/models/__init__.py` 📋
- [x] `app/ui/panels/models/models_panel.py` 📋
- [x] `app/ui/panels/panel_toolbar_view_model.py` 📋
- [x] `app/ui/panels/plan/__init__.py` 📋
- [x] `app/ui/panels/plan/plan_panel.py` 📋
- [x] `app/ui/panels/resources/__init__.py` 📋
- [x] `app/ui/panels/resources/resource_preview.py` 📋
- [x] `app/ui/panels/resources/resources_panel.py` 📋
- [x] `app/ui/panels/screen_play/__init__.py` 📋
- [x] `app/ui/panels/screen_play/screen_play_panel.py` 📋
- [x] `app/ui/panels/screen_play/screen_play_view_model.py` 📋
- [x] `app/ui/panels/server_list/__init__.py` 📋
- [x] `app/ui/panels/server_list/server_list_panel.py` 📋
- [x] `app/ui/panels/settings/__init__.py` 📋
- [x] `app/ui/panels/settings/settings_panel.py` 📋
- [x] `app/ui/panels/skills/skills_panel.py` 📋
- [x] `app/ui/panels/souls/souls_panel.py` 📋
- [x] `app/ui/panels/story_board/__init__.py` 📋
- [x] `app/ui/panels/story_board/story_board_editor_view_model.py` 📋
- [x] `app/ui/panels/timeline_tools/__init__.py` 📋
- [x] `app/ui/panels/timeline_tools/timeline_tools_panel.py` 📋
- [x] `app/ui/panels/video_effects/__init__.py` 📋
- [x] `app/ui/panels/video_effects/video_effects_panel.py` 📋
- [x] `app/ui/panels/workspace_top_left_bar.py` 📋
- [x] `app/ui/panels/workspace_top_right_bar.py` 📋
- [x] `app/ui/play_control/__init__.py` 📋
- [x] `app/ui/play_control/play_control.py` 📋
- [x] `app/ui/preview/__init__.py` 📋
- [x] `app/ui/preview/preview.py` 📋
- [x] `app/ui/project_menu/__init__.py` 📋
- [x] `app/ui/project_menu/project_menu.py` 📋
- [x] `app/ui/prompt/__init__.py` 📋
- [x] `app/ui/prompt/agent_prompt_widget.py` 📋
- [x] `app/ui/prompt/canvas_prompt_widget.py` 📋
- [x] `app/ui/prompt/context_item_widget.py` 📋
- [x] `app/ui/prompt/template_item_widget.py` 📋
- [x] `app/ui/qml/__init__.py` 📋
- [x] `app/ui/qml/shared_qml_engine.py` 📋
- [x] `app/ui/resource_tree/__init__.py` 📋
- [x] `app/ui/resource_tree/resource_tree.py` 📋
- [x] `app/ui/resource_tree/resource_tree2.py` 📋
- [x] `app/ui/server_list/__init__.py` 📋
- [x] `app/ui/server_list/default_config_widget.py` 📋
- [x] `app/ui/server_list/server_list_dialog.py` 📋
- [x] `app/ui/server_list/server_list_view.py` 📋
- [x] `app/ui/server_list/server_list_view_model.py` 📋
- [x] `app/ui/server_list/server_views.py` 📋
- [x] `app/ui/server_status/__init__.py` 📋
- [x] `app/ui/server_status/server_status_button.py` 📋
- [x] `app/ui/server_status/server_status_view_model.py` 📋
- [x] `app/ui/settings/__init__.py` 📋
- [x] `app/ui/settings/field_widget_factory.py` 📋
- [x] `app/ui/settings/plugin_detail_dialog.py` 📋
- [x] `app/ui/settings/plugin_grid_widget.py` 📋
- [x] `app/ui/settings/settings_dialog.py` 📋
- [x] `app/ui/settings/settings_view_model.py` 📋
- [x] `app/ui/settings/settings_widget.py` 📋
- [x] `app/ui/signals.py` 📋
- [x] `app/ui/skeleton_blocks_pulse.py` 📋
- [x] `app/ui/styles.py` 📋
- [x] `app/ui/task_list/__init__.py` 📋
- [x] `app/ui/task_list/enhanced_task_item_widget.py` 📋
- [x] `app/ui/task_list/task_item_preview_widget.py` 📋
- [x] `app/ui/task_list/task_item_widget.py` 📋
- [x] `app/ui/task_list/task_list_widget.py` 📋
- [x] `app/ui/timeline/__init__.py` 📋
- [x] `app/ui/timeline/base_timeline_scroll.py` 📋
- [x] `app/ui/timeline/screenplay_timeline.py` 📋
- [x] `app/ui/timeline/screenplay_timeline_card.py` 📋
- [x] `app/ui/timeline/screenplay_timeline_scroll.py` 📋
- [x] `app/ui/timeline/story_board_scene_card.py` 📋
- [x] `app/ui/timeline/story_board_shot_card.py` 📋
- [x] `app/ui/timeline/story_board_timeline.py` 📋
- [x] `app/ui/timeline/story_board_timeline_scroll.py` 📋
- [x] `app/ui/timeline/subtitle_timeline.py` 📋
- [x] `app/ui/timeline/subtitle_timeline_scroll.py` 📋
- [x] `app/ui/timeline/timeline_container.py` 📋
- [x] `app/ui/timeline/video_timeline.py` 📋
- [x] `app/ui/timeline/video_timeline_card.py` 📋
- [x] `app/ui/timeline/video_timeline_scroll.py` 📋
- [x] `app/ui/timeline/voice_timeline.py` 📋
- [x] `app/ui/timeline/voice_timeline_scroll.py` 📋
- [x] `app/ui/window/__init__.py` 📋
- [x] `app/ui/window/edit/__init__.py` 📋
- [x] `app/ui/window/edit/bottom_side_bar.py` 📋
- [x] `app/ui/window/edit/edit_preflight.py` 📋
- [x] `app/ui/window/edit/edit_widget.py` 📋
- [x] `app/ui/window/edit/edit_window.py` 📋
- [x] `app/ui/window/edit/h_layout.py` 📋
- [x] `app/ui/window/edit/left_bar.py` 📋
- [x] `app/ui/window/edit/left_side_bar.py` 📋
- [x] `app/ui/window/edit/right_bar.py` 📋
- [x] `app/ui/window/edit/right_side_bar.py` 📋
- [x] `app/ui/window/edit/top_side_bar.py` 📋
- [x] `app/ui/window/edit/workspace.py` 📋
- [x] `app/ui/window/edit/workspace_bottom.py` 📋
- [x] `app/ui/window/edit/workspace_top.py` 📋
- [x] `app/ui/window/startup/__init__.py` 📋
- [x] `app/ui/window/startup/panel_switcher.py` 📋
- [x] `app/ui/window/startup/project_info_widget.py` 📋
- [x] `app/ui/window/startup/project_list_widget.py` 📋
- [x] `app/ui/window/startup/project_startup_widget.py` 📋
- [x] `app/ui/window/startup/right_side_bar.py` 📋
- [x] `app/ui/window/startup/startup_window.py` 📋
- [x] `app/ui/window/window_manager.py` 📋
- [x] `app/ui/workers/__init__.py` 📋
- [x] `app/ui/workers/async_data_load_worker.py` 📋
- [x] `app/ui/workers/async_data_loader.py` 📋
- [x] `app/ui/workers/background_worker.py` 📋
- [x] `app/ui/workers/pool_worker.py` 📋
- [x] `app/ui/workers/timeline_export.py` 📋

### server/

- [x] `server/__init__.py` 📋
- [x] `server/api/__init__.py` 📋
- [x] `server/api/chat_types.py` ✅
- [x] `server/api/filmeto_api.py` 📋
- [x] `server/api/resource_processor.py` 📋
- [x] `server/api/types.py` ✅
- [x] `server/api/web_api.py` 📋
- [x] `server/plugins/__init__.py` 📋
- [x] `server/plugins/ability_model_config.py` 📋
- [x] `server/plugins/ability_models_qml_model.py` 📋
- [x] `server/plugins/bailian_server/bailian_ability_catalog.py` 📋
- [x] `server/plugins/bailian_server/config/bailian_config_widget.py` 📋
- [x] `server/plugins/bailian_server/main.py` 📋
- [x] `server/plugins/bailian_server/models_config.py` 📋
- [x] `server/plugins/base_plugin.py` 📋
- [x] `server/plugins/comfy_ui_server/__init__.py` 📋
- [x] `server/plugins/comfy_ui_server/comfy_ui_client.py` 📋
- [x] `server/plugins/comfy_ui_server/comfy_ui_config_qml_model.py` 📋
- [x] `server/plugins/comfy_ui_server/config/__init__.py` 📋
- [x] `server/plugins/comfy_ui_server/main.py` 📋
- [x] `server/plugins/filmeto_server/main.py` 📋
- [x] `server/plugins/local_server/main.py` 📋
- [x] `server/plugins/plugin_config_qml_model.py` 📋
- [x] `server/plugins/plugin_manager.py` ✅
- [x] `server/plugins/plugin_qml_loader.py` 📋
- [x] `server/plugins/plugin_ui_loader.py` 📋
- [x] `server/quickstart.py` 📋
- [x] `server/server.py` 📋
- [x] `server/service/__init__.py` 📋
- [x] `server/service/ability_selection_service.py` ✅
- [x] `server/service/ability_service.py` ✅
- [x] `server/service/chat_service.py` ✅
- [x] `server/service/filmeto_service.py` 📋

### utils/

- [x] `utils/__init__.py` 📋
- [x] `utils/ai_tdd_lint.py` ✅
- [x] `utils/async_file_io.py` 📋
- [x] `utils/async_queue_utils.py` ✅
- [x] `utils/comfy_ui_utils.py` 📋
- [x] `utils/dict_utils.py` ✅
- [x] `utils/download_utils.py` ✅
- [x] `utils/ffmpeg_utils.py` ✅
- [x] `utils/i18n_utils.py` 📋
- [x] `utils/img_utils.py` 📋
- [x] `utils/lazy_load.py` 📋
- [x] `utils/llm_utils.py` ✅
- [x] `utils/logging_utils.py` 📋
- [x] `utils/markdown_parser.py` ✅
- [x] `utils/md_with_meta_utils.py` 📋
- [x] `utils/opencv_utils.py` 📋
- [x] `utils/path_utils.py` ✅
- [x] `utils/progress_utils.py` ✅
- [x] `utils/qt_utils.py` 📋
- [x] `utils/queue_utils.py` ✅
- [x] `utils/signal_utils.py` ✅
- [x] `utils/thread_utils.py` ✅
- [x] `utils/yaml_utils.py` 📋

## Specialized Test Files Mapping

| Test File | Source Files Covered |
|-----------|---------------------|
| `tests/unit/test_agent/test_chat_content_types.py` | `agent/chat/agent_chat_message.py`, `agent/chat/content/content_status.py`, `agent/chat/content/button_content.py`, `agent/chat/content/code_content.py`, `agent/chat/content/crew_member_activity_content.py`, `agent/chat/content/crew_member_read_content.py`, `agent/chat/content/data_content.py`, `agent/chat/content/error_content.py`, `agent/chat/content/file_content.py`, `agent/chat/agent_chat_types.py` |
| `tests/unit/test_agent/test_chat_content_types_part2.py` | `agent/chat/content/structure_content.py`, `agent/chat/content/form_content.py`, `agent/chat/content/link_content.py`, `agent/chat/content/llm_output_content.py`, `agent/chat/content/media_content.py`, `agent/chat/content/metadata_content.py`, `agent/chat/content/plan_content.py`, `agent/chat/content/progress_content.py`, `agent/chat/content/skill_content.py`, `agent/chat/content/text_content.py`, `agent/chat/content/thinking_content.py` |
| `tests/unit/test_agent/test_global_sequence_manager.py` | `agent/chat/history/global_sequence_manager.py` |
| `tests/unit/test_agent/test_content_factory_and_dispatch.py` | `agent/chat/content/__init__.py` |
| `tests/unit/test_agent/test_plan_service_unit.py` | `agent/plan/plan_service.py`, `agent/plan/plan_models.py` |
| `tests/unit/test_agent/test_react_json_utils.py` | `agent/react/json_utils.py` |
| `tests/unit/test_agent/test_react_action_parser.py` | `agent/react/parser.py`, `agent/react/actions.py`, `agent/react/constants.py` |
| `tests/unit/test_agent/test_message_router_service_parsing.py` | `agent/router/message_router_service.py` |
| `tests/unit/test_agent/test_message_target.py` | `agent/router/message_target.py` |
| `tests/unit/test_agent/test_ai_tdd_lint.py` | `utils/ai_tdd_lint.py` |
| `tests/unit/test_agent/test_agent_chat_tab_switch.py` | `app/ui/chat/agent_chat.py` |
| `tests/unit/test_plan_task_widget.py` | `agent/chat/content/__init__.py`, `agent/chat/agent_chat_types.py`, `agent/plan/plan_models.py` |
| `tests/unit/test_utils/test_dict_utils.py` | `utils/dict_utils.py` |
| `tests/unit/test_utils/test_path_markdown_progress_utils.py` | `utils/path_utils.py`, `utils/markdown_parser.py`, `utils/progress_utils.py` |
| `tests/unit/test_utils/test_signal_utils.py` | `utils/signal_utils.py` |
| `tests/unit/test_utils/test_queue_utils.py` | `utils/queue_utils.py` |
| `tests/unit/test_app_data/test_character_manager.py` | `app/data/character.py` |
| `tests/unit/test_app_data/test_drawing_manager.py` | `app/data/drawing.py` |
| `tests/unit/test_app_data/test_layer_manager.py` | `app/data/layer.py` |
| `tests/unit/test_app_data/test_project_manager.py` | `app/data/project.py` |
| `tests/unit/test_app_data/test_prompt_manager.py` | `app/data/prompt.py` |
| `tests/unit/test_app_data/test_resource_manager.py` | `app/data/resource.py` |
| `tests/unit/test_app_data/test_screen_play_extras.py` | `app/data/screen_play/screen_play_formatter.py`, `screen_play_manager.py`, `screen_play_manager_factory.py`, `screen_play_scene.py` |
| `tests/unit/test_app_data/test_screen_play_more.py` | `app/data/screen_play/scene_paths.py`, `screen_play_formatter.py`, `screen_play_manager_factory.py` |
| `tests/unit/test_app_data/test_screenplay_storyboard_layout.py` | `app/data/screen_play/scene_paths.py`, `screen_play_manager.py`, `story_board/story_board_manager.py` |
| `tests/unit/test_app_data/test_settings_manager.py` | `app/data/settings.py` |
| `tests/unit/test_app_data/test_settings_workflow_project.py` | `app/data/settings.py`, `workflow.py`, `project.py` |
| `tests/unit/test_app_data/test_shot_task_executor.py` | `app/data/story_board/shot_task_manager.py`, `task.py`, `shot_task_executor.py` |
| `tests/unit/test_app_data/test_shot_task_manager.py` | `app/data/story_board/shot_task_manager.py` |
| `tests/unit/test_app_data/test_story_board_manager.py` | `app/data/screen_play/screen_play_manager.py`, `story_board/story_board_manager.py`, `story_board_shot.py` |
| `tests/unit/test_app_data/test_task_manager.py` | `app/data/task.py` |
| `tests/unit/test_app_data/test_timeline_manager.py` | `app/data/timeline.py` |
| `tests/unit/test_app_data/test_workflow_manager.py` | `app/data/workflow.py` |
| `tests/unit/test_app_data/test_workspace_manager.py` | `app/data/workspace.py` |
| `tests/unit/test_server/test_ability_selection_service.py` | `server/service/ability_selection_service.py`, `server/api/types.py` |
| `tests/unit/test_server/test_ability_service.py` | `server/service/ability_service.py` |
| `tests/unit/test_server/test_chat_service.py` | `server/service/chat_service.py`, `server/api/chat_types.py` |

## Notes

- Files marked `📋` (AST-only) pass syntax validation but lack behavior tests.
- Files marked `✅` have dedicated test assertions validating their logic.
- Global per-file AST coverage test: `tests/unit/test_meta/test_all_source_files_ast.py`
- Priority candidates for specialized tests (complex logic, 📋 status):
  - `utils/download_utils.py` - Qt-thread download worker
  - `utils/ffmpeg_utils.py` - Video processing operations
  - `utils/thread_utils.py` - Threading utilities
  - `utils/llm_utils.py` - LLM helper functions
  - `agent/chat/history/agent_chat_storage.py` - Chat persistence
  - `agent/core/filmeto_routing.py` - Agent routing logic
  - `agent/skill/skill_service.py` - Skill management
  - `server/plugins/plugin_manager.py` - Plugin system
  - `app/ui/core/event_bus.py` - Event bus system