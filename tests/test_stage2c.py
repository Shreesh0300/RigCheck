"""Stage 2C Integration & Unit Tests: Ratings & Public Reviews."""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from fastapi.testclient import TestClient

import app as api
import auth
import user_activity as activity


class Stage2CBackendTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.user_a_id = ObjectId()
        self.user_b_id = ObjectId()
        self.owner_a = auth.AuthenticatedUser(self.user_a_id)
        self.owner_b = auth.AuthenticatedUser(self.user_b_id)

        self.collection = AsyncMock()
        self.enterContext(patch.object(activity, "get_activity_collection", new=AsyncMock(return_value=self.collection)))

        self.store = {}

        async def mock_find_one(filter_dict):
            uid = str(filter_dict.get("user_id"))
            appid = filter_dict.get("appid")
            return self.store.get((uid, appid))

        async def mock_find_one_and_update(filter_dict, update_dict, *, upsert=False, return_document=None):
            uid = str(filter_dict.get("user_id"))
            appid = filter_dict.get("appid")
            key = (uid, appid)
            doc = self.store.get(key)
            if doc is None:
                if upsert:
                    doc = {**filter_dict, **update_dict.get("$setOnInsert", {})}
                    self.store[key] = doc
                    return doc
                return None
            if "$set" in update_dict:
                doc.update(update_dict["$set"])
            if "$inc" in update_dict:
                for inc_k, inc_v in update_dict["$inc"].items():
                    doc[inc_k] = doc.get(inc_k, 0) + inc_v
            return doc

        def mock_find(filter_dict):
            results = []
            target_appid = filter_dict.get("appid")
            for (_, appid), doc in self.store.items():
                if appid != target_appid:
                    continue
                if filter_dict.get("is_hidden") == {"$ne": True} and doc.get("is_hidden") is True:
                    continue
                if doc.get("rating") is not None:
                    results.append(doc)

            cursor = MagicMock()
            cursor.sort.return_value = cursor
            cursor.to_list = AsyncMock(return_value=results)
            return cursor

        self.collection.find_one.side_effect = mock_find_one
        self.collection.find_one_and_update.side_effect = mock_find_one_and_update
        self.collection.find = mock_find

    async def test_rating_validation_and_sanitization(self):
        # Invalid ratings
        for r in [0, 11, -1, 15, "8", None]:
            with self.subTest(rating=r), self.assertRaises(ValueError):
                await activity.submit_review(self.owner_a, 304430, rating=r)

        # Valid rating with HTML in comment
        raw_comment = "<script>alert('xss')</script><b>Incredible game!</b>"
        doc = await activity.submit_review(self.owner_a, 304430, rating=9, review_text=raw_comment)
        self.assertEqual(doc["rating"], 9)
        self.assertNotIn("<script>", doc["review_text"])
        self.assertIn("Incredible game!", doc["review_text"])
        self.assertTrue(doc["already_played"])

    async def test_single_active_review_per_user_and_edit(self):
        # First submission
        doc1 = await activity.submit_review(self.owner_a, 304430, rating=8, review_text="Good game")
        self.assertEqual(doc1["rating"], 8)
        created_at = doc1["review_created_at"]

        # Second submission overwrites and updates existing review (only one active review per user per game)
        doc2 = await activity.submit_review(self.owner_a, 304430, rating=10, review_text="Masterpiece upon replay")
        self.assertEqual(doc2["rating"], 10)
        self.assertEqual(doc2["review_text"], "Masterpiece upon replay")
        self.assertEqual(doc2["review_created_at"], created_at)
        self.assertGreaterEqual(doc2["review_updated_at"], created_at)

        # Total documents for this user and game is strictly 1
        self.assertEqual(len(self.store), 1)

    async def test_delete_own_review_preserves_activity(self):
        # User marks as favourite, played, and rates
        await activity.update_library_state(self.owner_a, 304430, is_favourite=True)
        await activity.submit_review(self.owner_a, 304430, rating=9, review_text="Awesome")

        doc = self.store.get((str(self.owner_a.id), 304430))
        self.assertTrue(doc["is_favourite"])
        self.assertEqual(doc["rating"], 9)

        # Delete review
        updated = await activity.delete_user_review(self.owner_a, 304430)
        self.assertIsNone(updated["rating"])
        self.assertIsNone(updated["review_text"])
        # Preserves favourite and played status
        self.assertTrue(updated["is_favourite"])
        self.assertTrue(updated["already_played"])

    async def test_already_played_does_not_auto_rate(self):
        # Marking game as already_played
        doc = await activity.update_library_state(self.owner_a, 304430, already_played=True)
        self.assertTrue(doc["already_played"])
        self.assertIsNone(doc.get("rating"))

    async def test_public_reviews_average_and_moderation_reporting(self):
        # User A rates 8
        await activity.submit_review(self.owner_a, 304430, rating=8, review_text="Solid 8")
        # User B rates 10
        await activity.submit_review(self.owner_b, 304430, rating=10, review_text="Perfect 10")

        # Mock database user lookup
        users_mock = MagicMock()
        user_cursor = MagicMock()
        user_cursor.to_list = AsyncMock(return_value=[
            {"_id": self.user_a_id, "display_name": "Alice", "avatar": None},
            {"_id": self.user_b_id, "display_name": "Bob", "avatar": None},
        ])
        users_mock.find.return_value = user_cursor
        with patch.object(activity, "get_database", return_value={"users": users_mock}):
            data = await activity.get_public_reviews(304430)
            self.assertEqual(data["average_rating"], 9.0)
            self.assertEqual(data["total_ratings"], 2)
            self.assertEqual(data["total_reviews"], 2)

            # Reporting safeguards: User A reports User B
            res = await activity.report_public_review(self.owner_a, 304430, str(self.user_b_id))
            self.assertTrue(res["reported"])
            self.assertFalse(res["is_hidden"])  # 1 report: not hidden yet

            # Self-reporting is prohibited
            with self.assertRaises(ValueError):
                await activity.report_public_review(self.owner_a, 304430, str(self.user_a_id))

            # Additional reports trigger moderation threshold (>= 3 reports)
            other_c = auth.AuthenticatedUser(ObjectId())
            other_d = auth.AuthenticatedUser(ObjectId())
            await activity.report_public_review(other_c, 304430, str(self.user_b_id))
            res3 = await activity.report_public_review(other_d, 304430, str(self.user_b_id))
            self.assertTrue(res3["is_hidden"])

            # Hidden review is excluded from public reviews
            data_after = await activity.get_public_reviews(304430)
            self.assertEqual(data_after["total_ratings"], 1)
            self.assertEqual(data_after["average_rating"], 8.0)


class Stage2CApiTests(unittest.TestCase):
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

    def test_public_reviews_accessible_without_auth(self):
        with patch.object(api, "get_public_reviews", new=AsyncMock(return_value={
            "appid": 304430, "average_rating": 8.5, "total_ratings": 4, "total_reviews": 2, "reviews": []
        })):
            res = self.client.get("/api/games/304430/reviews")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["average_rating"], 8.5)

    def test_submit_review_requires_auth_and_csrf(self):
        # 1. No auth -> 401
        res = self.client.put("/api/games/304430/review", json={"rating": 8})
        self.assertEqual(res.status_code, 401)

        # 2. Cookie auth without CSRF -> 403
        self.client.cookies.set(auth.SESSION_COOKIE_NAME, "valid-token")
        res = self.client.put("/api/games/304430/review", json={"rating": 8})
        self.assertEqual(res.status_code, 403)

        # 3. Cookie auth with valid CSRF -> 200
        self.client.cookies.set(auth.CSRF_COOKIE_NAME, "csrf-test")
        with patch.object(api, "submit_review", new=AsyncMock(return_value={
            "appid": 304430, "rating": 8, "review_text": "Nice", "already_played": True
        })):
            res = self.client.put(
                "/api/games/304430/review",
                json={"rating": 8, "comment": "Nice"},
                headers={"X-CSRF-Token": "csrf-test"}
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["state"]["rating"], 8)

    def test_delete_review_api(self):
        headers = {"Authorization": "Bearer valid-token"}
        with patch.object(api, "delete_user_review", new=AsyncMock(return_value={
            "appid": 304430, "rating": None, "review_text": None, "already_played": True
        })):
            res = self.client.delete("/api/games/304430/review", headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertIsNone(res.json()["state"]["rating"])

    def test_report_review_api(self):
        headers = {"Authorization": "Bearer valid-token"}
        target_uid = str(ObjectId())
        with patch.object(api, "report_public_review", new=AsyncMock(return_value={
            "success": True, "reported": True, "is_hidden": False, "report_count": 1
        })):
            res = self.client.post(
                "/api/games/304430/reviews/report",
                json={"target_user_id": target_uid, "reason": "Spam"},
                headers=headers
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json()["reported"])
