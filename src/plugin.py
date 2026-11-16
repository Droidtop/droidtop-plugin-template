"""yourorigin.hello: an example droidtop plugin to start from.

A python-kind plugin (droidtop docs/plugin-api.md): droidtop loads this one file in its own contained process and calls
handle() with each request as JSON text. The plugin answers with JSON text. It reaches droidtop only through
droidtop.host.call(api, op, args), which droidtop puts in sys.modules before importing this file; every call it makes is
checked against the permissions in the manifest.

This example adds a settings page (the ui.facets point, target settings.page) with a switch and a greeting that it keeps
with droidtop's data API. Replace it with what your plugin does; keep handle()'s shape.
"""
import base64
import json

import droidtop.host

SETTINGS_TARGET = "settings.page"
STATE_FILE = "settings.json"
CHUNK = 48 * 1024
# The error codes droidtop understands (docs/plugin-api.md); anything else is sent as FAILED.
ERROR_CODES = {"INVALID_ARGS", "UNSUPPORTED", "NOT_FOUND", "PERMISSION_DENIED", "RATE_LIMITED", "TIMEOUT", "CANCELLED", "FAILED"}


class HostError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ----------------------------------------------------------------------------------------------- talking to droidtop


def _ok(data=None):
    return json.dumps({"ok": True, "data": data if data is not None else {}})


def _error(code, message):
    return json.dumps({"ok": False, "error": {"code": code, "message": message}})


def _call(api, op, args=None, version=1):
    # A refusal comes back as {"ok": false, ...}; host calls never raise.
    return droidtop.host.call(api, op, args or {}, version)


def _data(api, op, args):
    reply = _call(api, op, args)
    if not reply.get("ok"):
        error = reply.get("error") or {}
        raise HostError(error.get("code", "FAILED"), error.get("message", "%s %s failed" % (api, op)))
    return reply.get("data") or {}


# The data API keeps small files in the plugin's own storage, read and written in base64 chunks.
def _read_json(name):
    data = bytearray()
    while True:
        reply = _call("data", "read", {"name": name, "offset": len(data), "length": CHUNK, "as": "base64"})
        if not reply.get("ok"):
            return None
        body = reply.get("data") or {}
        chunk = base64.b64decode(body.get("base64") or "")
        data.extend(chunk)
        if body.get("eof") or not chunk:
            break
    try:
        return json.loads(data.decode("utf-8")) if data else None
    except ValueError:
        return None


def _write_json(name, value):
    raw = json.dumps(value, sort_keys=True).encode("utf-8")
    offset = 0
    first = True
    while True:
        end = min(offset + CHUNK, len(raw))
        _data("data", "write", {"name": name, "base64": base64.b64encode(raw[offset:end]).decode("ascii"), "append": not first})
        first = False
        offset = end
        if offset >= len(raw):
            break


def _state():
    state = {"enabled": True, "greeting": "Hello"}
    saved = _read_json(STATE_FILE)
    if isinstance(saved, dict):
        if isinstance(saved.get("enabled"), bool):
            state["enabled"] = saved["enabled"]
        if isinstance(saved.get("greeting"), str):
            state["greeting"] = saved["greeting"][:60]
    return state


# --------------------------------------------------------------------------------------------- the settings page


def _facet(fid, kind, label, **fields):
    facet = {"id": fid, "kind": kind, "v": 1, "targets": [SETTINGS_TARGET], "label": label}
    facet.update({k: v for k, v in fields.items() if v is not None})
    return facet


def _settings_facets(state):
    """docs/plugin-api.md 1.10: facets are small pieces of UI as data, which droidtop draws with its own components."""
    return {
        "facets": [
            _facet("enabled", "toggle", "Say hello", value=state["enabled"], call={"op": "setEnabled"}),
            _facet("greeting", "input", "Greeting", value=state["greeting"], call={"op": "setGreeting"}),
            _facet("now", "status", "Today", state="ok" if state["enabled"] else "off",
                   value=(state["greeting"] + "!") if state["enabled"] else "Off"),
        ]
    }


def _value(args):
    """A facet's committed value (docs/plugin-api.md 1.10)."""
    return args.get("value")


def _set_enabled(args):
    value = _value(args)
    if not isinstance(value, bool):
        raise HostError("INVALID_ARGS", "Expected on or off")
    state = _state()
    state["enabled"] = value
    _write_json(STATE_FILE, state)
    return _ok({"message": "On" if value else "Off"})


def _set_greeting(args):
    value = str(_value(args) or "").strip()
    if not value:
        raise HostError("INVALID_ARGS", "Type a greeting")
    state = _state()
    state["greeting"] = value[:60]
    _write_json(STATE_FILE, state)
    return _ok({"message": "Saved"})


# ----------------------------------------------------------------------------------------------- entry points


def handle(call_json):
    """Every request droidtop sends: {"point", "version", "op", "args"}. Answer only the points the manifest declares."""
    try:
        call = json.loads(call_json)
    except ValueError:
        return _error("INVALID_ARGS", "not JSON")
    point = call.get("point")
    op = call.get("op")
    args = call.get("args") or {}
    try:
        if point == "ui.facets":
            if op == "get":
                if args.get("target") == SETTINGS_TARGET:
                    return _ok(_settings_facets(_state()))
                return _ok({"facets": []})
            if op == "setEnabled":
                return _set_enabled(args)
            if op == "setGreeting":
                return _set_greeting(args)
    except HostError as error:
        return _error(error.code if error.code in ERROR_CODES else "FAILED", error.message)
    return _error("UNSUPPORTED", "Unsupported point/op: %s/%s" % (point, op))


def on_unload():
    """Called before droidtop stops the plugin's process."""
