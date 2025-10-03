"""
Artifact registry implementation for MCP Core.
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .artifact_schema import Artifact, ArtifactMetadata, ArtifactType, ArtifactRegistration, ArtifactReference


class ArtifactRegistry:
    """Central registry for managing artifacts and their metadata."""
    
    def __init__(self):
        self.logger = logging.getLogger("artifact_registry")
        self._artifacts: Dict[str, Artifact] = {}  # artifact_id -> Artifact
        self._artifacts_by_job: Dict[str, List[str]] = {}  # job_id -> [artifact_ids]
        self._artifacts_by_service: Dict[str, List[str]] = {}  # service_id -> [artifact_ids]
        self._artifacts_by_type: Dict[ArtifactType, List[str]] = {}  # type -> [artifact_ids]
    
    async def register_artifact(self, registration: ArtifactRegistration) -> str:
        """
        Register a new artifact.
        
        Args:
            registration: Artifact registration data
            
        Returns:
            Artifact ID
            
        Raises:
            ValueError: If artifact ID already exists
        """
        # Create artifact metadata
        metadata = ArtifactMetadata(
            name=registration.name,
            type=registration.type,
            description=registration.description,
            created_by=registration.job_id,
            size_bytes=registration.size_bytes,
            checksum=registration.checksum,
            tags=registration.tags,
            metadata=registration.metadata
        )
        
        # Create artifact
        artifact = Artifact(
            metadata=metadata,
            storage_location=registration.storage_location,
            service_id=registration.service_id,
            job_id=registration.job_id,
            dependencies=registration.dependencies
        )
        
        # Check for duplicate ID (shouldn't happen with UUID, but just in case)
        if artifact.metadata.id in self._artifacts:
            raise ValueError(f"Artifact with ID {artifact.metadata.id} already exists")
        
        # Store artifact
        self._artifacts[artifact.metadata.id] = artifact
        
        # Update indexes
        self._update_indexes(artifact)
        
        # Update dependency references
        await self._update_dependency_references(artifact)
        
        self.logger.info(f"Registered artifact {artifact.metadata.id} ({artifact.metadata.name})")
        return artifact.metadata.id
    
    async def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """
        Get an artifact by ID.
        
        Args:
            artifact_id: The artifact ID
            
        Returns:
            Artifact or None if not found
        """
        return self._artifacts.get(artifact_id)
    
    async def list_artifacts(
        self,
        artifact_type: Optional[ArtifactType] = None,
        job_id: Optional[str] = None,
        service_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Artifact]:
        """
        List artifacts with optional filtering.
        
        Args:
            artifact_type: Filter by artifact type
            job_id: Filter by job ID
            service_id: Filter by service ID
            limit: Maximum number of artifacts to return
            
        Returns:
            List of artifacts
        """
        artifacts = []
        
        if artifact_type:
            artifact_ids = self._artifacts_by_type.get(artifact_type, [])
        elif job_id:
            artifact_ids = self._artifacts_by_job.get(job_id, [])
        elif service_id:
            artifact_ids = self._artifacts_by_service.get(service_id, [])
        else:
            artifact_ids = list(self._artifacts.keys())
        
        # Get artifacts
        for artifact_id in artifact_ids:
            if artifact_id in self._artifacts:
                artifacts.append(self._artifacts[artifact_id])
        
        # Sort by creation time (newest first)
        artifacts.sort(key=lambda x: x.metadata.created_at, reverse=True)
        
        # Apply limit
        if limit:
            artifacts = artifacts[:limit]
        
        return artifacts
    
    async def get_artifacts_by_job(self, job_id: str) -> List[Artifact]:
        """
        Get all artifacts produced by a specific job.
        
        Args:
            job_id: The job ID
            
        Returns:
            List of artifacts
        """
        artifact_ids = self._artifacts_by_job.get(job_id, [])
        return [self._artifacts[aid] for aid in artifact_ids if aid in self._artifacts]
    
    async def get_artifact_dependencies(self, artifact_id: str) -> List[Artifact]:
        """
        Get all artifacts that the given artifact depends on.
        
        Args:
            artifact_id: The artifact ID
            
        Returns:
            List of dependency artifacts
        """
        artifact = await self.get_artifact(artifact_id)
        if not artifact:
            return []
        
        dependencies = []
        for dep_ref in artifact.dependencies:
            dep_artifact = await self.get_artifact(dep_ref.artifact_id)
            if dep_artifact:
                dependencies.append(dep_artifact)
        
        return dependencies
    
    async def get_artifact_references(self, artifact_id: str) -> List[Artifact]:
        """
        Get all artifacts that reference the given artifact.
        
        Args:
            artifact_id: The artifact ID
            
        Returns:
            List of referencing artifacts
        """
        artifact = await self.get_artifact(artifact_id)
        if not artifact:
            return []
        
        references = []
        for ref in artifact.referenced_by:
            ref_artifact = await self.get_artifact(ref.artifact_id)
            if ref_artifact:
                references.append(ref_artifact)
        
        return references
    
    async def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete an artifact from the registry.
        
        Args:
            artifact_id: The artifact ID
            
        Returns:
            True if deleted, False if not found
        """
        if artifact_id not in self._artifacts:
            return False
        
        artifact = self._artifacts[artifact_id]
        
        # Remove from indexes
        self._remove_from_indexes(artifact)
        
        # Remove dependency references
        await self._remove_dependency_references(artifact)
        
        # Delete artifact
        del self._artifacts[artifact_id]
        
        self.logger.info(f"Deleted artifact {artifact_id}")
        return True
    
    def _update_indexes(self, artifact: Artifact):
        """Update internal indexes for the artifact."""
        artifact_id = artifact.metadata.id
        
        # Update job index
        if artifact.job_id:
            if artifact.job_id not in self._artifacts_by_job:
                self._artifacts_by_job[artifact.job_id] = []
            if artifact_id not in self._artifacts_by_job[artifact.job_id]:
                self._artifacts_by_job[artifact.job_id].append(artifact_id)
        
        # Update service index
        if artifact.service_id:
            if artifact.service_id not in self._artifacts_by_service:
                self._artifacts_by_service[artifact.service_id] = []
            if artifact_id not in self._artifacts_by_service[artifact.service_id]:
                self._artifacts_by_service[artifact.service_id].append(artifact_id)
        
        # Update type index
        artifact_type = artifact.metadata.type
        if artifact_type not in self._artifacts_by_type:
            self._artifacts_by_type[artifact_type] = []
        if artifact_id not in self._artifacts_by_type[artifact_type]:
            self._artifacts_by_type[artifact_type].append(artifact_id)
    
    def _remove_from_indexes(self, artifact: Artifact):
        """Remove artifact from internal indexes."""
        artifact_id = artifact.metadata.id
        
        # Remove from job index
        if artifact.job_id and artifact.job_id in self._artifacts_by_job:
            if artifact_id in self._artifacts_by_job[artifact.job_id]:
                self._artifacts_by_job[artifact.job_id].remove(artifact_id)
        
        # Remove from service index
        if artifact.service_id and artifact.service_id in self._artifacts_by_service:
            if artifact_id in self._artifacts_by_service[artifact.service_id]:
                self._artifacts_by_service[artifact.service_id].remove(artifact_id)
        
        # Remove from type index
        artifact_type = artifact.metadata.type
        if artifact_type in self._artifacts_by_type:
            if artifact_id in self._artifacts_by_type[artifact_type]:
                self._artifacts_by_type[artifact_type].remove(artifact_id)
    
    async def _update_dependency_references(self, artifact: Artifact):
        """Update referenced_by lists for dependency artifacts."""
        for dep_ref in artifact.dependencies:
            dep_artifact = await self.get_artifact(dep_ref.artifact_id)
            if dep_artifact:
                # Add reference to dependency artifact
                ref = ArtifactReference(
                    artifact_id=artifact.metadata.id,
                    artifact_type=artifact.metadata.type,
                    reference_type="referenced_by",
                    metadata={"reference_type": dep_ref.reference_type}
                )
                dep_artifact.referenced_by.append(ref)
    
    async def _remove_dependency_references(self, artifact: Artifact):
        """Remove referenced_by entries for dependency artifacts."""
        for dep_ref in artifact.dependencies:
            dep_artifact = await self.get_artifact(dep_ref.artifact_id)
            if dep_artifact:
                # Remove reference from dependency artifact
                dep_artifact.referenced_by = [
                    ref for ref in dep_artifact.referenced_by 
                    if ref.artifact_id != artifact.metadata.id
                ]
