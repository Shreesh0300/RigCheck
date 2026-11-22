"""Stage 2A Integration & Unit Tests: Personal Game Library Backend."""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from fastapi.testclient import TestClient

import app as api
import auth
import user_activity as activity


class Stage2ABackendTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.user_a_id = ObjectId()
        self.user_b_id = ObjectId()
        self.owner_a = auth.AuthenticatedUser(self.user_a_id)
        self.owner_b = auth.AuthenticatedUser(self.user_b_id)

        # Mock MongoDB activity collection
        self.collection = AsyncMock()
        self.enterContext(patch.object(activity, "get_activity_collection", new=AsyncMock(return_value=self.collection)))

        # In-memory store for activity collection simulation
        self.store = {}

        async def mock_find_one(filter_dict):
            key = (str(filter_dict.get("user_id")), filter_dict.get("appid"))
            return self.store.get(key)

        async def mock_find_one_and_update(filter_dict, update_dict, *, upsert=False, return_document=None):
            key = (str(filter_dict.get("user_id")), filter_dict.get("appid"))
            doc = self.store.get(key)
            if doc is None:
                if upsert:
                    doc = {**filter_dict, **update_dict.get("$setOnInsert", {})}
                    self.store[key] = doc
                    return doc
                return None
            if "$set" in update_dict:
                doc.update(update_dict["$set"])
            return doc

        def mock_find(filter_dict):
            results = []
            uid = str(filter_dict.get("user_id"))
            for (k_uid, _), doc in self.store.items():
                if k_uid != uid:
                    continue
                match = True
                for field in ["is_favourite", "want_to_play", "already_played"]:
                    if field in filter_dict and doc.get(field) != filter_dict[field]:
                        match = False
                        break
                if "$or" in filter_dict:
                    or_match = False
                    for condition in filter_dict["$or"]:
                        for cond_k, cond_v in condition.items():
                            if doc.get(cond_k) == cond_v:
                                or_match = True
                                break
                    if not or_match:
                        match = False
                if match:
                    results.append(doc)

            cursor_mock = MagicMock()
            cursor_mock.sort.return_value = cursor_mock
            cursor_mock.to_list = AsyncMock(return_value=results)
            return cursor_mock

        self.collection.find_one.side_effect = mock_find_one
        self.collection.find_one_and_update.side_effect = mock_find_one_and_update
        self.collection.find = mock_find

    async def test_three_independent_states_and_multiple_categories(self):
        # 1. Add to Favourite (INSIDE appid 304430)
        doc1 = await activity.update_library_state(self.owner_a, 304430, is_favourite=True)
        self.assertTrue(doc1["is_favourite"])
        self.assertFalse(doc1["want_to_play"])
        self.assertFalse(doc1["already_played"])
        t1 = doc1["updated_at"]

        # 2. Add to Already Played simultaneously
        doc2 = await activity.update_library_state(self.owner_a, 304430, already_played=True)
        self.assertTrue(doc2["is_favourite"])
        self.assertTrue(doc2["already_played"])
        self.assertFalse(doc2["want_to_play"])
        t2 = doc2["updated_at"]
        self.assertGreaterEqual(t2, t1)

        # 3. Add to Want to Play simultaneously
        doc3 = await activity.update_library_state(self.owner_a, 304430, want_to_play=True)
        self.assertTrue(doc3["is_favourite"])
        self.assertTrue(doc3["already_played"])
        self.assertTrue(doc3["want_to_play"])

        # 4. Remove from Favourite only
        doc4 = await activity.remove_library_state(self.owner_a, 304430, category="favourite")
        self.assertFalse(doc4["is_favourite"])
        self.assertTrue(doc4["already_played"])
        self.assertTrue(doc4["want_to_play"])

    async def test_effective_change_only_advances_updated_at(self):
        doc = await activity.update_library_state(self.owner_a, 304430, is_favourite=True)
        initial_updated_at = doc["updated_at"]
        initial_created_at = doc["created_at"]

        # Ineffective change: same state
        doc_same = await activity.update_library_state(self.owner_a, 304430, is_favourite=True)
        self.assertEqual(doc_same["updated_at"], initial_updated_at)
        self.assertEqual(doc_same["created_at"], initial_created_at)

        # Effective change: change state
        doc_diff = await activity.update_library_state(self.owner_a, 304430, want_to_play=True)
        self.assertEqual(doc_diff["created_at"], initial_created_at)
        self.assertGreaterEqual(doc_diff["updated_at"], initial_updated_at)

    async def test_user_data_isolation(self):
        await activity.update_library_state(self.owner_a, 304430, is_favourite=True)
        await activity.update_library_state(self.owner_b, 304430, want_to_play=True)

        lib_a = await activity.get_user_library(self.owner_a)
        lib_b = await activity.get_user_library(self.owner_b)

        self.assertEqual(len(lib_a), 1)
        self.assertEqual(len(lib_b), 1)
        self.assertTrue(lib_a[0]["is_favourite"])
        self.assertFalse(lib_a[0]["want_to_play"])
        self.assertFalse(lib_b[0]["is_favourite"])
        self.assertTrue(lib_b[0]["want_to_play"])

    async def test_reject_invalid_appid(self):
        with self.assertRaises(ValueError):
            await activity.update_library_state(self.owner_a, 999999999, is_favourite=True)


class Stage2AApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.addCleanup(self.client.close)
        self.uid = ObjectId()
        self.user = {"id": str(self.uid), "email": "tester@example.com", "display_name": "Tester"}

        self.users_mock = AsyncMock()
        self.sessions_mock = AsyncMock()
        self.users_mock.find_one.return_value = {"_id": self.uid, "email": "tester@example.com"}
        self.sessions_mock.find_one.return_value = {
            "token": "valid-token",
            "user_id": str(self.uid),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        }
        self.enterContext(patch.object(auth, "get_database", return_value={
            "users": self.users_mock, "sessions": self.sessions_mock
        }))

    def test_unauthenticated_requests_fail(self):
        # GET /api/library without credentials -> 401
        res = self.client.get("/api/library")
        self.assertEqual(res.status_code, 401)

        # PUT /api/library/304430 without credentials -> 401
        res = self.client.put("/api/library/304430", json={"is_favourite": True})
        self.assertEqual(res.status_code, 401)

    def test_csrf_protection_for_cookie_auth(self):
        # Request with session cookie but missing CSRF token -> 403 Forbidden
        self.client.cookies.set(auth.SESSION_COOKIE_NAME, "valid-token")
        res = self.client.put("/api/library/304430", json={"is_favourite": True})
        self.assertEqual(res.status_code, 403)
        self.assertIn("CSRF", res.json()["detail"])

        # Request with session cookie and mismatched CSRF token -> 403 Forbidden
        self.client.cookies.set(auth.CSRF_COOKIE_NAME, "token-a")
        res = self.client.put("/api/library/304430", json={"is_favourite": True}, headers={"X-CSRF-Token": "token-b"})
        self.assertEqual(res.status_code, 403)

        # Request with session cookie and valid CSRF token -> 200 OK
        with patch.object(api, "update_library_state", new=AsyncMock(return_value={
            "appid": 304430, "is_favourite": True, "want_to_play": False, "already_played": False
        })):
            res = self.client.put(
                "/api/library/304430",
                json={"is_favourite": True},
                headers={"X-CSRF-Token": "token-a"}
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json()["state"]["is_favourite"])

    def test_bearer_token_bypasses_csrf(self):
        # Bearer token does not require CSRF token
        with patch.object(api, "update_library_state", new=AsyncMock(return_value={
            "appid": 304430, "is_favourite": True, "want_to_play": False, "already_played": False
        })):
            res = self.client.put(
                "/api/library/304430",
                json={"is_favourite": True},
                headers={"Authorization": "Bearer valid-token"}
            )
            self.assertEqual(res.status_code, 200)

    def test_nonexistent_catalog_game_returns_404(self):
        headers = {"Authorization": "Bearer valid-token"}
        res = self.client.get("/api/library/99999999", headers=headers)
        self.assertEqual(res.status_code, 404)

        res = self.client.put("/api/library/99999999", json={"is_favourite": True}, headers=headers)
        self.assertEqual(res.status_code, 404)

    def test_delete_library_endpoints(self):
        headers = {"Authorization": "Bearer valid-token"}
        with patch.object(api, "remove_library_state", new=AsyncMock(return_value={
            "appid": 304430, "is_favourite": False, "want_to_play": False, "already_played": False
        })) as mock_remove:
            # DELETE /api/library/304430
            res = self.client.delete("/api/library/304430", headers=headers)
            self.assertEqual(res.status_code, 200)
            mock_remove.assert_awaited_with(user=auth.AuthenticatedUser(self.uid), appid=304430, category=None)

            # DELETE /api/library/304430/favourite
            res = self.client.delete("/api/library/304430/favourite", headers=headers)
            self.assertEqual(res.status_code, 200)
            mock_remove.assert_awaited_with(user=auth.AuthenticatedUser(self.uid), appid=304430, category="favourite")
