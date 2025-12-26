/** @vitest-environment node */

import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { PayloadTooLargeError, parseFormDataWithLimit } from "./body";

describe("parseFormDataWithLimit", () => {
  it("parses multipart FormData with files", async () => {
    const file = new File(["hello"], "hello.txt", { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", file);

    const req = new NextRequest("http://localhost/api/test", {
      body: formData,
      method: "POST",
    });

    const parsed = await parseFormDataWithLimit(req, 1024 * 1024);
    const parsedFile = parsed.get("file");

    expect(parsedFile).toBeInstanceOf(File);
    expect((parsedFile as File).name).toBe("hello.txt");
    expect((parsedFile as File).type).toBe("text/plain");
    expect(await (parsedFile as File).text()).toBe("hello");
  });

  it("rejects payloads exceeding the configured limit", async () => {
    const file = new File(["a".repeat(1024)], "big.txt", { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", file);

    const req = new NextRequest("http://localhost/api/test", {
      body: formData,
      method: "POST",
    });

    await expect(parseFormDataWithLimit(req, 32)).rejects.toBeInstanceOf(
      PayloadTooLargeError
    );
  });
});
