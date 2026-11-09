"""Create the two fictional demo users in the LOCAL dev Keycloak (admin/admin), with realm roles.

Usage: python3 seed/keycloak_users.py
"""
import json, urllib.request

KC = "http://localhost:8080"
PASSWORD = "DemoMetrique2026!"
USERS = [
    dict(username="demo.plombier", email="demo.plombier@metrique.local", firstName="Rodrigue", lastName="Agbo", roles=["provider", "client"]),
    dict(username="demo.cliente", email="demo.cliente@metrique.local", firstName="Afi", lastName="Dossou", roles=["client"]),
]


def call(method, path, token=None, body=None, form=None):
    data = json.dumps(body).encode() if body is not None else (form.encode() if form else None)
    req = urllib.request.Request(KC + path, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json" if body is not None else "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main():
    tok = call("POST", "/realms/master/protocol/openid-connect/token",
               form="client_id=admin-cli&username=admin&password=admin&grant_type=password")["access_token"]
    existing = {r["name"] for r in call("GET", "/admin/realms/metrique/roles", tok)}
    for role in ("client", "provider"):
        if role not in existing:
            call("POST", "/admin/realms/metrique/roles", tok, {"name": role})
    for u in USERS:
        found = call("GET", f"/admin/realms/metrique/users?exact=true&username={u['username']}", tok)
        if not found:
            call("POST", "/admin/realms/metrique/users", tok, {
                "username": u["username"], "email": u["email"], "firstName": u["firstName"], "lastName": u["lastName"],
                "enabled": True, "emailVerified": True,
                "credentials": [{"type": "password", "value": PASSWORD, "temporary": False}]})
            found = call("GET", f"/admin/realms/metrique/users?exact=true&username={u['username']}", tok)
        uid = found[0]["id"]
        roles = [call("GET", f"/admin/realms/metrique/roles/{r}", tok) for r in u["roles"]]
        call("POST", f"/admin/realms/metrique/users/{uid}/role-mappings/realm", tok, roles)
        print(u["username"], uid)


if __name__ == "__main__":
    main()
