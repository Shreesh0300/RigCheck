import assert from "node:assert/strict";
import { test } from "node:test";
import {
  fetchUserLibrary,
  fetchGameLibraryStatus,
  updateGameLibraryStatus,
  removeGameLibraryCategory,
  fetchGameReviews,
  submitGameReview,
  deleteGameReview,
  reportGameReview,
} from "../src/services/libraryService.js";

function mockApi(t, handler) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (url, options = {}) => {
    calls.push({ url, options });
    return handler(url, options);
  });
  return calls;
}

test("fetchUserLibrary requests all games or filtered category", async (t) => {
  const calls = mockApi(t, (url) => {
    if (url === "/api/library") {
      return Response.json({ success: true, games: [{ appid: 304430, is_favourite: true }] });
    }
    if (url === "/api/library?category=favourite") {
      return Response.json({ success: true, games: [{ appid: 304430, is_favourite: true }] });
    }
    return new Response(null, { status: 404 });
  });

  const all = await fetchUserLibrary();
  assert.equal(all.length, 1);
  assert.equal(all[0].appid, 304430);

  const favs = await fetchUserLibrary("favourite");
  assert.equal(favs.length, 1);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, "/api/library");
  assert.equal(calls[1].url, "/api/library?category=favourite");
});

test("fetchGameLibraryStatus returns state or unauthenticated defaults", async (t) => {
  mockApi(t, (url) => {
    if (url === "/api/library/304430") {
      return Response.json({
        success: true,
        state: { appid: 304430, is_favourite: true, want_to_play: false, already_played: true },
      });
    }
    if (url === "/api/library/2596760") {
      return new Response(null, { status: 401 });
    }
    return new Response(null, { status: 404 });
  });

  const s1 = await fetchGameLibraryStatus(304430);
  assert.equal(s1.is_favourite, true);
  assert.equal(s1.already_played, true);

  const s2 = await fetchGameLibraryStatus(2596760);
  assert.equal(s2.is_favourite, false);
  assert.equal(s2.want_to_play, false);
});

test("updateGameLibraryStatus sends PUT with CSRF header", async (t) => {
  const calls = mockApi(t, (url, options) => {
    assert.equal(options.method, "PUT");
    assert.equal(options.headers["X-CSRF-Token"], "test-csrf-token");
    assert.deepEqual(JSON.parse(options.body), { is_favourite: true });
    return Response.json({
      success: true,
      state: { appid: 304430, is_favourite: true, want_to_play: false, already_played: false },
    });
  });

  const updated = await updateGameLibraryStatus(304430, { is_favourite: true }, "test-csrf-token");
  assert.equal(updated.is_favourite, true);
  assert.equal(calls.length, 1);
});

test("removeGameLibraryCategory sends DELETE with category path", async (t) => {
  const calls = mockApi(t, (url, options) => {
    assert.equal(options.method, "DELETE");
    assert.equal(options.headers["X-CSRF-Token"], "test-csrf-token");
    return Response.json({
      success: true,
      state: { appid: 304430, is_favourite: false, want_to_play: false, already_played: false },
    });
  });

  const res = await removeGameLibraryCategory(304430, "favourite", "test-csrf-token");
  assert.equal(res.is_favourite, false);
  assert.equal(calls[0].url, "/api/library/304430/favourite");
});

test("fetchGameReviews retrieves public reviews and average rating", async (t) => {
  const calls = mockApi(t, (url) => {
    assert.equal(url, "/api/games/304430/reviews");
    return Response.json({
      success: true,
      appid: 304430,
      average_rating: 9.0,
      total_ratings: 2,
      total_reviews: 2,
      reviews: [{ rating: 9, comment: "Masterpiece" }],
    });
  });

  const data = await fetchGameReviews(304430);
  assert.equal(data.average_rating, 9.0);
  assert.equal(data.total_ratings, 2);
  assert.equal(data.reviews.length, 1);
  assert.equal(calls.length, 1);
});

test("submitGameReview sends rating and comment with CSRF token", async (t) => {
  const calls = mockApi(t, (url, options) => {
    assert.equal(url, "/api/games/304430/review");
    assert.equal(options.method, "PUT");
    assert.equal(options.headers["X-CSRF-Token"], "csrf-token-123");
    assert.deepEqual(JSON.parse(options.body), { rating: 10, comment: "Great game" });
    return Response.json({
      success: true,
      state: { appid: 304430, rating: 10, review: "Great game", already_played: true },
    });
  });

  const state = await submitGameReview(304430, 10, "Great game", "csrf-token-123");
  assert.equal(state.rating, 10);
  assert.equal(state.already_played, true);
  assert.equal(calls.length, 1);
});

test("deleteGameReview and reportGameReview endpoints", async (t) => {
  mockApi(t, (url, options) => {
    if (url === "/api/games/304430/review") {
      assert.equal(options.method, "DELETE");
      return Response.json({
        success: true,
        state: { appid: 304430, rating: null, review: null },
      });
    }
    if (url === "/api/games/304430/reviews/report") {
      assert.equal(options.method, "POST");
      assert.deepEqual(JSON.parse(options.body), { target_user_id: "user-123", reason: "Spam" });
      return Response.json({ success: true, reported: true });
    }
    return new Response(null, { status: 404 });
  });

  const deleted = await deleteGameReview(304430, "csrf-token-123");
  assert.equal(deleted.rating, null);

  const reported = await reportGameReview(304430, "user-123", "Spam", "csrf-token-123");
  assert.equal(reported.reported, true);
});
