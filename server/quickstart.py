#!/usr/bin/env python3
"""
Filmeto API Quick Start

Quick demonstration of the Filmeto API system.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.api import FilmetoApi, FilmetoTask, TaskProgress, TaskResult, ToolType


async def main():
    print("=" * 70)
    print(" Filmeto API - Quick Start Demonstration")
    print("=" * 70)
    print()
    
    # Initialize API
    print("🚀 Initializing Filmeto API...")
    api = FilmetoApi()
    
    try:
        # 1. List available tools
        print("\n📋 Available Tools:")
        tools = api.list_tools()
        for tool in tools:
            print(f"   • {tool['display_name']}")
        
        # 2. List available plugins
        print("\n🔌 Available Plugins:")
        plugins = api.list_plugins()
        if plugins:
            for plugin in plugins:
                print(f"   • {plugin['name']} v{plugin['version']} - {plugin['description']}")
        else:
            print("   ⚠️  No plugins found. Make sure the demo plugin is in server/plugins/")
        
        # 3. Create and execute a demo task
        print("\n🎨 Generating Demo Image...")
        print("   Plugin: text2image_demo")
        print("   Prompt: 'Quick Start Demo - Filmeto API'")
        print()
        
        task = FilmetoTask(
            tool_name=ToolType.TEXT2IMAGE,
            plugin_name="text2image_demo",
            parameters={
                "prompt": "Quick Start Demo - Filmeto API",
                "width": 512,
                "height": 512,
                "steps": 15
            }
        )
        
        # Validate task
        is_valid, error = api.validate_task(task)
        if not is_valid:
            print(f"❌ Task validation failed: {error}")
            return
        
        # Execute task
        result = None
        last_percent = 0
        
        async for update in api.execute_task_stream(task):
            if isinstance(update, TaskProgress):
                # Only print progress at 10% intervals
                if int(update.percent / 10) > int(last_percent / 10):
                    print(f"   ⏳ Progress: {update.percent:.0f}% - {update.message}")
                    last_percent = update.percent
            
            elif isinstance(update, TaskResult):
                result = update
                print()
                print(f"   ✅ Status: {result.status}")
                print(f"   ⏱️  Execution Time: {result.execution_time:.2f}s")
                
                if result.status == "success" and result.output_files:
                    print(f"   📁 Output File: {result.output_files[0]}")
                    
                    # Check file size
                    output_path = Path(result.output_files[0])
                    if output_path.exists():
                        file_size = output_path.stat().st_size
                        print(f"   💾 File Size: {file_size / 1024:.1f} KB")
                elif result.error_message:
                    print(f"   ❌ Error: {result.error_message}")
        
        # Summary
        print()
        print("=" * 70)
        if result and result.status == "success":
            print(" ✅ Quick Start Completed Successfully!")
            print()
            print(" Next Steps:")
            print("   1. Check out the examples in examples/")
            print("   2. Read the documentation in server/README.md")
            print("   3. Create your own plugin in server/plugins/")
            print("   4. Start the web server: python server/api/web_api.py")
        else:
            print(" ⚠️  Quick Start Completed with Errors")
            print()
            print(" Troubleshooting:")
            print("   1. Make sure all dependencies are installed: pip install -r requirements.txt")
            print("   2. Check that the demo plugin exists: server/plugins/text2image_demo/")
            print("   3. Review the error messages above")
        print("=" * 70)
    
    except KeyboardInterrupt:
        print("\n\n⏸️  Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error in quickstart: {e}", exc_info=True)
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await api.cleanup()
        print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
