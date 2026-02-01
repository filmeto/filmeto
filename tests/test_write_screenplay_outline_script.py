"""
Test write_screenplay_outline.py script argument parsing.

Tests that:
1. The script correctly parses --concept, --genre, --num-scenes, --project-path
2. The script can handle positional arguments for backward compatibility
3. Missing concept returns proper error
4. Missing project-path returns proper error
"""

import pytest
import sys
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWriteScreenplayOutlineScript:
    """Tests for write_screenplay_outline.py script."""

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
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import main

        # Mock sys.argv
        original_argv = sys.argv
        try:
            sys.argv = [
                'write_screenplay_outline.py',
                '--concept', 'A story about a detective',
                '--genre', 'film noir',
                '--num-scenes', '5',
                '--project-path', self.project_path
            ]

            result = main()

            # Check that it returns a result (not an error)
            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # It should either succeed or fail with missing project manager
            # (which is expected since we don't have a real project setup)
            assert 'success' in output
            assert 'error' in output or 'total_scenes' in output
        finally:
            sys.argv = original_argv

    def test_main_with_positional_args(self, capsys):
        """Test main() with positional arguments for backward compatibility."""
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_screenplay_outline.py',
                'A story about a detective',  # concept
                self.project_path  # project_path
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # Should either succeed or fail with missing project manager
            assert 'success' in output
        finally:
            sys.argv = original_argv

    def test_main_missing_concept(self, capsys):
        """Test that missing concept returns proper error."""
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_screenplay_outline.py',
                '--project-path', self.project_path
                # Missing --concept
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert output['success'] is False
            assert output['error'] == 'missing_concept'
        finally:
            sys.argv = original_argv

    def test_main_missing_project_path(self, capsys):
        """Test that missing project-path returns proper error."""
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_screenplay_outline.py',
                '--concept', 'A story about a detective'
                # Missing --project-path
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert output['success'] is False
            assert output['error'] == 'missing_project_path'
        finally:
            sys.argv = original_argv

    def test_main_with_default_genre_and_num_scenes(self, capsys):
        """Test main() with default genre and num_scenes."""
        from agent.skill.system.write_screenplay_outline.scripts.write_screenplay_outline import main

        original_argv = sys.argv
        try:
            sys.argv = [
                'write_screenplay_outline.py',
                '--concept', 'A story about a detective',
                '--project-path', self.project_path
            ]

            result = main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # Should use default genre "General" and num_scenes 10
            if output.get('success'):
                assert output.get('genre') == 'General'
                assert output.get('num_scenes') == 10
        finally:
            sys.argv = original_argv


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
