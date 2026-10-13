import { afterEach, beforeEach, test } from "node:test";
import assert from "node:assert/strict";
import { getErrorMessage, request } from "./api.js";

let storage;
let events;
beforeEach(() => {
  storage = new Map([["access_token","test-token"]]);
  events = [];
  globalThis.localStorage = { getItem: (key) => storage.get(key) ?? null };
  globalThis.window = { dispatchEvent: (event) => events.push(event.type) };
});
afterEach(() => {
  delete globalThis.localStorage;
  delete globalThis.window;
  delete globalThis.fetch;
});

test("validation errors identify fields and remain readable", () => {
  assert.equal(getErrorMessage({detail:[{loc:["body","title"],msg:"Too short"}]},"Failed"),
    "title: Too short");
  assert.equal(getErrorMessage({detail:"Ticket not found"},"Failed"),"Ticket not found");
  assert.equal(getErrorMessage({},"Failed"),"Failed");
});

test("request adds bearer identity and JSON body", async () => {
  globalThis.fetch = async (url, options) => {
    assert.ok(url.endsWith("/tickets/"));
    assert.equal(options.headers.Authorization,"Bearer test-token");
    assert.equal(options.headers["Content-Type"],"application/json");
    assert.deepEqual(JSON.parse(options.body),{title:"Example"});
    return new Response('{"message":"Created"}',{status:200});
  };
  assert.deepEqual(await request("/tickets/",{method:"POST",body:{title:"Example"}}),
    {message:"Created"});
});

test("expired sessions notify the UI and reject the response", async () => {
  globalThis.fetch = async () => new Response('{"detail":"Expired"}',{status:401});
  await assert.rejects(request("/auth/me"),/session expired/);
  assert.deepEqual(events,["session-expired"]);
});

test("invalid login does not expire an existing session", async () => {
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.headers.Authorization,undefined);
    return new Response('{"detail":"Invalid email or password"}',{status:401});
  };
  await assert.rejects(request("/auth/login",{publicRequest:true,method:"POST",
    body:new URLSearchParams({username:"user",password:"wrong"})}),/Invalid email or password/);
  assert.deepEqual(events,[]);
});

test("responses from an old session cannot populate a new account", async () => {
  globalThis.fetch = async () => {
    storage.set("access_token","new-account-token");
    return new Response('{"tickets":[{"title":"Private"}]}',{status:200});
  };
  await assert.rejects(request("/tickets/"),/session changed/);
});

test("network and non-JSON failures produce useful errors", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(request("/tickets/"),/Could not connect/);
  globalThis.fetch = async () => new Response("Bad gateway",{status:502});
  await assert.rejects(request("/tickets/"),/Request failed \(502\)/);
});
