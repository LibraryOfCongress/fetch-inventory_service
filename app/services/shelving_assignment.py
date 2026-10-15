# /app/services/shelving_assignment.py - NEW SERVICE FOR SHELVE BY LIST FEATURE

"""
ShelvingAssignmentService handles:
1. Container validation for adding to shelving lists
2. Pre-assignment of shelf positions with physical dimension checks
3. Position reservation with timestamps
4. Validation during execution
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, not_, func, asc

from app.models.shelving_jobs import ShelvingJob, ShelvingJobStatus
from app.models.shelving_job_containers import ShelvingJobContainer, ShelvingJobContainerStatus
from app.models.verification_jobs import VerificationJob, VerificationJobStatus
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.shelf_types import ShelfType
from app.models.size_class import SizeClass
from app.models.owners import Owner
from app.models.barcodes import Barcode
from app.models.modules import Module
from app.models.aisles import Aisle
from app.models.sides import Side
from app.models.ladders import Ladder


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of container validation."""
    is_valid: bool
    container_type: Optional[str] = None  # "Tray" or "NonTray"
    container_id: Optional[int] = None
    barcode_value: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    size_class_id: Optional[int] = None
    size_class_name: Optional[str] = None
    verification_job_id: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class PreAssignmentResult:
    """Result of running pre-assignment."""
    assigned_count: int
    unassigned_count: int
    unassigned_barcodes: List[str]
    message: str


def evaluate_container_validation(
    *,
    container_type: str,
    container_id: int,
    barcode_value: str,
    shelf_position_id: Optional[int],
    verification_job_id: Optional[int],
    verification_completed: bool,
    conflicting_shelving_job_id: Optional[int],
    owner_id: Optional[int] = None,
    owner_name: Optional[str] = None,
    size_class_id: Optional[int] = None,
    size_class_name: Optional[str] = None,
) -> ValidationResult:
    """
    Pure decision logic for whether a container may be added to a shelving list.

    All inputs are already resolved, so this performs no DB access and is
    unit-testable in isolation. The caller loads verification status, the
    conflicting-job id (or None), and owner/size-class names before calling.
    """
    if shelf_position_id:
        return ValidationResult(
            is_valid=False,
            container_type=container_type,
            container_id=container_id,
            barcode_value=barcode_value,
            error_message=f"Barcode {barcode_value} is already shelved",
        )

    if not verification_job_id or not verification_completed:
        return ValidationResult(
            is_valid=False,
            container_type=container_type,
            container_id=container_id,
            barcode_value=barcode_value,
            error_message=f"Barcode {barcode_value} has not completed verification",
        )

    if conflicting_shelving_job_id is not None:
        return ValidationResult(
            is_valid=False,
            container_type=container_type,
            container_id=container_id,
            barcode_value=barcode_value,
            error_message=f"Barcode {barcode_value} is on Shelving Job #{conflicting_shelving_job_id}",
        )

    return ValidationResult(
        is_valid=True,
        container_type=container_type,
        container_id=container_id,
        barcode_value=barcode_value,
        owner_id=owner_id,
        owner_name=owner_name,
        size_class_id=size_class_id,
        size_class_name=size_class_name,
        verification_job_id=verification_job_id,
    )


class ShelvingAssignmentService:
    """
    Service for managing Shelve by List operations:
    - Validating containers for list addition
    - Pre-assigning shelf positions
    - Position reservation management
    """

    def validate_container_for_list(
        self,
        session: Session,
        container_barcode: str,
        shelving_job_id: int
    ) -> ValidationResult:
        """
        Validate if a container can be added to a shelving list.
        
        Checks:
        1. Container exists (tray or non-tray item)
        2. Container is on a COMPLETED verification job
        3. Container is not already shelved (shelf_position_id is null)
        4. Container is not on another active shelving job
        
        Returns ValidationResult with container info or error.
        """
        # Find the barcode
        barcode = session.execute(
            select(Barcode).where(Barcode.value == container_barcode)
        ).scalars().first()
        
        if not barcode:
            return ValidationResult(
                is_valid=False,
                barcode_value=container_barcode,
                error_message=f"Barcode {container_barcode} not found"
            )
        
        # Check if it's a tray
        tray = session.execute(
            select(Tray).where(Tray.barcode_id == barcode.id)
        ).scalars().first()
        
        if tray:
            return self._validate_tray(session, tray, shelving_job_id)
        
        # Check if it's a non-tray item
        non_tray = session.execute(
            select(NonTrayItem).where(NonTrayItem.barcode_id == barcode.id)
        ).scalars().first()
        
        if non_tray:
            return self._validate_non_tray(session, non_tray, shelving_job_id)
        
        return ValidationResult(
            is_valid=False,
            barcode_value=container_barcode,
            error_message=f"Barcode {container_barcode} is not associated with a tray or non-tray item"
        )

    def _validate_tray(
        self,
        session: Session,
        tray: Tray,
        shelving_job_id: int
    ) -> ValidationResult:
        """Validate a tray for list addition."""
        barcode_value = tray.barcode.value if tray.barcode else str(tray.id)

        verification_completed = False
        if tray.verification_job_id:
            verification_job = session.get(VerificationJob, tray.verification_job_id)
            verification_completed = bool(
                verification_job
                and verification_job.status == VerificationJobStatus.Completed
            )

        existing_container = session.execute(
            select(ShelvingJobContainer)
            .join(ShelvingJob)
            .where(
                ShelvingJobContainer.tray_id == tray.id,
                ShelvingJobContainer.shelving_job_id != shelving_job_id,
                ShelvingJob.status.in_([
                    ShelvingJobStatus.Created,
                    ShelvingJobStatus.Running,
                    ShelvingJobStatus.Paused
                ])
            )
        ).scalars().first()

        owner = session.get(Owner, tray.owner_id) if tray.owner_id else None
        size_class = session.get(SizeClass, tray.size_class_id) if tray.size_class_id else None

        return evaluate_container_validation(
            container_type="Tray",
            container_id=tray.id,
            barcode_value=barcode_value,
            shelf_position_id=tray.shelf_position_id,
            verification_job_id=tray.verification_job_id,
            verification_completed=verification_completed,
            conflicting_shelving_job_id=(
                existing_container.shelving_job_id if existing_container else None
            ),
            owner_id=tray.owner_id,
            owner_name=owner.name if owner else None,
            size_class_id=tray.size_class_id,
            size_class_name=size_class.name if size_class else None,
        )

    def _validate_non_tray(
        self,
        session: Session,
        non_tray: NonTrayItem,
        shelving_job_id: int
    ) -> ValidationResult:
        """Validate a non-tray item for list addition."""
        barcode_value = non_tray.barcode.value if non_tray.barcode else str(non_tray.id)

        verification_completed = False
        if non_tray.verification_job_id:
            verification_job = session.get(VerificationJob, non_tray.verification_job_id)
            verification_completed = bool(
                verification_job
                and verification_job.status == VerificationJobStatus.Completed
            )

        existing_container = session.execute(
            select(ShelvingJobContainer)
            .join(ShelvingJob)
            .where(
                ShelvingJobContainer.non_tray_item_id == non_tray.id,
                ShelvingJobContainer.shelving_job_id != shelving_job_id,
                ShelvingJob.status.in_([
                    ShelvingJobStatus.Created,
                    ShelvingJobStatus.Running,
                    ShelvingJobStatus.Paused
                ])
            )
        ).scalars().first()

        owner = session.get(Owner, non_tray.owner_id) if non_tray.owner_id else None
        size_class = session.get(SizeClass, non_tray.size_class_id) if non_tray.size_class_id else None

        return evaluate_container_validation(
            container_type="NonTray",
            container_id=non_tray.id,
            barcode_value=barcode_value,
            shelf_position_id=non_tray.shelf_position_id,
            verification_job_id=non_tray.verification_job_id,
            verification_completed=verification_completed,
            conflicting_shelving_job_id=(
                existing_container.shelving_job_id if existing_container else None
            ),
            owner_id=non_tray.owner_id,
            owner_name=owner.name if owner else None,
            size_class_id=non_tray.size_class_id,
            size_class_name=size_class.name if size_class else None,
        )

    def pre_assign_containers(
        self,
        session: Session,
        shelving_job_id: int,
        building_id: int,
        module_id: Optional[int] = None,
        aisle_id: Optional[int] = None,
        ladder_id: Optional[int] = None,
        allow_unassigned_size: bool = False,
        allow_unassigned_owner: bool = False,
        allow_tiered_owner: bool = False
    ) -> PreAssignmentResult:
        """
        Pre-assign shelf positions to containers in a shelving job.
        
        Uses database-level locking to prevent race conditions.
        Validates physical dimensions (shelf.height >= size_class.height).
        Supports partial assignment - unassignable containers marked as 'Unassigned'.
        """
        # Get all pending containers for this job
        containers = session.execute(
            select(ShelvingJobContainer)
            .where(
                ShelvingJobContainer.shelving_job_id == shelving_job_id,
                ShelvingJobContainer.status == ShelvingJobContainerStatus.PENDING
            )
        ).scalars().all()
        
        if not containers:
            return PreAssignmentResult(
                assigned_count=0,
                unassigned_count=0,
                unassigned_barcodes=[],
                message="No pending containers to assign"
            )
        
        # Group containers by (size_class_id, owner_id) for efficient assignment
        containers_by_group = {}
        for container in containers:
            # Get the actual container to find size_class and owner
            if container.tray_id:
                tray = session.get(Tray, container.tray_id)
                if tray:
                    key = (tray.size_class_id, tray.owner_id)
                    containers_by_group.setdefault(key, []).append(container)
            elif container.non_tray_item_id:
                non_tray = session.get(NonTrayItem, container.non_tray_item_id)
                if non_tray:
                    key = (non_tray.size_class_id, non_tray.owner_id)
                    containers_by_group.setdefault(key, []).append(container)
        
        assigned_count = 0
        unassigned_count = 0
        unassigned_barcodes = []
        
        # Process each group
        for (size_class_id, owner_id), group_containers in containers_by_group.items():
            # Find available positions for this size_class/owner combination
            available_positions = self._find_available_positions(
                session=session,
                size_class_id=size_class_id,
                owner_id=owner_id,
                building_id=building_id,
                module_id=module_id,
                aisle_id=aisle_id,
                ladder_id=ladder_id,
                allow_unassigned_size=allow_unassigned_size,
                allow_unassigned_owner=allow_unassigned_owner,
                allow_tiered_owner=allow_tiered_owner,
                count_needed=len(group_containers)
            )
            
            # Assign positions to containers
            for i, container in enumerate(group_containers):
                if i < len(available_positions):
                    position = available_positions[i]
                    container.proposed_shelf_position_id = position.id
                    container.position_reserved_at = datetime.now(timezone.utc)
                    container.status = ShelvingJobContainerStatus.ASSIGNED
                    assigned_count += 1
                else:
                    # Not enough positions
                    container.status = ShelvingJobContainerStatus.UNASSIGNED
                    unassigned_count += 1
                    # Get barcode for error message
                    barcode_value = self._get_container_barcode(session, container)
                    unassigned_barcodes.append(barcode_value)
                
                session.add(container)
        
        session.commit()
        
        message = f"{assigned_count} of {assigned_count + unassigned_count} containers assigned."
        if unassigned_count > 0:
            message += f" {unassigned_count} could not be assigned due to insufficient matching shelf positions."
        
        return PreAssignmentResult(
            assigned_count=assigned_count,
            unassigned_count=unassigned_count,
            unassigned_barcodes=unassigned_barcodes,
            message=message
        )

    def _find_available_positions(
        self,
        session: Session,
        size_class_id: int,
        owner_id: int,
        building_id: int,
        module_id: Optional[int],
        aisle_id: Optional[int],
        ladder_id: Optional[int],
        allow_unassigned_size: bool,
        allow_unassigned_owner: bool,
        allow_tiered_owner: bool,
        count_needed: int
    ) -> List[ShelfPosition]:
        """
        Find available shelf positions matching criteria.
        
        Validates:
        - shelf.height >= size_class.height (physical fit)
        - Owner match (or unassigned/tiered if allowed)
        - Size class match (or unassigned if allowed)
        - Position not occupied or proposed elsewhere
        """
        # Get size class for height comparison
        size_class = session.get(SizeClass, size_class_id)
        if not size_class:
            return []
        
        # Build location filter
        location_conditions = []
        if ladder_id:
            location_conditions.append(Shelf.ladder_id == ladder_id)
        elif aisle_id:
            location_conditions.append(Side.aisle_id == aisle_id)
        elif module_id:
            location_conditions.append(Aisle.module_id == module_id)
        else:
            location_conditions.append(Module.building_id == building_id)
        
        # Build owner conditions
        owner_conditions = [Shelf.owner_id == owner_id]
        if allow_unassigned_owner:
            # Find the "Unassigned" owner
            unassigned_owner = session.execute(
                select(Owner).where(Owner.name == "Unassigned")
            ).scalars().first()
            if unassigned_owner:
                owner_conditions.append(Shelf.owner_id == unassigned_owner.id)
        if allow_tiered_owner:
            # Find parent owners
            owner = session.get(Owner, owner_id)
            if owner and owner.parent_owner_id:
                owner_conditions.append(Shelf.owner_id == owner.parent_owner_id)
        
        # Build size class conditions
        size_conditions = [ShelfType.size_class_id == size_class_id]
        if allow_unassigned_size:
            # Find the "Unassigned" size class
            unassigned_size = session.execute(
                select(SizeClass).where(SizeClass.name == "Unassigned")
            ).scalars().first()
            if unassigned_size:
                size_conditions.append(ShelfType.size_class_id == unassigned_size.id)
        
        # Build the query
        query = (
            select(ShelfPosition)
            .join(Shelf, ShelfPosition.shelf_id == Shelf.id)
            .join(ShelfType, Shelf.shelf_type_id == ShelfType.id)
            .join(Ladder, Shelf.ladder_id == Ladder.id)
            .join(Side, Ladder.side_id == Side.id)
            .join(Aisle, Side.aisle_id == Aisle.id)
            .join(Module, Aisle.module_id == Module.id)
            # Physical dimension check
            .where(Shelf.height >= size_class.height)
            # Location filter
            .where(and_(*location_conditions))
            # Owner filter
            .where(or_(*owner_conditions))
            # Size class filter
            .where(or_(*size_conditions))
            # Not occupied by tray
            .where(not_(
                select(Tray.id).where(Tray.shelf_position_id == ShelfPosition.id).exists()
            ))
            # Not occupied by non-tray
            .where(not_(
                select(NonTrayItem.id).where(NonTrayItem.shelf_position_id == ShelfPosition.id).exists()
            ))
            # Not proposed for tray
            .where(not_(
                select(Tray.id).where(Tray.shelf_position_proposed_id == ShelfPosition.id).exists()
            ))
            # Not proposed for non-tray
            .where(not_(
                select(NonTrayItem.id).where(NonTrayItem.shelf_position_proposed_id == ShelfPosition.id).exists()
            ))
            # Not reserved by another ShelvingJobContainer
            .where(not_(
                select(ShelvingJobContainer.id)
                .where(ShelvingJobContainer.proposed_shelf_position_id == ShelfPosition.id)
                .where(ShelvingJobContainer.status == ShelvingJobContainerStatus.ASSIGNED)
                .exists()
            ))
            .order_by(
                asc(Module.module_number),
                asc(Aisle.aisle_number),
                asc(Side.side_orientation_id),
                asc(Ladder.ladder_number),
                asc(Shelf.shelf_number),
                asc(ShelfPosition.position_number)
            )
            .limit(count_needed)
            .with_for_update()  # Lock positions to prevent race conditions
        )
        
        return list(session.execute(query).scalars().all())

    def _get_container_barcode(
        self,
        session: Session,
        container: ShelvingJobContainer
    ) -> str:
        """Get the barcode value for a container."""
        if container.tray_id:
            tray = session.get(Tray, container.tray_id)
            if tray and tray.barcode:
                return tray.barcode.value
            return f"TRAY-{container.tray_id}"
        elif container.non_tray_item_id:
            non_tray = session.get(NonTrayItem, container.non_tray_item_id)
            if non_tray and non_tray.barcode:
                return non_tray.barcode.value
            return f"NONTRAY-{container.non_tray_item_id}"
        return f"CONTAINER-{container.id}"


# Singleton instance
shelving_assignment_service = ShelvingAssignmentService()
