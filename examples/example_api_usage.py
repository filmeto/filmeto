"""
Example Usage of Filmeto API

Demonstrates how to use the Filmeto API for various tasks.
"""

import asyncio
from pathlib import Path

from server.api import (
    FilmetoApi, FilmetoTask, TaskProgress, TaskResult,
    ToolType, ResourceType, ResourceInput
)


async def example_text2image():
    """Example: Generate an image from text"""
    print("\n=== Example: Text to Image ===")
    
    api = FilmetoApi()
    
    # Create a text-to-image task
    task = FilmetoTask(
        tool_name=ToolType.TEXT2IMAGE,
        plugin_name="text2image_demo",
        parameters={
            "prompt": "A serene mountain landscape at sunset",
            "width": 512,
            "height": 512,
            "steps": 20
        }
    )
    
    print(f"Task ID: {task.task_id}")
    print(f"Tool: {task.tool_name.value}")
    print(f"Plugin: {task.plugin_name}")
    
    # Execute and stream progress
    async for update in api.execute_task_stream(task):
        if isinstance(update, TaskProgress):
            print(f"  Progress: {update.percent:.1f}% - {update.message}")
        elif isinstance(update, TaskResult):
            print(f"\n✅ Result: {update.status}")
            print(f"   Execution time: {update.execution_time:.2f}s")
            print(f"   Output files: {update.output_files}")
            
            if update.status == "success" and update.output_files:
                print(f"   ✓ Image saved to: {update.output_files[0]}")
    
    await api.cleanup()


async def example_image2image():
    """Example: Transform an image"""
    print("\n=== Example: Image to Image ===")
    
    api = FilmetoApi()
    
    # First, create an image to work with
    print("Creating source image...")
    source_task = FilmetoTask(
        tool_name=ToolType.TEXT2IMAGE,
        plugin_name="text2image_demo",
        parameters={
            "prompt": "Source image for transformation",
            "width": 256,
            "height": 256,
            "steps": 5
        }
    )
    
    source_image = None
    async for update in api.execute_task_stream(source_task):
        if isinstance(update, TaskResult) and update.status == "success":
            source_image = update.output_files[0]
            print(f"✓ Source image: {source_image}")
    
    if source_image and Path(source_image).exists():
        # Now transform it
        print("\nTransforming image...")
        task = FilmetoTask(
            tool_name=ToolType.IMAGE2IMAGE,
            plugin_name="text2image_demo",  # Demo plugin supports this too
            parameters={
                "prompt": "Enhanced and stylized version",
                "strength": 0.8
            },
            resources=[
                ResourceInput(
                    type=ResourceType.LOCAL_PATH,
                    data=source_image,
                    mime_type="image/png"
                )
            ]
        )
        
        async for update in api.execute_task_stream(task):
            if isinstance(update, TaskProgress):
                print(f"  Progress: {update.percent:.1f}%")
            elif isinstance(update, TaskResult):
                print(f"✅ Result: {update.status}")
                if update.output_files:
                    print(f"   Output: {update.output_files[0]}")
    
    await api.cleanup()


async def example_with_url_resource():
    """Example: Use a remote URL as resource"""
    print("\n=== Example: Using Remote URL Resource ===")
    
    api = FilmetoApi()
    
    task = FilmetoTask(
        tool_name=ToolType.IMAGE2VIDEO,
        plugin_name="image2video_demo",  # Would need this plugin
        parameters={
            "duration": 5,
            "fps": 30
        },
        resources=[
            ResourceInput(
                type=ResourceType.REMOTE_URL,
                data="https://example.com/image.png",
                mime_type="image/png"
            )
        ]
    )
    
    # Note: This will fail without the actual plugin
    # Just demonstrating the API usage
    print(f"Task created with URL resource: {task.resources[0].data}")
    
    await api.cleanup()


async def example_with_base64():
    """Example: Use base64 encoded data"""
    print("\n=== Example: Using Base64 Encoded Data ===")
    
    import base64
    
    api = FilmetoApi()
    
    # Create some dummy image data
    dummy_data = b"fake image data for demonstration"
    encoded = base64.b64encode(dummy_data).decode()
    
    task = FilmetoTask(
        tool_name=ToolType.IMAGE2IMAGE,
        plugin_name="text2image_demo",
        parameters={
            "prompt": "Process this image"
        },
        resources=[
            ResourceInput(
                type=ResourceType.BASE64,
                data=f"data:image/png;base64,{encoded}",
                mime_type="image/png"
            )
        ]
    )
    
    print(f"Task created with base64 resource (length: {len(encoded)})")
    
    await api.cleanup()


async def example_list_capabilities():
    """Example: List available tools and plugins"""
    print("\n=== Example: Listing Capabilities ===")
    
    api = FilmetoApi()
    
    # List all tools
    print("\nAvailable Tools:")
    tools = api.list_tools()
    for tool in tools:
        print(f"  • {tool['name']}: {tool['display_name']}")
    
    # List all plugins
    print("\nAvailable Plugins:")
    plugins = api.list_plugins()
    for plugin in plugins:
        print(f"  • {plugin['name']} v{plugin['version']}")
        primary = plugin.get("ability") or (
            ", ".join(a["name"] for a in plugin.get("abilities", [])) or "—"
        )
        print(f"    Abilities: {primary}")
        print(f"    Engine: {plugin['engine']}")
        print(f"    Description: {plugin['description']}")
    
    # Get plugins by tool type
    print("\nPlugins for 'text2image':")
    text2image_plugins = api.get_plugins_by_tool("text2image")
    for plugin in text2image_plugins:
        print(f"  • {plugin['name']}")
    
    await api.cleanup()


async def example_error_handling():
    """Example: Error handling"""
    print("\n=== Example: Error Handling ===")
    
    api = FilmetoApi()
    
    # Try with invalid plugin
    print("Attempting task with non-existent plugin...")
    task = FilmetoTask(
        tool_name=ToolType.TEXT2IMAGE,
        plugin_name="nonexistent_plugin",
        parameters={"prompt": "test"}
    )
    
    try:
        async for update in api.execute_task_stream(task):
            if isinstance(update, TaskResult):
                print(f"Result status: {update.status}")
                if update.error_message:
                    print(f"Error: {update.error_message}")
    except Exception as e:
        print(f"Exception caught: {type(e).__name__}: {e}")
    
    # Try with missing required parameter
    print("\nAttempting task with missing parameter...")
    task2 = FilmetoTask(
        tool_name=ToolType.TEXT2IMAGE,
        plugin_name="text2image_demo",
        parameters={}  # Missing prompt
    )
    
    is_valid, error = api.validate_task(task2)
    if not is_valid:
        print(f"Validation failed: {error}")
    
    await api.cleanup()


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Filmeto API Usage Examples")
    print("=" * 60)
    
    # Run examples
    await example_text2image()
    await example_list_capabilities()
    await example_error_handling()
    
    # Optional: uncomment to run other examples
    # await example_image2image()
    # await example_with_url_resource()
    # await example_with_base64()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
