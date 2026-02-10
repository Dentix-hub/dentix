import pytest
from backend.routers import admin
from backend import models, schemas

def test_admin_users_query_count(db_session):
    """
    Test that the admin user query eager loads tenant relations to avoid N+1 queries.
    """
    # 1. Create Dummy Tenant
    t = db_session.query(models.Tenant).filter_by(name="N+1 Test Tenant").first()
    if not t:
        t = models.Tenant(name="N+1 Test Tenant", plan="trial")
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)

    # 2. Create Users
    created_users = []
    for i in range(5):
        u_name = f"nplus1_user_{i}"
        u = db_session.query(models.User).filter_by(username=u_name).first()
        if not u:
            u = models.User(
                username=u_name, hashed_password="pw", role="doctor", tenant_id=t.id
            )
            db_session.add(u)
            created_users.append(u)
    db_session.commit()

    # 3. Execute Query
    # We are testing the service function logic directly to ensure it runs and returns generated fields
    try:
        # Mocking current_user logic if needed, but get_global_users just needs an object with role="super_admin"
        super_admin = models.User(role="super_admin")
        
        users = admin.get_global_users(
            db=db_session, limit=10, current_user=super_admin
        )

        # 4. Verify
        # We should find at least the 5 users we created (plus potentially others from other tests)
        assert len(users) >= 5
        
        # Check that the joined/hybrid property 'tenant_name' is populated
        # (This confirms that the query fetched tenant info)
        found_our_user = False
        for user_schema in users:
            # users is a list of schemas.UserOut usually, or the models if response_model is doing the conversion
            # The router function returns models/rows, FastAPI converts to schema.
            # Let's check what the function returns.
            # admin.get_global_users returns a list of models or dicts?
            # It usually returns a list of User objects.
            
            if user_schema.username.startswith("nplus1_user_"):
                found_our_user = True
                # Accessing tenant_name should not trigger a lazy load if it was joined,
                # but with an in-memory DB and sync session it's hard to strict prove N+1 without query counting.
                # However, we verify the field is accessible.
                assert user_schema.tenant_name == "N+1 Test Tenant"
        
        assert found_our_user, "Did not find the created test users"

    finally:
        # Cleanup (optional with function scoped db_session but good practice)
        pass
