from sqlmodel import Session
from sqlalchemy import event
from app.models.shelf_positions import ShelfPosition

@event.listens_for(ShelfPosition, "after_insert")
def generate_location(mapper, connection, target):
    """Update the shelf position location after the object has been inserted into the database."""
    with Session(bind=connection) as session:
        refreshed_target = session.query(ShelfPosition).filter_by(id=target.id).one()
        refreshed_target.update_position_address(session=session)
        session.add(refreshed_target)
        session.commit()
