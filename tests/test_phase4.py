"""Phase 4 Integration & Unit Tests: Personalized Recommendation Engine."""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from fastapi.testclient import TestClient

import app as api
import auth
import user_activity as activity
from model.personalized_engine import generate_personalized_feed
from model.steam_database import get_game_by_appid


class Phase4RecommendationEngineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.new_user_id = ObjectId()
        self.rpg_user_id = ObjectId()
        self.racing_user_id = ObjectId()

        self.owner_new = auth.AuthenticatedUser(self.new_user_id)
        self.owner_rpg = auth.AuthenticatedUser(self.rpg_user_id)
        self.owner_racing = auth.AuthenticatedUser(self.racing_user_id)

        self.users_mock = AsyncMock()
        self.activity_mock = AsyncMock()
        self.ai_mock = AsyncMock()

        self.enterContext(patch("model.personalized_engine.get_activity_collection", new=AsyncMock(return_value=self.activity_mock)))
        self.enterContext(patch("model.personalized_engine.get_user_preferences", new=self.mock_get_user_preferences))
        self.enterContext(patch("model.personalized_engine.get_user_ai_history", new=self.mock_get_user_ai_history))

        # In-memory stores
        self.users_store = {
            self.new_user_id: {
                "_id": self.new_user_id,
                "preferred_genres": [],
                "interests": [],
                "feed_revision": 1,
            },
            self.rpg_user_id: {
                "_id": self.rpg_user_id,
                "preferred_genres": ["RPG", "Adventure"],
                "interests": ["story rich", "open world"],
                "feed_revision": 2,
            },
            self.racing_user_id: {
                "_id": self.racing_user_id,
                "preferred_genres": ["Racing", "Simulation"],
                "interests": ["driving"],
                "feed_revision": 2,
            },
        }

        self.activities_store = {
            # RPG user favourited Skyrim (72850) and played + rated The Witcher 3 (292030) a 10/10
            # Also played and hated a casual puzzle game (rated 1/10)
            self.rpg_user_id: [
                {
                    "user_id": self.rpg_user_id,
                    "appid": 72850,  # Skyrim
                    "is_favourite": True,
                    "want_to_play": False,
                    "already_played": False,
                    "rating": None,
                },
                {
                    "user_id": self.rpg_user_id,
                    "appid": 292030,  # The Witcher 3
                    "is_favourite": False,
                    "want_to_play": False,
                    "already_played": True,
                    "rating": 10,
                    "review_text": "Peak RPG",
                },
                {
                    "user_id": self.rpg_user_id,
                    "appid": 304430,  # INSIDE (marked already played)
                    "is_favourite": False,
                    "want_to_play": False,
                    "already_played": True,
                    "rating": 9,
                },
            ],
            # Racing user favourited Forza Horizon 5 (1551360) and want to play DiRT Rally 2.0 (690790)
            self.racing_user_id: [
                {
                    "user_id": self.racing_user_id,
                    "appid": 1551360,  # Forza Horizon 5
                    "is_favourite": True,
                    "want_to_play": False,
                    "already_played": False,
                    "rating": None,
                },
                {
                    "user_id": self.racing_user_id,
                    "appid": 690790,  # DiRT Rally 2.0
                    "is_favourite": False,
                    "want_to_play": True,
                    "already_played": False,
                    "rating": None,
                },
            ],
            self.new_user_id: [],
        }

        self.ai_store = {
            self.rpg_user_id: [
                {"query": "deep story rich fantasy rpg with swords", "interactions": []}
            ],
            self.racing_user_id: [
                {"query": "best realistic racing sim with steering wheel", "interactions": []}
            ],
            self.new_user_id: [],
        }

        def mock_find(filter_dict):
            uid = filter_dict.get("user_id")
            items = self.activities_store.get(uid, [])
            cursor = MagicMock()
            async def to_list(length=1000):
                return list(items)[:length]
            cursor.to_list = to_list
            return cursor

        self.activity_mock.find = mock_find

    async def mock_get_user_preferences(self, user):
        u = self.users_store.get(user.id, {})
        return {
            "preferred_genres": u.get("preferred_genres", []),
            "interests": u.get("interests", []),
            "feed_revision": u.get("feed_revision", 1),
        }

    async def mock_get_user_ai_history(self, user, limit=25):
        return self.ai_store.get(user.id, [])

    async def test_cold_start_recommendations_for_new_user(self):
        feed = await generate_personalized_feed(self.owner_new, limit=10)
        self.assertTrue(feed["success"])
        self.assertTrue(feed["is_cold_start"])
        recs = feed["recommendations"]
        self.assertEqual(len(recs), 10)
        self.assertEqual(len(feed["already_played_recommendations"]), 0)

        # Confirm diversity in cold start: multiple different genres
        genres_seen = set()
        for g in recs:
            for genre in g.get("genres", []):
                genres_seen.add(genre)
        self.assertGreaterEqual(len(genres_seen), 3)

    async def test_different_users_get_distinct_tailored_recommendations(self):
        rpg_feed = await generate_personalized_feed(self.owner_rpg, limit=10)
        racing_feed = await generate_personalized_feed(self.owner_racing, limit=10)

        rpg_appids = {r["appid"] for r in rpg_feed["recommendations"]}
        racing_appids = {r["appid"] for r in racing_feed["recommendations"]}

        # Overlap in top 10 recommendations between RPG lover and Racing lover must be minimal or zero
        common = rpg_appids.intersection(racing_appids)
        self.assertLessEqual(len(common), 2, f"Expected minimal overlap between RPG and Racing users, got {common}")

        # RPG recommendations should match RPG / Adventure / Story
        rpg_genres = [genre.lower() for r in rpg_feed["recommendations"] for genre in r.get("genres", [])]
        self.assertTrue(any("rpg" in g or "adventure" in g or "action" in g for g in rpg_genres))

        # Racing recommendations should heavily feature Racing / Sports / Simulation
        racing_genres = [genre.lower() for r in racing_feed["recommendations"] for genre in r.get("genres", [])]
        self.assertTrue(any("racing" in g or "simulation" in g or "sports" in g for g in racing_genres))

    async def test_already_played_games_strictly_excluded_from_main_feed(self):
        # RPG user has already played The Witcher 3 (292030) and INSIDE (304430)
        feed = await generate_personalized_feed(self.owner_rpg, limit=20)
        main_recs_appids = [r["appid"] for r in feed["recommendations"]]

        self.assertNotIn(292030, main_recs_appids, "Already played game (Witcher 3) must be excluded from main feed")
        self.assertNotIn(304430, main_recs_appids, "Already played game (INSIDE) must be excluded from main feed")

        # Must be present in already_played_recommendations section
        already_played_appids = [r["appid"] for r in feed["already_played_recommendations"]]
        self.assertIn(292030, already_played_appids)
        self.assertIn(304430, already_played_appids)

        # Ranked with highest rating first (Witcher 3 rated 10 should precede INSIDE rated 9)
        self.assertEqual(already_played_appids[0], 292030)
        self.assertEqual(feed["already_played_recommendations"][0]["rating"], 10)

    async def test_favourited_games_excluded_from_main_feed(self):
        # RPG user favourited Skyrim (72850)
        feed = await generate_personalized_feed(self.owner_rpg, limit=20)
        main_recs_appids = [r["appid"] for r in feed["recommendations"]]
        self.assertNotIn(72850, main_recs_appids, "Favourited game (Skyrim) must not be recommended back to user")

    async def test_meaningful_explanations(self):
        feed = await generate_personalized_feed(self.owner_rpg, limit=10)
        for r in feed["recommendations"]:
            exp = r.get("explanation")
            self.assertIsInstance(exp, str)
            self.assertGreater(len(exp), 5)
            # Should have meaningful contextual strings
            self.assertTrue(any(phrase in exp for phrase in [
                "Because you", "Similar to", "Matches your", "Based on", "Popular in", "Recommended"
            ]), f"Unexpected explanation format: {exp}")

    async def test_negative_rating_penalty(self):
        # User rates a Horror game 1/10
        user_dislike_horror = auth.AuthenticatedUser(ObjectId())
        self.activities_store[user_dislike_horror.id] = [
            {
                "user_id": user_dislike_horror.id,
                "appid": 304430,  # INSIDE (indie, atmospheric)
                "is_favourite": True,
                "want_to_play": False,
                "already_played": False,
                "rating": None,
            },
            {
                "user_id": user_dislike_horror.id,
                "appid": 2050650,  # Resident Evil 4 or horror game
                "is_favourite": False,
                "want_to_play": False,
                "already_played": True,
                "rating": 1,  # Hated it
                "review_text": "Too terrifying, hated it",
            }
        ]
        self.users_store[user_dislike_horror.id] = {
            "_id": user_dislike_horror.id,
            "preferred_genres": ["Indie"],
            "interests": [],
            "feed_revision": 1,
        }

        feed = await generate_personalized_feed(user_dislike_horror, limit=10)
        # Main feed should favor Indie and avoid Horror
        top_recs = feed["recommendations"][:5]
        for r in top_recs:
            self.assertNotIn(2050650, [r["appid"]])


class Phase4ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.addCleanup(self.client.close)
        self.uid = ObjectId()

        self.users_mock = AsyncMock()
        self.sessions_mock = AsyncMock()
        self.users_mock.find_one.return_value = {
            "_id": self.uid,
            "email": "tester@example.com",
            "preferred_genres": ["Action"],
            "interests": [],
            "feed_revision": 5,
        }
        self.sessions_mock.find_one.return_value = {
            "token": "valid-token",
            "user_id": str(self.uid),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        self.enterContext(patch.object(auth, "get_database", return_value={
            "users": self.users_mock, "sessions": self.sessions_mock
        }))

    def test_personalized_recommendations_endpoint_auth(self):
        # 1. Unauthenticated request -> 401
        res_unauth = self.client.get("/api/recommendations/personalized")
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Authenticated request -> 200
        cookies = {"rigcheck_session": "valid-token"}
        mock_feed_data = {
            "success": True,
            "feed_revision": 5,
            "is_cold_start": False,
            "recommendations": [
                {
                    "appid": 105600,
                    "title": "Terraria",
                    "explanation": "Because you enjoy Action",
                    "confidence": 95,
                }
            ],
            "already_played_recommendations": [],
            "total_recommendations": 1,
            "total_already_played": 0,
        }
        with patch("app.generate_personalized_feed", new=AsyncMock(return_value=mock_feed_data)):
            res_auth = self.client.get("/api/recommendations/personalized", cookies=cookies)
            self.assertEqual(res_auth.status_code, 200)
            data = res_auth.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["feed_revision"], 5)
            self.assertEqual(len(data["recommendations"]), 1)
            self.assertEqual(data["recommendations"][0]["appid"], 105600)


if __name__ == "__main__":
    unittest.main()
