
import asyncio
import httpx
import uuid

BASE_URL = "http://localhost:8000/api/v1/users"

async def verify_user_crud():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Create User (Guest)
        print("1. Creating Guest User...")
        # Empty body for guest creation (since steam_id is optional and defaults to None)
        response = await client.post(f"{BASE_URL}/", json={})
        if response.status_code not in [200, 201]:
            print(f"Failed to create user: {response.status_code} {response.text}")
            return
        
        user_data = response.json()
        user_id = user_data["user_id"]
        print(f"Created User: {user_data}")
        assert user_data["steam_id"] is None
        
        # 2. Get User
        print(f"2. Getting User {user_id}...")
        response = await client.get(f"{BASE_URL}/{user_id}")
        if response.status_code != 200:
            print(f"Failed to get user: {response.status_code} {response.text}")
            return
        print(f"Got User: {response.json()}")
        assert response.json()["user_id"] == user_id

        # 3. Update User (Set steam_id)
        new_steam_id = f"test_steam_{uuid.uuid4().hex[:8]}"
        print(f"3. Updating User {user_id} with steam_id={new_steam_id}...")
        response = await client.patch(f"{BASE_URL}/{user_id}", json={"steam_id": new_steam_id})
        if response.status_code != 200:
            print(f"Failed to update user: {response.status_code} {response.text}")
            return
        updated_user = response.json()
        print(f"Updated User: {updated_user}")
        assert updated_user["steam_id"] == new_steam_id
        
        # 4. Delete User
        print(f"4. Deleting User {user_id}...")
        response = await client.delete(f"{BASE_URL}/{user_id}")
        if response.status_code != 204:
            print(f"Failed to delete user: {response.status_code} {response.text}")
            return
        print("Deleted User (204 No Content)")

        # 5. Verify Delete
        print(f"5. Verifying Delete...")
        response = await client.get(f"{BASE_URL}/{user_id}")
        if response.status_code == 404:
            print("Verified: User not found (404)")
        else:
            print(f"Error: User still exists or other error: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(verify_user_crud())
