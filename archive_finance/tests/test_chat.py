"""Tests du chat dans une session : envoi messages, persistance, historique après refresh."""


def _new_session(client, headers) -> str:
    return client.post("/sessions", json={}, headers=headers).json()["id"]


def test_send_message_returns_answer_and_tools(client, alice_headers):
    sid = _new_session(client, alice_headers)
    r = client.post(f"/sessions/{sid}/chat", headers=alice_headers,
                    json={"message": "C'est quoi un livret A ?"})
    assert r.status_code == 200
    body = r.json()
    assert "Définition mockée" in body["answer"]
    assert "rag_finance" in body["tools_used"]
    assert "message_id" in body


def test_actuality_question_uses_web_search(client, alice_headers):
    sid = _new_session(client, alice_headers)
    r = client.post(f"/sessions/{sid}/chat", headers=alice_headers,
                    json={"message": "Quel est le taux du Livret A en 2026 ?"})
    assert "web_search" in r.json()["tools_used"]


def test_messages_are_persisted(client, alice_headers):
    """Vérifie qu'on peut récupérer l'historique après l'envoi (= cas du refresh)."""
    sid = _new_session(client, alice_headers)
    client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": "Q1 ?"})
    client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": "Q2 taux ?"})

    msgs = client.get(f"/sessions/{sid}/messages", headers=alice_headers).json()
    assert len(msgs) == 4  # 2 user + 2 assistant
    assert msgs[0]["role"] == "user" and msgs[0]["content"] == "Q1 ?"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user" and msgs[2]["content"] == "Q2 taux ?"
    assert msgs[3]["role"] == "assistant"


def test_assistant_message_records_tool_used(client, alice_headers):
    sid = _new_session(client, alice_headers)
    client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": "définition"})
    msgs = client.get(f"/sessions/{sid}/messages", headers=alice_headers).json()
    assistant = msgs[1]
    assert assistant["tool_used"] == "rag_finance"


def test_session_title_auto_generated_from_first_message(client, alice_headers):
    sid = _new_session(client, alice_headers)
    client.post(f"/sessions/{sid}/chat", headers=alice_headers,
                json={"message": "Comment ça marche le livret A ?"})
    sess = client.get(f"/sessions/{sid}", headers=alice_headers).json()
    assert sess["title"] == "Comment ça marche le livret A ?"


def test_long_first_message_truncates_title(client, alice_headers):
    sid = _new_session(client, alice_headers)
    long_msg = "Bonjour je voudrais comprendre en détail comment fonctionne le livret A et ses taux"
    client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": long_msg})
    sess = client.get(f"/sessions/{sid}", headers=alice_headers).json()
    assert sess["title"].endswith("…")
    assert len(sess["title"]) <= 50


def test_cannot_chat_in_ended_session(client, alice_headers):
    sid = _new_session(client, alice_headers)
    client.post(f"/sessions/{sid}/end", headers=alice_headers)
    r = client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": "X"})
    assert r.status_code == 400


def test_empty_message_rejected(client, alice_headers):
    sid = _new_session(client, alice_headers)
    r = client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": ""})
    assert r.status_code == 422


def test_chat_in_others_session_returns_404(client, alice_headers):
    sid = _new_session(client, alice_headers)
    bob_token = client.post("/auth/signup", json={
        "email": "bob@test.com", "password": "bob12345",
    }).json()["token"]
    r = client.post(
        f"/sessions/{sid}/chat",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={"message": "spy"},
    )
    assert r.status_code == 404


def test_full_user_journey(client, alice_headers):
    """Parcours complet : crée session → 2 messages → end → feedback."""
    sid = _new_session(client, alice_headers)
    client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": "Q1"})
    client.post(f"/sessions/{sid}/chat", headers=alice_headers, json={"message": "Q2 taux"})
    end = client.post(f"/sessions/{sid}/end", headers=alice_headers)
    assert end.status_code == 200
    fb = client.post(f"/sessions/{sid}/feedback", headers=alice_headers,
                     json={"rating": 5, "comment": "Top !"})
    assert fb.status_code == 201

    # État final cohérent
    sess = client.get(f"/sessions/{sid}", headers=alice_headers).json()
    assert sess["status"] == "ended"
    assert sess["rating"] == 5
    assert len(client.get(f"/sessions/{sid}/messages", headers=alice_headers).json()) == 4
