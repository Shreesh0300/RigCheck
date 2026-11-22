import assert from "node:assert/strict";
import { test } from "node:test";
import { loadGameDetails } from "../src/services/gameService.js";

function mockApi(t, responses) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (url) => {
    calls.push(url);
    const body = responses[url];
    return body ? Response.json(body) : new Response(null, { status: 404 });
  });
  return calls;
}

test("primary, alternative and gallery summaries load their own App ID", async (t) => {
  const calls = mockApi(t, {
    "/games/2596760": { appid: 2596760, name: "Inside" },
    "/games/304430": { appid: 304430, name: "INSIDE" },
  });
  for (const [appid, title] of [[2596760, "Inside"], [304430, "INSIDE"], [2596760, "Inside"]]) {
    const game = { appid, title, compatibility: { compatibility_pct: 80 } };
    assert.deepEqual(await loadGameDetails(game), { ...game, name: title });
  }
  assert.deepEqual(calls, ["/games/2596760", "/games/304430", "/games/2596760"]);
});

test("explicit invalid, missing catalog and mismatched response IDs never use a title", async (t) => {
  const calls = mockApi(t, { "/games/304430": { appid: 2596760, name: "Inside" } });
  for (const appid of [0, null, false, "", "12x", -1, 1.5, "9007199254740993", 999999, 304430]) {
    assert.deepEqual(await loadGameDetails({ appid, title: "INSIDE" }), { title: "INSIDE" });
  }
  assert.deepEqual(calls, ["/games/999999", "/games/304430"]);
});

test("legacy steamAppId resolves directly, including a numeric string", async (t) => {
  const record = { appid: 304430, name: "INSIDE" };
  const calls = mockApi(t, { "/games/304430": record });
  assert.equal((await loadGameDetails({ steamAppId: "304430", title: "Inside" })).name, "INSIDE");
  assert.deepEqual(calls, ["/games/304430"]);
});

test("only an unambiguous legacy title match resolves to a record", async (t) => {
  const game = { appid: 550, name: "Left 4 Dead 2" };
  const calls = mockApi(t, {
    "/search?q=Left%204%20Dead%202&limit=2": [game, { appid: 9, name: "Left 4 Dead 2 extra" }],
    "/games/550": game,
    "/search?q=Inside&limit=2": [{ appid: 2596760, name: "Inside" }, { appid: 304430, name: "INSIDE" }],
    "/search?q=Dead%202&limit=2": [game],
  });
  assert.equal((await loadGameDetails({ title: game.name })).appid, 550);
  assert.deepEqual(await loadGameDetails({ title: "Inside" }), { title: "Inside" });
  assert.deepEqual(await loadGameDetails({ title: "Dead 2" }), { title: "Dead 2" });
  assert.equal(calls.length, 4);
});
