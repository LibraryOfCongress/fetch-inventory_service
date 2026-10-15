# /app/helpers/owner_helpers.py
"""
Helper functions for owner-related operations including hierarchical queries.
"""

from typing import List, Set
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.owners import Owner


def get_owner_with_descendants(session: Session, owner_ids: List[int]) -> List[int]:
    """
    Given a list of owner IDs, return a list including those IDs
    plus all their descendant (child) owner IDs.

    Uses iterative approach to traverse parent_owner_id relationships.

    Args:
        session: SQLAlchemy database session
        owner_ids: List of owner IDs to expand

    Returns:
        List of owner IDs including original IDs and all descendants
    """
    if not owner_ids:
        return []

    # Use a set for efficient deduplication
    all_owner_ids: Set[int] = set(owner_ids)
    ids_to_process: Set[int] = set(owner_ids)

    # Iteratively find all children until no more are found
    while ids_to_process:
        # Find all owners whose parent_owner_id is in the current set
        query = select(Owner.id).where(Owner.parent_owner_id.in_(ids_to_process))
        result = session.execute(query).scalars().all()

        # Get new children that we haven't seen yet
        new_children = set(result) - all_owner_ids

        # Add new children to our result set
        all_owner_ids.update(new_children)

        # Process these new children in the next iteration
        ids_to_process = new_children

    return list(all_owner_ids)


def is_child_of_owner(session: Session, child_owner_id: int, parent_owner_id: int) -> bool:
    """
    Check if child_owner is a descendant of parent_owner.
    
    Traverses up the parent_owner_id chain from child to see if it reaches parent.
    
    Args:
        session: SQLAlchemy database session
        child_owner_id: The owner ID to check as a potential child
        parent_owner_id: The owner ID to check as a potential parent
        
    Returns:
        True if child_owner is a descendant of parent_owner, False otherwise
    """
    if child_owner_id == parent_owner_id:
        return False  # Same owner is not a child
    
    current_id = child_owner_id
    visited = set()
    
    while current_id is not None:
        if current_id in visited:
            break  # Prevent infinite loop on circular references
        visited.add(current_id)
        
        owner = session.get(Owner, current_id)
        if owner is None:
            break
            
        if owner.parent_owner_id == parent_owner_id:
            return True
            
        current_id = owner.parent_owner_id
    
    return False
