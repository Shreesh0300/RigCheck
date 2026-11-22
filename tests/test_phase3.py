"""Phase 3 Integration & Unit Tests: User Preferences & AI History."""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from fastapi.testclient import TestClient

import app as api
import auth
import user_activity as activity


class Phase3BackendTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.user_a_id = ObjectId()
        self.user_b_id = ObjectId()
        self.owner_a = auth.AuthenticatedUser(self.user_a_id)
        self.owner_b = auth.AuthenticatedUser(self.user_b_id)

        # Mock collections
        self.ai_col = AsyncMock()
        self.users_mock = AsyncMock()

        self.enterContext(patch.object(activity, "get_ai_history_collection", new=AsyncMock(return_value=self.ai_col)))

        # In-memory store for ai_history
        self.ai_store = {}
        # In-memory store for users
        self.users_store = {
            self.user_a_id: {
                "_id": self.user_a_id,
                "email": "user_a@test.com",
                "preferred_genres": [],
                "interests": [],
                "onboarding_completed": False,
                "feed_revision": 1,
            },
            self.user_b_id: {
                "_id": self.user_b_id,
                "email": "user_b@test.com",
                "preferred_genres": ["Action"],
                "interests": ["multiplayer"],
                "onboarding_completed": True,
                "feed_revision": 2,
            },
        }

        # Wire users_col mock
        async def mock_users_find_one(filter_dict):
            uid = filter_dict.get("_id")
            return self.users_store.get(uid)

        async def mock_users_update_one(filter_dict, update_dict):
            uid = filter_dict.get("_id")
            doc = self.users_store.get(uid)
            if doc:
                if "$inc" in update_dict:
                    for k, v in update_dict["$inc"].items():
                        doc[k] = doc.get(k, 0) + v
                if "$set" in update_dict:
                    doc.update(update_dict["$set"])
            return MagicMock(modified_count=1 if doc else 0)

        async def mock_users_find_one_and_update(filter_dict, update_dict, *, return_document=None):
            uid = filter_dict.get("_id")
            doc = self.users_store.get(uid)
            if not doc:
                return None
            if "$inc" in update_dict:
                for k, v in update_dict["$inc"].items():
                    doc[k] = doc.get(k, 0) + v
            if "$set" in update_dict:
                doc.update(update_dict["$set"])
            return dict(doc)

        self.users_mock.find_one = mock_users_find_one
        self.users_mock.update_one = mock_users_update_one
        self.users_mock.find_one_and_update = mock_users_find_one_and_update

        # Wire ai_col mock
        async def mock_ai_insert_one(doc):
            doc_id = ObjectId()
            stored = dict(doc)
            stored["_id"] = doc_id
            self.ai_store[doc_id] = stored
            return MagicMock(inserted_id=doc_id)

        async def mock_ai_find_one(filter_dict, sort=None):
            uid = filter_dict.get("user_id")
            doc_id = filter_dict.get("_id")
            candidates = []
            for did, item in self.ai_store.items():
                if uid and item.get("user_id") != uid:
                    continue
                if doc_id and did != doc_id:
                    continue
                if "interactions" in filter_dict and "$elemMatch" in filter_dict["interactions"]:
                    elem = filter_dict["interactions"]["$elemMatch"]
                    matches_elem = any(
                        it.get("appid") == elem.get("appid") and it.get("action") == elem.get("action")
                        for it in item.get("interactions", [])
                    )
                    if not matches_elem:
                        continue
                if "$or" in filter_dict:
                    or_matched = False
                    for cond in filter_dict["$or"]:
                        for k, v in cond.items():
                            val = item.get(k)
                            if isinstance(val, list) and v in val:
                                or_matched = True
                            elif val == v:
                                or_matched = True
                    if not or_matched:
                        continue
                candidates.append(item)
            if not candidates:
                return None
            if sort:
                candidates.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
            return dict(candidates[0])

        def mock_ai_find(filter_dict):
            uid = filter_dict.get("user_id")
            results = [
                dict(item) for item in self.ai_store.values()
                if item.get("user_id") == uid
            ]
            cursor = MagicMock()
            cursor.sort = MagicMock(return_value=cursor)
            cursor.limit = MagicMock(return_value=cursor)
            async def to_list(length=100):
                res = list(results)
                res.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
                return res[:length]
            cursor.to_list = to_list
            return cursor

        async def mock_ai_update_one(filter_dict, update_dict):
            did = filter_dict.get("_id")
            doc = self.ai_store.get(did)
            if not doc:
                return MagicMock(modified_count=0)
            if "$push" in update_dict:
                for k, v in update_dict["$push"].items():
                    doc.setdefault(k, []).append(v)
            if "$set" in update_dict:
                for k, v in update_dict["$set"].items():
                    if k.startswith("interactions.$."):
                        field = k.split("interactions.$.")[1]
                        elem = filter_dict.get("interactions", {}).get("$elemMatch", {})
                        for it in doc.get("interactions", []):
                            if it.get("appid") == elem.get("appid") and it.get("action") == elem.get("action"):
                                it[field] = v
                    else:
                        doc[k] = v
            return MagicMock(modified_count=1)

        async def mock_ai_delete_one(filter_dict):
            did = filter_dict.get("_id")
            uid = filter_dict.get("user_id")
            doc = self.ai_store.get(did)
            if doc and doc.get("user_id") == uid:
                del self.ai_store[did]
                return MagicMock(deleted_count=1)
            return MagicMock(deleted_count=0)

        async def mock_ai_delete_many(filter_dict):
            uid = filter_dict.get("user_id")
            to_delete = [did for did, item in self.ai_store.items() if item.get("user_id") == uid]
            for did in to_delete:
                del self.ai_store[did]
            return MagicMock(deleted_count=len(to_delete))

        self.ai_col.insert_one = mock_ai_insert_one
        self.ai_col.find_one = mock_ai_find_one
        self.ai_col.find = mock_ai_find
        self.ai_col.update_one = mock_ai_update_one
        self.ai_col.delete_one = mock_ai_delete_one
        self.ai_col.delete_many = mock_ai_delete_many

        self.enterContext(patch.object(activity, "get_database", return_value={"users": self.users_mock}))

    async def test_get_and_update_preferences(self):
        # Initial preferences
        prefs_a = await activity.get_user_preferences(self.owner_a)
        self.assertEqual(prefs_a["preferred_genres"], [])
        self.assertFalse(prefs_a["onboarding_completed"])
        self.assertEqual(prefs_a["feed_revision"], 1)

        # Update preferences
        updated = await activity.update_user_preferences(
            self.owner_a,
            preferred_genres=["RPG", "<b>Action</b>", "RPG"],  # Sanitizes tags and deduplicates
            interests=["Open World", "story rich"],
            onboarding_completed=True,
        )
        self.assertEqual(updated["preferred_genres"], ["RPG", "Action"])
        self.assertEqual(updated["interests"], ["Open World", "story rich"])
        self.assertTrue(updated["onboarding_completed"])
        self.assertGreater(updated["feed_revision"], 1)

    async def test_record_ai_query_and_retrieval(self):
        # 304430 is a valid catalog App ID (INSIDE)
        query_doc = await activity.record_ai_query(
            self.owner_a,
            query="dark moody puzzle adventure",
            recommended_appid=304430,
            alternative_appids=[105600],  # Terraria
            budget=2000,
            gpu_name="RTX 3060",
            ram=16,
        )
        self.assertIn("id", query_doc)
        self.assertEqual(query_doc["recommended_appid"], 304430)
        self.assertIn(105600, query_doc["alternative_appids"])

        history = await activity.get_user_ai_history(self.owner_a)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["query"], "dark moody puzzle adventure")
        self.assertEqual(history[0]["recommended_game"]["appid"], 304430)

    async def test_interaction_tracking_and_deduplication(self):
        # Record query
        q = await activity.record_ai_query(
            self.owner_a,
            query="atmospheric puzzle",
            recommended_appid=304430,
            alternative_appids=[105600],
        )
        query_id = q["id"]

        # Track first click
        first_click = await activity.record_ai_interaction(
            self.owner_a,
            appid=304430,
            action="click",
            query_id=query_id,
        )
        self.assertTrue(first_click["success"])
        self.assertFalse(first_click["deduplicated"])

        # Track repeated click on same game (must be deduplicated)
        second_click = await activity.record_ai_interaction(
            self.owner_a,
            appid=304430,
            action="click",
            query_id=query_id,
        )
        self.assertTrue(second_click["success"])
        self.assertTrue(second_click["deduplicated"])

        # Track different action on same game (favourite) -> new interaction entry
        fav_act = await activity.record_ai_interaction(
            self.owner_a,
            appid=304430,
            action="favourite",
            query_id=query_id,
        )
        self.assertTrue(fav_act["success"])
        self.assertFalse(fav_act["deduplicated"])

        history = await activity.get_user_ai_history(self.owner_a)
        interactions = history[0]["interactions"]
        self.assertEqual(len(interactions), 2)  # 1 click and 1 favourite, NOT 2 clicks

    async def test_cross_user_isolation_and_deletion(self):
        # User A records query
        qa = await activity.record_ai_query(self.owner_a, query="User A query", recommended_appid=304430)
        # User B records query
        qb = await activity.record_ai_query(self.owner_b, query="User B query", recommended_appid=105600)

        # User A attempts to delete User B's query -> must fail to delete
        res = await activity.delete_user_ai_history(self.owner_a, query_id=qb["id"])
        self.assertEqual(res["deleted_count"], 0)

        # User B still has their query intact
        hb = await activity.get_user_ai_history(self.owner_b)
        self.assertEqual(len(hb), 1)

        # User A deletes their own query
        res_a = await activity.delete_user_ai_history(self.owner_a, query_id=qa["id"])
        self.assertEqual(res_a["deleted_count"], 1)

        ha = await activity.get_user_ai_history(self.owner_a)
        self.assertEqual(len(ha), 0)


class Phase3ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.addCleanup(self.client.close)
        self.uid = ObjectId()
        self.user = {
            "id": str(self.uid),
            "email": "tester@example.com",
            "display_name": "Tester",
            "preferred_genres": ["Action"],
            "interests": ["RPG"],
            "onboarding_completed": True,
            "feed_revision": 3,
        }

        self.users_mock = AsyncMock()
        self.sessions_mock = AsyncMock()
        self.users_mock.find_one.return_value = {
            "_id": self.uid,
            "email": "tester@example.com",
            "preferred_genres": ["Action"],
            "interests": ["RPG"],
            "onboarding_completed": True,
            "feed_revision": 3,
        }
        self.sessions_mock.find_one.return_value = {
            "token": "valid-token",
            "user_id": str(self.uid),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        self.enterContext(patch.object(auth, "get_database", return_value={
            "users": self.users_mock, "sessions": self.sessions_mock
        }))
        self.enterContext(patch.object(activity, "get_database", return_value={
            "users": self.users_mock, "sessions": self.sessions_mock
        }))

    def test_preferences_api_authentication_and_csrf(self):
        # Unauthenticated GET
        r1 = self.client.get("/api/preferences")
        self.assertEqual(r1.status_code, 401)

        # Authenticated GET
        cookies = {"rigcheck_session": "valid-token"}
        r2 = self.client.get("/api/preferences", cookies=cookies)
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()["success"])

        # PUT without CSRF token -> 403
        r3 = self.client.put(
            "/api/preferences",
            json={"preferred_genres": ["Indie"]},
            cookies=cookies,
        )
        self.assertEqual(r3.status_code, 403)

        # PUT with valid CSRF
        cookies_with_csrf = {
            "rigcheck_session": "valid-token",
            "rigcheck_csrf": "valid-csrf-token",
        }
        headers = {"X-CSRF-Token": "valid-csrf-token"}
        with patch.object(api, "update_user_preferences", new=AsyncMock(return_value={
            "preferred_genres": ["Indie"],
            "interests": ["Story Rich"],
            "onboarding_completed": True,
            "feed_revision": 4,
        })):
            r4 = self.client.put(
                "/api/preferences",
                json={"preferred_genres": ["Indie"], "interests": ["Story Rich"]},
                cookies=cookies_with_csrf,
                headers=headers,
            )
            self.assertEqual(r4.status_code, 200)
            self.assertEqual(r4.json()["preferences"]["preferred_genres"], ["Indie"])

    def test_ai_history_api(self):
        cookies_with_csrf = {
            "rigcheck_session": "valid-token",
            "rigcheck_csrf": "valid-csrf-token",
        }
        headers = {"X-CSRF-Token": "valid-csrf-token"}

        # GET history
        with patch.object(api, "get_user_ai_history", new=AsyncMock(return_value=[
            {"id": "60c72b2f9b1d8b2bad000001", "query": "space shooter", "timestamp": "2026-11-22T00:00:00Z"}
        ])):
            r_get = self.client.get("/api/ai-history", cookies=cookies_with_csrf)
            self.assertEqual(r_get.status_code, 200)
            self.assertEqual(len(r_get.json()["history"]), 1)

        # DELETE single item
        with patch.object(api, "delete_user_ai_history", new=AsyncMock(return_value={"deleted_count": 1})):
            r_del = self.client.delete(
                "/api/ai-history/60c72b2f9b1d8b2bad000001",
                cookies=cookies_with_csrf,
                headers=headers,
            )
            self.assertEqual(r_del.status_code, 200)

        # Log interaction
        with patch.object(api, "record_ai_interaction", new=AsyncMock(return_value={"success": True, "deduplicated": False})):
            r_act = self.client.post(
                "/api/ai-history/interaction",
                json={"appid": 304430, "action": "click"},
                cookies=cookies_with_csrf,
                headers=headers,
            )
            self.assertEqual(r_act.status_code, 200)
            self.assertTrue(r_act.json()["interaction"]["success"])

    def test_recommend_route_logging_behavior(self):
        # 1. Unauthenticated request to /recommend
        payload = {
            "description": "dark atmospheric indie puzzle game",
            "budget": 2000,
            "gpu_name": "GTX 1650",
            "ram": 8,
        }
        res_unauth = self.client.post("/recommend", json=payload)
        self.assertEqual(res_unauth.status_code, 200)
        self.assertIn("recommended_game", res_unauth.json())
        self.assertNotIn("query_id", res_unauth.json())

        # 2. Authenticated request to /recommend
        cookies = {"rigcheck_session": "valid-token"}
        with patch.object(api, "record_ai_query", new=AsyncMock(return_value={"id": "mock_query_id_123"})) as mock_rec:
            res_auth = self.client.post("/recommend", json=payload, cookies=cookies)
            self.assertEqual(res_auth.status_code, 200)
            self.assertIn("recommended_game", res_auth.json())
            self.assertEqual(res_auth.json().get("query_id"), "mock_query_id_123")
            mock_rec.assert_called_once()


if __name__ == "__main__":
    unittest.main()
