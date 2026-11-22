import assert from "node:assert/strict";
import { test } from "node:test";
import {
  fetchPersonalizedRecommendations,
  fetchUserPreferences,
  updateUserPreferences,
  fetchAiHistory,
  deleteAiHistoryItem,
  clearAllAiHistory,
  logAiInteraction,
} from "../src/services/recommendationService.js";

function mockApi(t, handler) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (url, options = {}) => {
    calls.push({ url, options });
    return handler(url, options);
  });
  return calls;
}

test("fetchPersonalizedRecommendations requests API with query params and handles auth", async (t) => {
  const calls = mockApi(t, (url) => {
    if (url.startsWith("/api/recommendations/personalized")) {
      return Response.json({
        success: true,
        feed_revision: 3,
        is_cold_start: false,
        recommendations: [
          { appid: 105600, title: "Terraria", explanation: "Because you enjoy Action" },
        ],
        already_played_recommendations: [
          { appid: 304430, title: "INSIDE", rating: 10 },
        ],
        total_recommendations: 1,
      });
    }
    return new Response(null, { status: 404 });
  });

  const res = await fetchPersonalizedRecommendations({ limit: 15, refresh: true });
  assert.equal(res.success, true);
  assert.equal(res.authenticated, true);
  assert.equal(res.recommendations.length, 1);
  assert.equal(res.recommendations[0].appid, 105600);
  assert.equal(res.already_played_recommendations.length, 1);
  assert.equal(calls.length, 1);
  assert.ok(calls[0].url.includes("limit=15"));
  assert.ok(calls[0].url.includes("refresh=true"));
});

test("fetchPersonalizedRecommendations returns unauthenticated fallback on 401", async (t) => {
  mockApi(t, () => new Response(null, { status: 401 }));

  const res = await fetchPersonalizedRecommendations();
  assert.equal(res.authenticated, false);
  assert.equal(res.success, false);
  assert.equal(res.recommendations.length, 0);
});

test("fetchUserPreferences and updateUserPreferences work with CSRF headers", async (t) => {
  globalThis.document = { cookie: "rigcheck_csrf=test-csrf-token-123" };

  const calls = mockApi(t, (url, options) => {
    if (url === "/api/preferences" && (!options.method || options.method === "GET")) {
      return Response.json({
        success: true,
        preferences: {
          preferred_genres: ["RPG", "Action"],
          interests: ["open world"],
          onboarding_completed: true,
          feed_revision: 2,
        },
      });
    }
    if (url === "/api/preferences" && options.method === "PUT") {
      const body = JSON.parse(options.body);
      return Response.json({
        success: true,
        preferences: {
          preferred_genres: body.preferred_genres,
          interests: body.interests,
          onboarding_completed: body.onboarding_completed,
          feed_revision: 3,
        },
      });
    }
    return new Response(null, { status: 404 });
  });

  const prefs = await fetchUserPreferences();
  assert.equal(prefs.preferred_genres.length, 2);
  assert.equal(prefs.preferred_genres[0], "RPG");

  const updated = await updateUserPreferences({
    preferred_genres: ["Indie"],
    interests: ["single-player"],
    onboarding_completed: true,
  });
  assert.equal(updated.preferred_genres[0], "Indie");
  assert.equal(calls[1].options.headers["X-CSRF-Token"], "test-csrf-token-123");
});

test("AI history fetch, single item delete, and clear all history", async (t) => {
  globalThis.document = { cookie: "rigcheck_csrf=csrf-token-abc" };

  const calls = mockApi(t, (url, options) => {
    if (url.startsWith("/api/ai-history") && (!options.method || options.method === "GET")) {
      return Response.json({
        success: true,
        history: [{ id: "query_1", query: "fast paced racer" }],
      });
    }
    if (url === "/api/ai-history/query_1" && options.method === "DELETE") {
      return Response.json({ success: true, message: "Query deleted" });
    }
    if (url === "/api/ai-history" && options.method === "DELETE") {
      return Response.json({ success: true, message: "Cleared all" });
    }
    return new Response(null, { status: 404 });
  });

  const history = await fetchAiHistory(20);
  assert.equal(history.length, 1);
  assert.equal(history[0].id, "query_1");

  const deleted = await deleteAiHistoryItem("query_1");
  assert.equal(deleted, true);
  assert.equal(calls[1].options.headers["X-CSRF-Token"], "csrf-token-abc");

  const cleared = await clearAllAiHistory();
  assert.equal(cleared, true);
  assert.equal(calls[2].options.headers["X-CSRF-Token"], "csrf-token-abc");
});

test("logAiInteraction sends interaction payload", async (t) => {
  globalThis.document = { cookie: "rigcheck_csrf=csrf-interaction-token" };

  const calls = mockApi(t, (url) => {
    if (url === "/api/ai-history/interaction") {
      return Response.json({ success: true });
    }
    return new Response(null, { status: 404 });
  });

  await logAiInteraction({ appid: 304430, action: "click", query_id: "q_123" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/api/ai-history/interaction");
  const payload = JSON.parse(calls[0].options.body);
  assert.equal(payload.appid, 304430);
  assert.equal(payload.action, "click");
  assert.equal(payload.query_id, "q_123");
});
