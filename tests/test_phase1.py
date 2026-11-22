"""Phase 1 integration boundaries. Database and external provider I/O are isolated."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

from bson import ObjectId
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

import app as api
import auth
import db
import user_activity as activity
from model import rigcheck_engine as engine
from model.steam_database import get_game_by_name
from run_regression_tests import payload_for


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.addCleanup(self.client.close)

    def test_distinct_inside_records(self):
        games = self.client.get("/search", params={"q": "inside", "limit": 2}).json()
        self.assertEqual({(g["name"], g["appid"]) for g in games},
                         {("Inside", 2596760), ("INSIDE", 304430)})
        for game in games:
            self.assertEqual(self.client.get(f"/games/{game['appid']}").json()["name"], game["name"])
        self.assertIsNone(get_game_by_name("inside"))

    def test_identical_titles_serialize_independent_candidates(self):
        # Use both real catalog rows, forcing an exact title collision in this copy only.
        rows = engine.df[engine.df.Steam_AppID.isin([2596760, 304430])].copy()
        rows["Title"] = "Inside"
        rows["Vibe_Score"] = [10.0, 20.0]
        with patch.object(engine, "run_vibe_check", return_value=rows):
            response = self.client.post("/recommend", json=payload_for("inside"))
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["recommended_game"], "Inside")
        self.assertEqual([g["title"] for g in result["alternative_games"]], ["Inside"])
        games = [result, *result["alternative_games"]]
        self.assertEqual({g["appid"] for g in games}, {2596760, 304430})
        for game in games:
            self.assertTrue(game["store_url"].endswith(f"/{game['appid']}"))

    def test_empty_response_has_no_invented_id(self):
        with patch.object(engine, "run_vibe_check", return_value=engine.df.iloc[:0]):
            result = self.client.post("/recommend", json=payload_for("inside")).json()
        self.assertEqual((result["recommended_game"], result["alternative_games"]), ("", []))
        self.assertIsNone(result.get("appid"))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.uid = ObjectId()
        self.users, self.sessions = AsyncMock(), AsyncMock()
        self.sessions.delete_one.return_value.deleted_count = 1
        self.users.find_one.return_value = {"_id": self.uid, "password_hash": "private"}
        self.session = {"user_id": str(self.uid), "expires_at":
                        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
        self.sessions.find_one.return_value = self.session
        self.enterContext(patch.object(auth, "get_database", return_value={
            "users": self.users, "sessions": self.sessions}))
        # This probe exists only on the test app.
        private = FastAPI()

        @private.get("/owner")
        async def owner(user=Depends(auth.require_authenticated_user)):
            return {"id": str(user.id)}

        self.client = TestClient(private)
        self.addCleanup(self.client.close)

    def test_cookie_and_bearer_resolve_only_session_owner(self):
        headers = {"Authorization": "Bearer test-bearer"}
        self.assertEqual(self.client.get("/owner?user_id=other", headers=headers).json(),
                         {"id": str(self.uid)})
        self.sessions.find_one.assert_awaited_with({"token": "test-bearer"})
        self.client.cookies.set(auth.SESSION_COOKIE_NAME, "test-cookie")
        self.assertEqual(self.client.get("/owner", headers=headers).json(), {"id": str(self.uid)})
        self.sessions.find_one.assert_awaited_with({"token": "test-cookie"})

    def test_missing_invalid_and_expired_sessions(self):
        self.assertEqual(self.client.get("/owner").status_code, 401)
        self.sessions.find_one.assert_not_awaited()
        self.client.cookies.set(auth.SESSION_COOKIE_NAME, "test")
        for doc in [None, {}, {**self.session, "expires_at": "malformed"},
                    {**self.session, "user_id": "invalid"},
                    {**self.session, "expires_at": "2000-01-01T00:00:00+00:00"}]:
            with self.subTest(doc=doc):
                self.sessions.find_one.return_value = doc
                self.assertEqual(self.client.get("/owner").status_code, 401)
        self.sessions.delete_one.assert_awaited_once_with({"token": "test"})
        self.sessions.find_one.return_value = self.session
        self.users.find_one.return_value = None
        self.assertEqual(self.client.get("/owner").status_code, 401)

    def test_me_and_logout_contract(self):
        client = TestClient(api.app)
        self.addCleanup(client.close)
        self.assertEqual(client.get("/auth/me").json(), {"authenticated": False, "user": None})
        client.cookies.set(auth.SESSION_COOKIE_NAME, "test")
        profile = client.get("/auth/me")
        self.assertEqual(profile.json()["user"]["id"], str(self.uid))
        self.assertNotIn("password_hash", profile.json()["user"])
        self.assertNotIn("token", profile.json()["user"])
        self.assertEqual(profile.headers["cache-control"], "no-store")
        self.assertTrue(client.post("/auth/logout").json()["success"])
        self.sessions.delete_one.assert_awaited_once_with({"token": "test"})

    def test_password_login_and_register_cookie_and_token_modes(self):
        user = auth.sanitize_user(self.users.find_one.return_value)
        with patch.object(api, "register_user", new=AsyncMock(return_value=user)), \
             patch.object(api, "authenticate_user", new=AsyncMock(return_value=user)), \
             patch.object(api, "create_user_session", new=AsyncMock(return_value="issued")):
            client = TestClient(api.app, base_url="https://example.test")
            self.addCleanup(client.close)
            for path in ["/auth/register", "/auth/login"]:
                body = {"email": "gamer@example.com", "password": "sample-password"}
                self.assertEqual(client.post(path, json=body).json()["token"], "issued")
                response = client.post(path, json=body, headers={"X-Session-Mode": "cookie"})
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("token", response.json())
                self.assertNotIn("password_hash", response.json()["user"])
                for flag in ["HttpOnly", "Secure", "SameSite=lax"]:
                    self.assertIn(flag, response.headers["set-cookie"])
                self.assertEqual(response.headers["cache-control"], "no-store")

    def test_google_state_bound_to_cookie_and_consumed(self):
        user = {"id": str(self.uid)}
        with patch.object(auth, "GOOGLE_CLIENT_ID", "test"), patch.object(auth, "GOOGLE_CLIENT_SECRET", "test"), \
             patch.object(api, "handle_google_callback", new=AsyncMock(return_value=user)) as exchange, \
             patch.object(api, "create_user_session", new=AsyncMock(return_value="issued")):
            client = TestClient(api.app, base_url="https://example.test", follow_redirects=False)
            self.addCleanup(client.close)
            callback = "/auth/google/callback"
            client.get(callback, params={"code": "code"})
            exchange.assert_not_awaited()
            client.get("/auth/google/login")
            self.assertIn("auth_error", client.get(callback, params={"state": "wrong", "code": "code"}).headers["location"])
            exchange.assert_not_awaited()
            login = client.get("/auth/google/login")
            state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
            params = {"state": state, "code": "code"}
            self.assertIn("login_success", client.get(callback, params=params).headers["location"])
            self.assertIn("auth_error", client.get(callback, params=params).headers["location"])
            exchange.assert_awaited_once()

    def test_steam_callback_uses_existing_session_flow(self):
        client = TestClient(api.app, base_url="http://localhost", follow_redirects=False)
        self.addCleanup(client.close)
        with patch.object(auth, "FRONTEND_URL", "http://localhost"), \
             patch.object(api, "handle_steam_callback", new=AsyncMock(return_value={"id": str(self.uid)})), \
             patch.object(api, "create_user_session", new=AsyncMock(return_value="issued")):
            response = client.get("/auth/steam/callback")
        self.assertIn("login_success", response.headers["location"])
        self.assertNotIn("Secure", response.headers["set-cookie"])
        self.assertEqual(client.cookies.get(auth.SESSION_COOKIE_NAME), "issued")


class ActivityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.collection = AsyncMock()
        self.owner = auth.AuthenticatedUser(ObjectId())
        self.access = self.enterContext(patch.object(activity, "get_activity_collection",
                                                     new=AsyncMock(return_value=self.collection)))

    async def test_scoped_reads_and_idempotent_insert(self):
        records = {}

        def upsert(key, update, *, upsert, return_document):
            self.assertTrue(upsert)
            self.assertEqual(return_document, ReturnDocument.AFTER)
            self.assertEqual(set(update), {"$setOnInsert"})
            return records.setdefault((key["user_id"], key["appid"]), {**key, **update["$setOnInsert"]})

        self.collection.find_one_and_update.side_effect = upsert
        self.collection.find_one.side_effect = lambda key: records.get((key["user_id"], key["appid"]))
        other = auth.AuthenticatedUser(ObjectId())
        first = await activity.ensure_activity(self.owner, 304430)
        self.assertEqual(first["created_at"].tzinfo, timezone.utc)
        self.assertEqual(set(first), {"user_id", "appid", "created_at", "updated_at"})
        self.assertEqual(first, await activity.ensure_activity(self.owner, 304430))
        self.assertIsNone(await activity.get_activity(other, 304430))
        await activity.ensure_activity(other, 304430)
        await activity.ensure_activity(self.owner, 2596760)
        self.assertEqual(len(records), 3)
        self.assertEqual(first, await activity.get_activity(self.owner, 304430))

    async def test_reject_invalid_owner_and_appid_before_db(self):
        for appid in [0, -1, True, "304430", 304430.0, None, 999999999]:
            with self.subTest(appid=appid), self.assertRaises(ValueError):
                await activity.ensure_activity(self.owner, appid)
        with self.assertRaises(TypeError):
            await activity.ensure_activity({"id": str(self.owner.id)}, 304430)
        self.access.assert_not_awaited()

    async def test_duplicate_insert_race_reads_only_owner(self):
        self.collection.find_one_and_update.side_effect = DuplicateKeyError("duplicate")
        key = {"user_id": self.owner.id, "appid": 304430}
        self.collection.find_one.return_value = key
        self.assertEqual(await activity.ensure_activity(self.owner, 304430), key)
        self.collection.find_one.assert_awaited_once_with(key)

    async def test_index_initialization_and_failure(self):
        database = {name: AsyncMock() for name in ["users", "sessions", "user_game_activity"]}
        indexes = database["user_game_activity"].create_index
        with patch.object(db, "get_database", return_value=database), patch.object(db, "_activity_collection", None):
            indexes.side_effect = RuntimeError("index unavailable")
            with self.assertRaises(RuntimeError):
                await db.get_activity_collection()
            indexes.side_effect = None
            indexes.reset_mock()
            await db.init_db()
            self.assertIs(await db.get_activity_collection(), database["user_game_activity"])
            indexes.assert_awaited_once_with([("user_id", 1), ("appid", 1)], unique=True)
