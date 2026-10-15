import sys
from app.seed.seeder_session import get_session
from app.models.users import User
from app.models.groups import Group
from app.models.permissions import Permission
from app.seed.seed_permissions_adhoc import seed_new_permissions

def bootstrap_admin(email: str, first_name: str, last_name: str):
    """
    Bootstraps an initial System Administrator user into an empty production database.
    This creates the necessary permissions, the Admin group, and the User record,
    allowing the first user to log in via SSO and configure the system.
    """
    print(f"Bootstrapping early system access for {email}...")
    
    # 1. Ensure all system permissions exist in the database
    seed_new_permissions()
    
    session = get_session()
    
    try:
        # 2. Check for or create the System Administrators group
        admin_group = session.query(Group).filter_by(name="System Administrators").first()
        if not admin_group:
            print("Creating 'System Administrators' group...")
            admin_group = Group(name="System Administrators", description="Created by bootstrapper: Full system access")
            session.add(admin_group)
            
        # 3. Attach all available permissions to the group
        all_perms = session.query(Permission).all()
        admin_group.permissions = all_perms
        
        # 4. Check for or create the User
        user = session.query(User).filter_by(email=email).first()
        if not user:
            print(f"Creating user record for {email}...")
            user = User(email=email, first_name=first_name, last_name=last_name)
            session.add(user)
        else:
            print(f"User {email} already exists. Updating group mapping...")
            
        # 5. Link the user to the admin group
        if admin_group not in user.groups:
            user.groups.append(admin_group)
            
        session.commit()
        print("\n✅ Success!")
        print(f"User {email} is now a System Administrator.")
        print("You may now log into the FETCH2 frontend via SSO.")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error bootstrapping admin user: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bootstrap_production.py <email> [first_name] [last_name]")
        sys.exit(1)
        
    user_email = sys.argv[1]
    user_first = sys.argv[2] if len(sys.argv) > 2 else "System"
    user_last = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    
    bootstrap_admin(user_email, user_first, user_last)
