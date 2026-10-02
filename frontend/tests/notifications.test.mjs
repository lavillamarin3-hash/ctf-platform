import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import {
  markAllNotificationsRead,
  markNotificationRead,
  observeAssignedChallenges,
  publishNotification,
  readNotifications,
  subscribeNotifications,
} from "../src/lib/notifications.ts";

class MemoryStorage {
  values = new Map();
  getItem(key) { return this.values.has(key) ? this.values.get(key) : null; }
  setItem(key, value) { this.values.set(key, value); }
  removeItem(key) { this.values.delete(key); }
}

beforeEach(() => {
  const events = new EventTarget();
  globalThis.window = Object.assign(events, { sessionStorage: new MemoryStorage() });
});

test("guarda solo tipos de evento, máximo 20, sin flags, IP ni credenciales", () => {
  for (let index = 0; index < 24; index += 1) publishNotification(8, index % 2 ? "flag.correct" : "lab.ready");
  const items = readNotifications(8);
  assert.equal(items.length, 20);
  assert.ok(items.every((item) => !item.read && item.id && item.createdAt));
  assert.deepEqual(new Set(items.map(({ kind }) => kind)), new Set(["flag.correct", "lab.ready"]));
  const raw = window.sessionStorage.getItem("ctf:notifications:8");
  assert.ok(!raw.includes("FLAG{"));
  assert.ok(!raw.includes("password"));
  assert.ok(!raw.includes("192.168."));
  publishNotification(8, "FLAG{secret}" );
  assert.equal(readNotifications(8).length, 20);
});

test("lectura individual y masiva ajustan el contador sin alterar otros usuarios", () => {
  publishNotification(8, "lab.ready");
  publishNotification(8, "flag.incorrect");
  publishNotification(9, "lab.closed");
  const id = readNotifications(8)[0].id;
  markNotificationRead(8, id);
  assert.equal(readNotifications(8).filter((item) => !item.read).length, 1);
  markAllNotificationsRead(8);
  assert.equal(readNotifications(8).filter((item) => !item.read).length, 0);
  assert.equal(readNotifications(9).filter((item) => !item.read).length, 1);
});

test("suscripción entrega eventos solo al usuario y se puede cancelar", () => {
  const seen = [];
  const stop = subscribeNotifications(8, (kind) => seen.push(kind));
  publishNotification(9, "lab.ready");
  publishNotification(8, "lab.closed");
  markAllNotificationsRead(8);
  stop();
  publishNotification(8, "flag.correct");
  assert.deepEqual(seen, ["lab.closed", undefined]);
});

test("detecta nueva asignación tras línea base sin repetir ni consultar en bucle", () => {
  observeAssignedChallenges(8, [2, 1, 1]);
  assert.equal(readNotifications(8).length, 0);
  assert.equal(window.sessionStorage.getItem("ctf:notification-assignments:8"), "[1,2]");
  observeAssignedChallenges(8, [1, 2, 3]);
  assert.deepEqual(readNotifications(8).map((item) => item.kind), ["assignment.new"]);
  observeAssignedChallenges(8, [1, 2, 3]);
  assert.equal(readNotifications(8).length, 1);
  observeAssignedChallenges(8, [1, 2]);
  assert.equal(readNotifications(8).length, 1);
  observeAssignedChallenges(8, [1, 2, 3]);
  assert.equal(readNotifications(8).length, 2);
  assert.equal(readNotifications(9).length, 0);
});

test("datos locales dañados se ignoran y recuperan", () => {
  window.sessionStorage.setItem("ctf:notifications:8", "not-json");
  assert.deepEqual(readNotifications(8), []);
  window.sessionStorage.setItem("ctf:notifications:8", JSON.stringify([{ id: "x", kind: "unknown", createdAt: "now", read: false }]));
  assert.deepEqual(readNotifications(8), []);
  window.sessionStorage.setItem("ctf:notification-assignments:8", "not-json");
  observeAssignedChallenges(8, [1, 2]);
  assert.equal(window.sessionStorage.getItem("ctf:notification-assignments:8"), "[1,2]");
  assert.equal(readNotifications(8).length, 0);
});
