import { describe, expect, it } from "vitest";
import { effectClassForPrefix } from "../effectClass";

describe("effectClassForPrefix", () => {
  it("maps messaging / ticketing / PR mounts to external-effect", () => {
    expect(effectClassForPrefix("/slack")).toBe("external-effect");
    expect(effectClassForPrefix("/linear")).toBe("external-effect");
    expect(effectClassForPrefix("/gmail")).toBe("external-effect");
    expect(effectClassForPrefix("/github/pulls")).toBe("external-effect");
    expect(effectClassForPrefix("/pagerduty")).toBe("external-effect");
  });

  it("maps databases / customers / finance to system-of-record", () => {
    expect(effectClassForPrefix("/postgres")).toBe("system-of-record");
    expect(effectClassForPrefix("/customers/accounts")).toBe("system-of-record");
    expect(effectClassForPrefix("/finance")).toBe("system-of-record");
  });

  it("maps object/doc stores to durable-internal", () => {
    expect(effectClassForPrefix("/s3")).toBe("durable-internal");
    expect(effectClassForPrefix("/datadog")).toBe("durable-internal");
    expect(effectClassForPrefix("/tickets")).toBe("durable-internal");
  });

  it("maps scratch and root to scratch", () => {
    expect(effectClassForPrefix("/scratch")).toBe("scratch");
    expect(effectClassForPrefix("/tmp")).toBe("scratch");
    expect(effectClassForPrefix("/")).toBe("scratch");
    expect(effectClassForPrefix("")).toBe("scratch");
  });

  it("defaults unknown mounts to durable-internal", () => {
    expect(effectClassForPrefix("/some-unknown-thing")).toBe("durable-internal");
  });
});
