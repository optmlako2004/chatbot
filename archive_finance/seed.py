"""
Crée des données mockées dans la BDD.

⚠️ Ce script DROP toute la BDD avant de seed (perte de données).

Mocks créés :
- 3 users : alice (email/pwd), bob (email/pwd), carol (Google mock), 1 anonyme
- Conversations variées : actives, terminées, avec/sans feedback
- Messages avec différents tools (rag_finance, web_search)

Usage :
    python seed.py

Pour effacer les mocks et repartir vide (sans en recréer) :
    python -c "from db import reset_db; reset_db()"
"""

from datetime import datetime, timedelta, timezone

from auth import hash_password
from db import db_session, reset_db
from models import ChatSession, Feedback, Message, User


def seed():
    print("🗑️  Reset de la BDD...")
    reset_db()

    print("👥 Création des utilisateurs mockés...")
    with db_session() as db:
        # User 1 : email/password
        alice = User(
            id="mock-alice",
            email="alice@test.com",
            password_hash=hash_password("alice123"),
            name="Alice Martin",
        )
        # User 2 : email/password
        bob = User(
            id="mock-bob",
            email="bob@test.com",
            password_hash=hash_password("bob123"),
            name="Bob Dupont",
        )
        # User 3 : Google OAuth (mock)
        carol = User(
            id="mock-carol",
            google_sub="mock-google-sub-12345",
            email="carol.gmail@gmail.com",
            name="Carol Bernard",
            picture="https://i.pravatar.cc/150?img=5",
        )
        # User 4 : anonyme
        anon = User(
            id="mock-anon-uuid",
            is_anonymous=True,
        )
        db.add_all([alice, bob, carol, anon])
        db.flush()

        now = datetime.now(timezone.utc)

        # Conv 1 (alice, terminée, avec feedback 5⭐)
        s1 = ChatSession(
            id="mock-session-1",
            user_id=alice.id,
            thread_id="thread-mock-1",
            title="Question sur le Livret A",
            status="ended",
            created_at=now - timedelta(days=2),
            ended_at=now - timedelta(days=2, hours=-1),
        )
        db.add(s1)
        db.add_all([
            Message(session_id=s1.id, role="user",
                    content="C'est quoi un Livret A ?",
                    created_at=now - timedelta(days=2, minutes=10)),
            Message(session_id=s1.id, role="assistant",
                    content="Le Livret A est un produit d'épargne réglementé par l'État français...",
                    tool_used="rag_finance",
                    created_at=now - timedelta(days=2, minutes=9)),
            Message(session_id=s1.id, role="user",
                    content="Et son taux actuel ?",
                    created_at=now - timedelta(days=2, minutes=8)),
            Message(session_id=s1.id, role="assistant",
                    content="Le taux du Livret A est de 1,5% depuis le 1er février 2026.",
                    tool_used="web_search",
                    created_at=now - timedelta(days=2, minutes=7)),
        ])
        db.add(Feedback(
            session_id=s1.id,
            rating=5,
            comment="Très clair et précis, merci !",
            created_at=now - timedelta(days=2, hours=-1),
        ))

        # Conv 2 (alice, active, en cours)
        s2 = ChatSession(
            id="mock-session-2",
            user_id=alice.id,
            thread_id="thread-mock-2",
            title="Comprendre le PEL",
            status="active",
            created_at=now - timedelta(hours=3),
        )
        db.add(s2)
        db.add_all([
            Message(session_id=s2.id, role="user",
                    content="Quelle est la différence entre PEL et CEL ?",
                    created_at=now - timedelta(hours=3)),
            Message(session_id=s2.id, role="assistant",
                    content="Le PEL (Plan d'Épargne Logement) et le CEL (Compte Épargne Logement) sont deux produits d'épargne...",
                    tool_used="rag_finance",
                    created_at=now - timedelta(hours=3, minutes=-1)),
        ])

        # Conv 3 (bob, terminée, feedback 3⭐)
        s3 = ChatSession(
            id="mock-session-3",
            user_id=bob.id,
            thread_id="thread-mock-3",
            title="Arnaques bancaires",
            status="ended",
            created_at=now - timedelta(days=1),
            ended_at=now - timedelta(days=1, hours=-1),
        )
        db.add(s3)
        db.add_all([
            Message(session_id=s3.id, role="user",
                    content="Comment se protéger des arnaques par téléphone ?",
                    created_at=now - timedelta(days=1)),
            Message(session_id=s3.id, role="assistant",
                    content="Pour vous protéger, ne communiquez jamais vos codes de carte bancaire...",
                    tool_used="rag_finance",
                    created_at=now - timedelta(days=1, minutes=-1)),
        ])
        db.add(Feedback(
            session_id=s3.id,
            rating=3,
            comment="Réponse correcte mais un peu courte.",
        ))

        # Conv 4 (carol Google, active, vide pour tester l'état initial)
        s4 = ChatSession(
            id="mock-session-4",
            user_id=carol.id,
            thread_id="thread-mock-4",
            title="Nouvelle conversation",
            status="active",
        )
        db.add(s4)

        # Conv 5 (anonyme)
        s5 = ChatSession(
            id="mock-session-5",
            user_id=anon.id,
            thread_id="thread-mock-5",
            title="Question rapide",
            status="ended",
            ended_at=now,
        )
        db.add(s5)
        db.add_all([
            Message(session_id=s5.id, role="user", content="Bonjour !"),
            Message(session_id=s5.id, role="assistant",
                    content="Bonjour ! Je suis l'assistant en éducation financière. Comment puis-je vous aider ?"),
        ])

    print("✅ Seed terminé.\n")
    print("Comptes de test :")
    print("  📧 alice@test.com / alice123    (5 conv terminée + 1 active)")
    print("  📧 bob@test.com   / bob123      (1 conv terminée)")
    print("  🔵 carol (Google mock)          (1 conv vide)")
    print("  👤 mock-anon-uuid (anonyme)     (1 conv terminée)")


if __name__ == "__main__":
    seed()
