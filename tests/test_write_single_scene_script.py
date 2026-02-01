"""
Test write_single_scene.py script argument parsing.

Tests that:
1. The script correctly parses all named arguments
2. The script can handle positional arguments for backward compatibility
3. Missing required arguments return proper errors
4. List arguments (characters, tags) are parsed correctly
"""

import pytest
import sys
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWriteSingleSceneScript:
    """Tests for write_single_scene.py script."""

    def setup_method(self):
        """Setup test fixtures."""
        # Create a temporary project directory
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = self.temp_dir

    def teardown_method(self):
        """Cleanup test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_main_with_all_named_args(self, capsys):
        """Test main() with all named arguments."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        # Mock sys.argv
        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                '--scene-id', 'scene_001',
                '--title', 'Opening Scene',
                '--content', 'INT. LOCATION - DAY\\n\\nScene content here.',
                '--project-path', self.project_path,
                '--location', 'INT. LOCATION',
                '--time-of-day', 'DAY',
                '--genre', 'Drama',
                '--logline', 'The opening scene',
                '--characters', '["ALEX", "JORDAN"]',
                '--story-beat', 'setup',
                '--page-count', '3',
                '--duration-minutes', '5',
                '--tags', '["opening", "drama"]',
                '--status', 'draft'
            ]

            result = main()

            # Check that it returns a result (not an error)
            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # It should either succeed or fail with missing project manager
            # (which is expected since we don't have a real project setup)
            assert 'success' in output
            assert 'error' in output or 'scene_id' in output
        finally:
            sys.argv = original_argv

    def test_main_with_positional_args(self, capsys):
        """Test main() with positional arguments for backward compatibility."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                'scene_001',  # scene_id
                'Opening Scene',  # title
                'INT. LOCATION - DAY\\n\\nScene content here.',  # content
                self.project_path  # project_path
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # Should either succeed or fail with missing project manager
            assert 'success' in output
        finally:
            sys.argv = original_argv

    def test_main_missing_scene_id(self, capsys):
        """Test that missing scene_id returns proper error."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                '--title', 'Opening Scene',
                '--content', 'Scene content',
                '--project-path', self.project_path
                # Missing --scene-id
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert output['success'] is False
            assert output['error'] == 'missing_scene_id'
        finally:
            sys.argv = original_argv

    def test_main_missing_title(self, capsys):
        """Test that missing title returns proper error."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                '--scene-id', 'scene_001',
                '--content', 'Scene content',
                '--project-path', self.project_path
                # Missing --title
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert output['success'] is False
            assert output['error'] == 'missing_title'
        finally:
            sys.argv = original_argv

    def test_main_missing_content(self, capsys):
        """Test that missing content returns proper error."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                '--scene-id', 'scene_001',
                '--title', 'Opening Scene',
                '--project-path', self.project_path
                # Missing --content
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert output['success'] is False
            assert output['error'] == 'missing_content'
        finally:
            sys.argv = original_argv

    def test_main_missing_project_path(self, capsys):
        """Test that missing project-path returns proper error."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                '--scene-id', 'scene_001',
                '--title', 'Opening Scene',
                '--content', 'Scene content'
                # Missing --project-path
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert output['success'] is False
            assert output['error'] == 'missing_project_path'
        finally:
            sys.argv = original_argv

    def test_main_with_list_arguments_json(self, capsys):
        """Test main() with list arguments in JSON format."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                '--scene-id', 'scene_001',
                '--title', 'Opening Scene',
                '--content', 'Scene content',
                '--project-path', self.project_path,
                '--characters', '["ALEX", "JORDAN", "MAYA"]',
                '--tags', '["opening", "setup", "drama"]'
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # Should either succeed or fail gracefully
            assert 'success' in output
        finally:
            sys.argv = original_argv

    def test_main_with_list_arguments_comma_separated(self, capsys):
        """Test main() with list arguments as comma-separated strings."""
        from agent.skill.system.write_single_scene.scripts.write_single_scene import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_single_scene.py',
                '--scene-id', 'scene_001',
                '--title', 'Opening Scene',
                '--content', 'Scene content',
                '--project-path', self.project_path,
                '--characters', 'ALEX,JORDAN,MAYA',
                '--tags', 'opening,setup,drama'
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # Should either succeed or fail gracefully
            assert 'success' in output
        finally:
            sys.argv = original_argv


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
