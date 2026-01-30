"""
Workflow Manager

Manages ComfyUI workflow files and configurations in workspace.
Handles workflow storage, retrieval, and metadata management.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class WorkflowNodeMapping:
    """Node mapping configuration for a workflow"""
    prompt_node: str
    output_node: str
    input_node: Optional[str] = None
    seed_node: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'prompt_node': self.prompt_node,
            'output_node': self.output_node
        }
        if self.input_node:
            result['input_node'] = self.input_node
        if self.seed_node:
            result['seed_node'] = self.seed_node
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowNodeMapping':
        """Create from dictionary"""
        return cls(
            prompt_node=data['prompt_node'],
            output_node=data['output_node'],
            input_node=data.get('input_node'),
            seed_node=data.get('seed_node')
        )


@dataclass
class WorkflowMetadata:
    """Metadata for a workflow"""
    name: str
    type: str
    file: str
    node_mapping: WorkflowNodeMapping
    description: Optional[str] = None
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'name': self.name,
            'type': self.type,
            'file': self.file,
            'node_mapping': self.node_mapping.to_dict(),
            'version': self.version
        }
        if self.description:
            result['description'] = self.description
        if self.author:
            result['author'] = self.author
        if self.tags:
            result['tags'] = self.tags
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowMetadata':
        """Create from dictionary"""
        node_mapping = WorkflowNodeMapping.from_dict(data['node_mapping'])
        return cls(
            name=data['name'],
            type=data['type'],
            file=data['file'],
            node_mapping=node_mapping,
            description=data.get('description'),
            version=data.get('version', '1.0.0'),
            author=data.get('author'),
            tags=data.get('tags', [])
        )


class WorkflowManager:
    """Manager for ComfyUI workflows"""
    
    def __init__(self, workspace_path: str, server_name: str = "comfyui"):
        """
        Initialize workflow manager
        
        Args:
            workspace_path: Path to workspace directory
            server_name: Server name (default: comfyui)
        """
        self.workspace_path = Path(workspace_path)
        self.server_name = server_name
        self.workflows_dir = self.workspace_path / "servers" / server_name / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
    
    def list_workflows(self) -> List[WorkflowMetadata]:
        """
        List all workflows
        
        Returns:
            List of workflow metadata
        """
        workflows = []
        
        # Find all JSON files that are not workflow files
        for metadata_file in self.workflows_dir.glob("*.json"):
            # Skip workflow files (those ending with _workflow.json)
            if metadata_file.name.endswith('_workflow.json'):
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if it's a metadata file (has required fields)
                    if 'name' in data and 'type' in data and 'node_mapping' in data:
                        metadata = WorkflowMetadata.from_dict(data)
                        workflows.append(metadata)
            except Exception as e:
                logger.error(f"Failed to load workflow metadata {metadata_file}: {e}")
        
        return workflows
    
    def get_workflow(self, workflow_name: str) -> Optional[WorkflowMetadata]:
        """
        Get workflow by name
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow metadata or None if not found
        """
        # First try exact name match from list
        workflows = self.list_workflows()
        for workflow in workflows:
            if workflow.name == workflow_name:
                return workflow
        
        # Fallback to file-based lookup
        return self.load_workflow_metadata(workflow_name)
    
    def get_workflow_by_type(self, workflow_type: str) -> Optional[WorkflowMetadata]:
        """
        Get first workflow matching the given type
        
        Args:
            workflow_type: Type of workflow (e.g., 'text2image', 'image_edit')
            
        Returns:
            Workflow metadata or None if not found
        """
        workflows = self.list_workflows()
        for workflow in workflows:
            if workflow.type == workflow_type:
                return workflow
        return None
    
    def save_workflow(
        self,
        name: str,
        workflow_type: str,
        workflow_file_path: str,
        node_mapping: WorkflowNodeMapping,
        description: Optional[str] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Save a workflow
        
        Args:
            name: Workflow name
            workflow_type: Workflow type
            workflow_file_path: Path to workflow JSON file
            node_mapping: Node mapping configuration
            description: Optional description
            author: Optional author name
            tags: Optional tags
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate file names
            safe_name = name.replace(' ', '_').lower()
            workflow_filename = f"{safe_name}_workflow.json"
            metadata_filename = f"{safe_name}_metadata.json"
            
            # Copy workflow file
            import shutil
            source_path = Path(workflow_file_path)
            target_path = self.workflows_dir / workflow_filename
            
            if source_path != target_path:
                shutil.copy2(source_path, target_path)
            
            # Create metadata
            metadata = WorkflowMetadata(
                name=name,
                type=workflow_type,
                file=workflow_filename,
                node_mapping=node_mapping,
                description=description,
                author=author,
                tags=tags or []
            )
            
            # Save metadata
            metadata_path = self.workflows_dir / metadata_filename
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save workflow: {e}")
            return False
    
    def delete_workflow(self, workflow_name: str) -> bool:
        """
        Delete a workflow
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            True if successful, False otherwise
        """
        try:
            safe_name = workflow_name.replace(' ', '_').lower()
            
            # Delete metadata file
            metadata_file = self.workflows_dir / f"{safe_name}_metadata.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Delete workflow file
            workflow_file = self.workflows_dir / f"{safe_name}_workflow.json"
            if workflow_file.exists():
                workflow_file.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete workflow: {e}")
            return False
    
    def load_workflow_metadata(self, workflow_name: str) -> Optional[WorkflowMetadata]:
        """
        Load workflow metadata
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow metadata or None if not found
        """
        try:
            safe_name = workflow_name.replace(' ', '_').lower()
            
            # Try both naming patterns
            metadata_files = [
                self.workflows_dir / f"{safe_name}.json",
                self.workflows_dir / f"{safe_name}_metadata.json"
            ]
            
            for metadata_file in metadata_files:
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Verify it's a metadata file
                        if 'name' in data and 'type' in data and 'node_mapping' in data:
                            return WorkflowMetadata.from_dict(data)
            
            return None
                
        except Exception as e:
            logger.error(f"Failed to load workflow metadata: {e}")
            return None
    
    def load_workflow_content(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """
        Load workflow JSON content
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow JSON data or None if not found
        """
        try:
            # Use get_workflow for better name matching
            metadata = self.get_workflow(workflow_name)
            if not metadata:
                logger.warning(f"Metadata not found for workflow: {workflow_name}")
                return None
            
            workflow_file = self.workflows_dir / metadata.file
            if not workflow_file.exists():
                logger.warning(f"Workflow file not found: {workflow_file}")
                return None
            
            with open(workflow_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load workflow content: {e}", exc_info=True)
            return None
    
    def prepare_workflow(
        self,
        workflow_name: str,
        prompt: str,
        input_image: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare workflow with parameters
        
        Args:
            workflow_name: Name of the workflow
            prompt: Text prompt
            input_image: Optional input image filename (already uploaded to ComfyUI)
            seed: Optional random seed
            
        Returns:
            Prepared workflow JSON or None if failed
        """
        try:
            # Load workflow content
            workflow = self.load_workflow_content(workflow_name)
            if not workflow:
                return None
            
            # Load metadata using get_workflow for better matching
            metadata = self.get_workflow(workflow_name)
            if not metadata:
                return None
            
            # Convert to string for replacement
            workflow_str = json.dumps(workflow)
            
            # Replace prompt
            node_mapping = metadata.node_mapping
            workflow_str = workflow_str.replace('$prompt', prompt)
            
            # Replace input image if provided
            if input_image and node_mapping.input_node:
                workflow_str = workflow_str.replace('$inputImage', input_image)
            
            # Replace seed if provided
            if seed is not None and node_mapping.seed_node:
                workflow_str = workflow_str.replace('$seed', str(seed))
            
            # Parse back to JSON
            return json.loads(workflow_str)
            
        except Exception as e:
            logger.error(f"Failed to prepare workflow: {e}")
            return None
    
    def get_workflow_path(self, workflow_name: str) -> Optional[Path]:
        """
        Get path to workflow file
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Path to workflow file or None if not found
        """
        metadata = self.load_workflow_metadata(workflow_name)
        if not metadata:
            return None
        
        workflow_file = self.workflows_dir / metadata.file
        if not workflow_file.exists():
            return None
        
        return workflow_file
    
    def import_workflow(self, source_path: str, name: Optional[str] = None) -> bool:
        """
        Import a workflow from external source
        
        Args:
            source_path: Path to workflow JSON file
            name: Optional name (defaults to filename)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source = Path(source_path)
            if not source.exists():
                return False
            
            # Use filename as name if not provided
            if not name:
                name = source.stem
            
            safe_name = name.replace(' ', '_').lower()
            target_file = self.workflows_dir / f"{safe_name}_workflow.json"
            
            # Copy file
            import shutil
            shutil.copy2(source, target_file)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to import workflow: {e}")
            return False
    
    def export_workflow(self, workflow_name: str, target_path: str) -> bool:
        """
        Export a workflow to external location
        
        Args:
            workflow_name: Name of the workflow
            target_path: Target path for export
            
        Returns:
            True if successful, False otherwise
        """
        try:
            workflow_path = self.get_workflow_path(workflow_name)
            if not workflow_path:
                return False
            
            # Copy file
            import shutil
            shutil.copy2(workflow_path, target_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export workflow: {e}")
            return False

