async def test_registers_new_user_and_returns_jwt(client):
  response = await client.post("/login", json={"username": "Alice", "password": "correcthorse"})
  assert response.status_code == 200

  data = response.json()
  assert "access_token" in data
  assert data["token_type"] == "bearer"
  assert data["user"]["username"] == "Alice"
  assert data["user"]["score"] == 500
  assert "password_hash" not in data["user"]


async def test_logs_in_existing_user_with_correct_password(client):
  await client.post("/login", json={"username": "Bob", "password": "correcthorse"})

  response = await client.post("/login", json={"username": "Bob", "password": "correcthorse"})
  assert response.status_code == 200


async def test_rejects_wrong_password(client):
  await client.post("/login", json={"username": "Carol", "password": "correcthorse"})

  response = await client.post("/login", json={"username": "Carol", "password": "wrongpassword"})
  assert response.status_code == 401
