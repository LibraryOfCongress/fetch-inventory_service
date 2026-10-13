
import sys
import os
import importlib
import pkgutil

# Add current directory to path
sys.path.append(os.getcwd())

def check_models():
    print("Checking model imports...")
    try:
        import app.models
        package = app.models
        prefix = package.__name__ + "."
        
        # Walk packages and import each one
        for _, name, _ in pkgutil.walk_packages(package.__path__, prefix):
            print(f"Importing {name}...")
            importlib.import_module(name)
            
        print("\nAll models imported successfully!")
        
        print("Configuring mappers...")
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        print("Mappers configured successfully!")
        
        return 0
    except Exception as e:
        print(f"\nERROR importing models: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_models())
