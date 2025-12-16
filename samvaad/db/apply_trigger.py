from sqlalchemy import text
from samvaad.db.session import get_db_context

def apply_trigger():
    print("Applying User Sync Trigger...")
    with get_db_context() as db:
        with open("samvaad/db/sync_users.sql", "r") as f:
            sql = f.read()
        
        try:
            # Split by statement if needed, or execute block
            # SQLAlchemy might not support multi-statement in one execute calls depending on driver
            # But for DDL it usually works if wrapped properly or separate.
            # We'll try singular execution or just running it.
            
            db.execute(text(sql))
            db.commit()
            print("Successfully created 'handle_new_user' function and 'on_auth_user_created' trigger.")
        except Exception as e:
            print(f"Error applying trigger: {e}")
            print("Ensure your database user has permissions to access the 'auth' schema.")

if __name__ == "__main__":
    apply_trigger()
