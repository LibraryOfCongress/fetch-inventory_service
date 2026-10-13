
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

# Set DATABASE_URL to localhost for local testing
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/inventory_service"

def debug_login():
    print("Initializing Database...")
    try:
        from app.database.session import get_session
        from app.models.users import User
        from sqlalchemy import select
        # Pre-import these to avoid "name not defined" when testing User in isolation
        from app.models.batch_upload import BatchUpload 
        from app.models.verification_changes import VerificationChange
        from app.models.workflows import Workflow # Needed for VerificationChange
        from app.models.groups import Group
        from app.models.user_groups import UserGroup
        
        # Import ALL models via the main aggregator.
        # This ensures the SQLAlchemy registry is fully populated, just like in the main app.
        import app.models.all
        
        session_gen = get_session()
        session = next(session_gen)
        
        try:
            print("Querying User ID 1...")
            stmt = select(User).where(User.id == 1)
            result = session.execute(stmt) # This might trigger load
            user = result.scalars().first()
            
            if not user:
                print("User ID 1 not found. trying any user.")
                user = session.execute(select(User)).scalars().first()
                
            if not user:
                print("No users found.")
                return 0
                
            print(f"User found: {user.name}")
            
            # Eager load relationships as Pydantic would - attempt to access all fields
            # The error "AttributeError: strategy" often comes from a failed relationship load
            # particularly when lazy="selectin" is used on a misconfigured relationship.
            
            print("Accessing Accession Jobs...")
            _ = user.accession_jobs
            print("Accessing Shelving Jobs...")
            _ = user.shelving_jobs
            print("Accessing Verification Jobs...")
            _ = user.verification_jobs
            print("Accessing Groups...")
            try:
                # Groups uses a complex secondary join now - prime suspect
                groups = user.groups
                print(f"Groups loaded: {len(groups)}")
                for g in groups:
                     print(f" - Group: {g.name}")
            except Exception as e:
                print(f"!!! Error accessing groups: {e}")
                raise e

            print("Accessing Shipping Jobs...")
            _ = user.shipping_jobs
            
            print("Success! User login simulation complete.")
            return 0
        except Exception as e:
            raise e
        finally:
            session.close()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    if "app.models" not in sys.modules:
         # Force configure mappers
         from sqlalchemy.orm import configure_mappers
         configure_mappers()
         
    sys.exit(debug_login())
