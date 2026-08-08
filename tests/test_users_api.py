async def test_login_creates_user_and_jwt(client):
  response = await client.post("/login", json={"username": "Alice"})
  assert response.status_code == 200

  data = response.json()
  assert "access_token" in data
  assert data["token_type"] == "bearer"
  assert data["user"]["username"] == "Alice"
  assert data["user"]["score"] == 500
