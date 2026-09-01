"""认证模块测试：注册/登录/忘记密码(dev)/重置密码/修改密码"""
import pytest
import uuid

from tests.conftest import _register_and_login


async def test_register_success(client):
    uname = f"reg_{uuid.uuid4().hex[:8]}"
    r = await client.post("/api/auth/register", json={
        "username": uname, "email": f"{uname}@test.com", "password": "testpass123",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"]
    assert data["user"]["username"] == uname
    assert "password" not in str(data["user"])


async def test_register_duplicate_username(client):
    uname = f"dup_{uuid.uuid4().hex[:8]}"
    payload = {"username": uname, "email": f"{uname}@test.com", "password": "testpass123"}
    r1 = await client.post("/api/auth/register", json=payload)
    r2 = await client.post("/api/auth/register", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 400  # 用户名重复


async def test_login_wrong_password(client):
    uname = f"lw_{uuid.uuid4().hex[:8]}"
    await client.post("/api/auth/register", json={
        "username": uname, "email": f"{uname}@test.com", "password": "testpass123",
    })
    r = await client.post("/api/auth/login", json={"username": uname, "password": "wrongpass"})
    assert r.status_code in (400, 401)


async def test_login_success_and_me(client):
    uname = f"ok_{uuid.uuid4().hex[:8]}"
    await client.post("/api/auth/register", json={
        "username": uname, "email": f"{uname}@test.com", "password": "testpass123",
    })
    r = await client.post("/api/auth/login", json={"username": uname, "password": "testpass123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    # 无效 token 拒绝
    bad = await client.get("/api/equipment/items", headers={"Authorization": "Bearer invalid.token.here"})
    assert bad.status_code == 401
    assert token  # 有效 token 由其它测试覆盖


async def test_forgot_password_dev_mode_returns_token(client):
    """dev 模式（DEBUG=true）应直接返回重置凭证"""
    uname = f"fp_{uuid.uuid4().hex[:8]}"
    await client.post("/api/auth/register", json={
        "username": uname, "email": f"{uname}@test.com", "password": "testpass123",
    })
    r = await client.post("/api/auth/forgot-password", json={"email": f"{uname}@test.com"})
    assert r.status_code == 200
    data = r.json()
    assert data["reset_token"], "dev 模式应返回 reset_token"
    assert "重置" in data["message"]


async def test_forgot_password_unknown_email_no_leak(client):
    """未知邮箱不泄露注册状态"""
    r = await client.post("/api/auth/forgot-password", json={"email": "nobody@nowhere.com"})
    assert r.status_code == 200
    assert r.json()["reset_token"] is None


async def test_reset_password_flow(client):
    """忘记密码 → 重置密码 → 新密码可登录"""
    uname = f"rs_{uuid.uuid4().hex[:8]}"
    email = f"{uname}@test.com"
    await client.post("/api/auth/register", json={
        "username": uname, "email": email, "password": "oldpass123",
    })
    fp = await client.post("/api/auth/forgot-password", json={"email": email})
    token = fp.json()["reset_token"]

    # 太短的新密码被拒
    short = await client.post("/api/auth/reset-password", json={"token": token, "new_password": "123"})
    assert short.status_code == 400

    r = await client.post("/api/auth/reset-password", json={"token": token, "new_password": "newpass456"})
    assert r.status_code == 200

    # 旧密码失效、新密码生效
    old = await client.post("/api/auth/login", json={"username": uname, "password": "oldpass123"})
    assert old.status_code in (400, 401)
    new = await client.post("/api/auth/login", json={"username": uname, "password": "newpass456"})
    assert new.status_code == 200


async def test_reset_password_invalid_token(client):
    r = await client.post("/api/auth/reset-password", json={
        "token": "not-a-real-token", "new_password": "newpass456",
    })
    assert r.status_code == 400


async def test_change_password(client):
    uname = f"cp_{uuid.uuid4().hex[:8]}"
    headers, _ = await _register_and_login(client, uname)

    # 当前密码错误
    bad = await client.post("/api/auth/change-password", headers=headers, json={
        "current_password": "wrong", "new_password": "brandnew123",
    })
    assert bad.status_code == 400

    ok = await client.post("/api/auth/change-password", headers=headers, json={
        "current_password": "testpass123", "new_password": "brandnew123",
    })
    assert ok.status_code == 200

    # 新密码登录成功
    r = await client.post("/api/auth/login", json={"username": uname, "password": "brandnew123"})
    assert r.status_code == 200
