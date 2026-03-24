import sys
sys.path.insert(0, "backend")
from app import app

with app.test_client() as c:
    with c.session_transaction() as s:
        s["user"] = {
            "sub": "student-1",
            "role": "student",
            "resource_link_id": "res-1",
        }

    create = c.post("/api/attempts")
    print("CREATE:", create.status_code, create.json)
    assert create.status_code == 201, create.json
    attempt_id = create.json["attempt_id"]

    get1 = c.get(f"/api/attempts/{attempt_id}")
    print("GET:", get1.status_code, get1.json)

    reset = c.post(f"/api/attempts/{attempt_id}/reset")
    print("RESET:", reset.status_code, reset.json)
    assert reset.status_code == 200, reset.json

    term = c.post(f"/api/attempts/{attempt_id}/terminate")
    print("TERMINATE:", term.status_code, term.json)
    assert term.status_code == 200, term.json

    get2 = c.get(f"/api/attempts/{attempt_id}")
    print("GET AFTER TERMINATE:", get2.status_code, get2.json)