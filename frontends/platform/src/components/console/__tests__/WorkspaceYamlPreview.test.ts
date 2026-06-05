import { describe, expect, it } from "vitest";
import { buildWorkspaceYaml } from "../WorkspaceYamlPreview";

describe("buildWorkspaceYaml", () => {
  it("renders mounts with derived effect classes — the form and file are two views of one thing", () => {
    const yaml = buildWorkspaceYaml({
      name: "incident",
      templateId: "incident-response",
      mode: "TEST",
      mounts: [
        { path: "/slack", mode: "ro" },
        { path: "/scratch", mode: "rw" },
      ],
    });
    expect(yaml).toContain("name: incident");
    expect(yaml).toContain("template: incident-response");
    expect(yaml).toContain("mode: TEST");
    expect(yaml).toContain("- path: /slack");
    expect(yaml).toContain("effect_class: external-effect");
    expect(yaml).toContain("- path: /scratch");
    expect(yaml).toContain("effect_class: scratch");
  });

  it("handles an empty mount list", () => {
    const yaml = buildWorkspaceYaml({
      name: "",
      templateId: "custom",
      mode: "TEST",
      mounts: [],
    });
    expect(yaml).toContain("name: untitled");
    expect(yaml).toContain("mounts:");
  });
});
