import json

import server


class _Delta:
    def __init__(self, content=None, reasoning_content=None):
        self.content = content
        self.reasoning_content = reasoning_content


class _Chunk:
    def __init__(self, delta):
        self.choices = [type("C", (), {"delta": delta})()]


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for c in self._chunks:
            yield c


class _FakeClient:
    def __init__(self, chunks):
        self._chunks = chunks
        completions = type("Comp", (), {"create": self._create})()
        self.chat = type("Chat", (), {"completions": completions})()

    async def _create(self, **kwargs):
        return _FakeStream(self._chunks)


def _parse_sse(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                out.append(json.loads(payload))
    return out


def _drive(client, monkeypatch, deltas):
    monkeypatch.setattr(server, "OPENAI_API_KEY", "test")
    monkeypatch.setattr(server, "_get_openai_client",
                        lambda: _FakeClient([_Chunk(d) for d in deltas]))
    sid = client.post("/api/sessions", json={"services": []}).json()["id"]
    resp = client.post(f"/api/sessions/{sid}/message/stream",
                       json={"message": "go"})
    assert resp.status_code == 200, resp.text
    return _parse_sse(resp.text)


def _joined(events, etype, key):
    return "".join(e.get(key, "") for e in events if e["type"] == etype)


def test_native_reasoning_emits_thinking(client, monkeypatch):
    events = _drive(client, monkeypatch, [
        _Delta(reasoning_content="Let me "),
        _Delta(reasoning_content="reason."),
        _Delta(content="The answer "),
        _Delta(content="is 42."),
    ])
    types = [e["type"] for e in events]
    assert "THINKING_START" in types
    assert "THINKING_END" in types
    assert types.index("THINKING_START") < types.index("TEXT_MESSAGE_START")
    assert _joined(events, "THINKING_CONTENT", "delta") == "Let me reason."
    assert _joined(events, "TEXT_MESSAGE_CONTENT", "delta") == "The answer is 42."
    start = next(e for e in events if e["type"] == "THINKING_START")
    assert start["step_id"]


def test_thinking_tag_fallback(client, monkeypatch):
    events = _drive(client, monkeypatch, [
        _Delta(content="<thinking>I should "),
        _Delta(content="check.</thinking>Here "),
        _Delta(content="is the result."),
    ])
    types = [e["type"] for e in events]
    assert "THINKING_START" in types
    assert _joined(events, "THINKING_CONTENT", "delta") == "I should check."
    assert _joined(events, "TEXT_MESSAGE_CONTENT", "delta") == "Here is the result."


def test_no_reasoning_is_additive(client, monkeypatch):
    events = _drive(client, monkeypatch, [
        _Delta(content="Just an answer."),
    ])
    types = [e["type"] for e in events]
    assert "THINKING_START" not in types
    assert _joined(events, "TEXT_MESSAGE_CONTENT", "delta") == "Just an answer."
