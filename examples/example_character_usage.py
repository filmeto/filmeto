"""
Example: Character Management Usage

This example demonstrates how to use the Character Management System.
"""

import os
import sys
import tempfile
import shutil

# Add app to path
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(current_dir)
app_path = os.path.join(workspace_root, 'app')
if app_path not in sys.path:
    sys.path.insert(0, app_path)

from app.data.character import CharacterManager


def main():
    """Main example function"""
    # Create a temporary project directory
    project_dir = tempfile.mkdtemp()
    print(f"📁 Project directory: {project_dir}")
    
    try:
        # Initialize CharacterManager
        manager = CharacterManager(project_dir)
        print("✅ CharacterManager initialized")
        
        # Create some characters
        print("\n📝 Creating characters...")
        alice = manager.create_character(
            name="Alice",
            description="A brave adventurer",
            story="Alice is a skilled warrior who loves exploring ancient ruins."
        )
        print(f"  ✅ Created: {alice.name}")
        
        bob = manager.create_character(
            name="Bob",
            description="A wise wizard",
            story="Bob is a master of arcane magic and ancient knowledge."
        )
        print(f"  ✅ Created: {bob.name}")
        
        charlie = manager.create_character(
            name="Charlie",
            description="A cunning rogue",
            story="Charlie is known for quick thinking and stealth."
        )
        print(f"  ✅ Created: {charlie.name}")
        
        # List all characters
        print("\n📋 Listing all characters...")
        characters = manager.list_characters()
        for char in characters:
            print(f"  - {char.name}: {char.description}")
        
        # Update actor
        print("\n✏️  Updating actor...")
        manager.update_character(
            "Alice",
            description="A brave adventurer and leader",
            relationships={
                "Bob": "Trusted ally",
                "Charlie": "Friend"
            }
        )
        alice = manager.get_character("Alice")
        print(f"  ✅ Updated: {alice.name}")
        print(f"     Description: {alice.description}")
        print(f"     Relationships: {alice.relationships}")
        
        # Add resource files (simulated)
        print("\n🖼️  Adding resources...")
        # Create a dummy image file
        dummy_image = os.path.join(project_dir, "dummy_image.png")
        with open(dummy_image, "wb") as f:
            f.write(b"fake image data")
        
        resource_path = manager.add_resource("Alice", "main_view", dummy_image)
        if resource_path:
            print(f"  ✅ Added main_view resource: {resource_path}")
        
        # Search characters
        print("\n🔍 Searching characters...")
        results = manager.search_characters("brave")
        print(f"  Found {len(results)} actor(s) matching 'brave':")
        for char in results:
            print(f"    - {char.name}")
        
        # Rename actor
        print("\n🔄 Renaming actor...")
        success = manager.rename_character("Bob", "Robert")
        if success:
            print("  ✅ Renamed 'Bob' to 'Robert'")
            robert = manager.get_character("Robert")
            print(f"     New name: {robert.name}")
        
        # Delete actor
        print("\n🗑️  Deleting actor...")
        success = manager.delete_character("Charlie", remove_files=True)
        if success:
            print("  ✅ Deleted 'Charlie'")
        
        # Final list
        print("\n📋 Final actor list:")
        characters = manager.list_characters()
        for char in characters:
            print(f"  - {char.name}: {char.description}")
            if char.resources:
                print(f"    Resources: {list(char.resources.keys())}")
        
        print("\n✅ Example completed successfully!")
        print(f"\n📁 Check the project directory for actor files: {project_dir}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error in character usage example: {e}", exc_info=True)
    finally:
        # Cleanup (comment out to inspect files)
        # shutil.rmtree(project_dir, ignore_errors=True)
        pass


if __name__ == "__main__":
    main()

