/** @vitest-environment node */

import { beforeEach, describe, expect, it } from "vitest";
import {
  TEST_QSTASH_NEXT_SIGNING_KEY,
  TEST_QSTASH_SIGNING_KEY,
  TEST_QSTASH_TOKEN,
} from "@/test/upstash/constants";
import { createQStashMock } from "@/test/upstash/qstash-mock";

const qstash = createQStashMock();

describe("QStashMock", () => {
  beforeEach(() => {
    qstash.__reset();
  });

  describe("Client.publishJSON", () => {
    it("stores published messages for assertions", async () => {
      const client = new qstash.Client({ token: TEST_QSTASH_TOKEN });

      await client.publishJSON({
        body: { event: "user.signup", userId: "123" },
        url: "http://localhost/api/webhooks/notify",
      });

      const messages = qstash.__getMessages();
      expect(messages).toHaveLength(1);
      expect(messages[0].url).toBe("http://localhost/api/webhooks/notify");
      expect(messages[0].body).toEqual({ event: "user.signup", userId: "123" });
    });

    it("returns unique message IDs", async () => {
      const client = new qstash.Client({ token: TEST_QSTASH_TOKEN });

      const r1 = await client.publishJSON({ body: {}, url: "http://a" });
      const r2 = await client.publishJSON({ body: {}, url: "http://b" });

      expect(r1.messageId).toBe("qstash-mock-1");
      expect(r2.messageId).toBe("qstash-mock-2");
    });

    it("marks delayed messages as scheduled", async () => {
      const client = new qstash.Client({ token: TEST_QSTASH_TOKEN });

      const immediate = await client.publishJSON({ body: {}, url: "http://a" });
      const delayed = await client.publishJSON({
        body: {},
        delay: 5,
        url: "http://b",
      });

      expect(immediate.scheduled).toBeFalsy();
      expect(delayed.scheduled).toBe(true);
    });

    it("preserves all publish options in message", async () => {
      const client = new qstash.Client({ token: TEST_QSTASH_TOKEN });

      await client.publishJSON({
        body: { test: true },
        callback: "http://callback",
        deduplicationId: "dedup-123",
        delay: 10,
        headers: { "x-custom": "value" },
        retries: 5,
        url: "http://target",
      });

      const messages = qstash.__getMessages();
      expect(messages[0]).toMatchObject({
        body: { test: true },
        callback: "http://callback",
        deduplicationId: "dedup-123",
        delay: 10,
        headers: { "x-custom": "value" },
        retries: 5,
        url: "http://target",
      });
    });

    it("tracks publishedAt timestamp", async () => {
      const client = new qstash.Client({ token: TEST_QSTASH_TOKEN });
      const before = Date.now();

      await client.publishJSON({ body: {}, url: "http://test" });

      const messages = qstash.__getMessages();
      expect(messages[0].publishedAt).toBeGreaterThanOrEqual(before);
      expect(messages[0].publishedAt).toBeLessThanOrEqual(Date.now());
    });
  });

  describe("Receiver.verify", () => {
    it("returns true by default", async () => {
      const receiver = new qstash.Receiver({
        currentSigningKey: TEST_QSTASH_SIGNING_KEY,
        nextSigningKey: TEST_QSTASH_NEXT_SIGNING_KEY,
      });

      const valid = await receiver.verify({ body: "{}", signature: "any" });

      expect(valid).toBe(true);
    });

    it("can be forced to reject signatures", async () => {
      qstash.__forceVerify(false);

      const receiver = new qstash.Receiver({
        currentSigningKey: TEST_QSTASH_SIGNING_KEY,
        nextSigningKey: TEST_QSTASH_NEXT_SIGNING_KEY,
      });

      const valid = await receiver.verify({ body: "{}", signature: "bad" });

      expect(valid).toBe(false);
    });

    it("can be forced to throw errors", async () => {
      qstash.__forceVerify(new Error("Signature invalid"));

      const receiver = new qstash.Receiver({
        currentSigningKey: TEST_QSTASH_SIGNING_KEY,
        nextSigningKey: TEST_QSTASH_NEXT_SIGNING_KEY,
      });

      await expect(receiver.verify({ body: "{}", signature: "sig" })).rejects.toThrow(
        "Signature invalid"
      );
    });

    it("accepts optional verification parameters", async () => {
      const receiver = new qstash.Receiver({
        currentSigningKey: TEST_QSTASH_SIGNING_KEY,
        nextSigningKey: TEST_QSTASH_NEXT_SIGNING_KEY,
      });

      const valid = await receiver.verify({
        body: "{}",
        clockTolerance: 300,
        signature: "sig",
        url: "http://test",
      });

      expect(valid).toBe(true);
    });
  });

  describe("reset behavior", () => {
    it("clears all published messages", async () => {
      const client = new qstash.Client({ token: TEST_QSTASH_TOKEN });
      await client.publishJSON({ body: {}, url: "http://a" });

      expect(qstash.__getMessages()).toHaveLength(1);

      qstash.__reset();

      expect(qstash.__getMessages()).toHaveLength(0);
    });

    it("resets message counter", async () => {
      const client = new qstash.Client({ token: TEST_QSTASH_TOKEN });
      await client.publishJSON({ body: {}, url: "http://a" });
      await client.publishJSON({ body: {}, url: "http://b" });

      qstash.__reset();

      const r = await client.publishJSON({ body: {}, url: "http://c" });
      expect(r.messageId).toBe("qstash-mock-1");
    });

    it("resets verify outcome to true", async () => {
      qstash.__forceVerify(false);

      const receiver = new qstash.Receiver({
        currentSigningKey: TEST_QSTASH_SIGNING_KEY,
        nextSigningKey: TEST_QSTASH_NEXT_SIGNING_KEY,
      });

      const invalid = await receiver.verify({ body: "{}", signature: "sig" });
      expect(invalid).toBe(false);

      qstash.__reset();

      const valid = await receiver.verify({ body: "{}", signature: "sig" });
      expect(valid).toBe(true);
    });
  });

  describe("multiple clients", () => {
    it("shares message store across client instances", async () => {
      const client1 = new qstash.Client({ token: `${TEST_QSTASH_TOKEN}-1` });
      const client2 = new qstash.Client({ token: `${TEST_QSTASH_TOKEN}-2` });

      await client1.publishJSON({ body: { from: "client1" }, url: "http://a" });
      await client2.publishJSON({ body: { from: "client2" }, url: "http://b" });

      const messages = qstash.__getMessages();
      expect(messages).toHaveLength(2);
      expect(messages[0].body).toEqual({ from: "client1" });
      expect(messages[1].body).toEqual({ from: "client2" });
    });
  });
});
