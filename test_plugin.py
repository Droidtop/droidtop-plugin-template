"""Drives the example plugin with a fake droidtop module (the real one exists only inside droidtop's embedded
interpreter): `python3 test_plugin.py` from this folder. CI runs the same, before and after build.sh."""
import base64
import json
import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

calls = []
store = {}


def fake_call(api, op, args=None, version=1):
    """The host calls this example uses: the data API's read and write. Anything else is refused, as droidtop
    refuses a call the manifest does not allow."""
    args = args or {}
    calls.append((api, op, args))
    if api == "data" and op == "write":
        raw = base64.b64decode(args["base64"])
        store[args["name"]] = (store.get(args["name"], b"") if args.get("append") else b"") + raw
        return {"ok": True, "data": {}}
    if api == "data" and op == "read":
        if args["name"] not in store:
            return {"ok": False, "error": {"code": "NOT_FOUND", "message": "no such file"}}
        raw = store[args["name"]]
        part = raw[args["offset"]: args["offset"] + args["length"]]
        return {"ok": True, "data": {"base64": base64.b64encode(part).decode("ascii"), "eof": args["offset"] + len(part) >= len(raw)}}
    return {"ok": False, "error": {"code": "UNSUPPORTED", "message": "%s %s" % (api, op)}}


fake_host = types.ModuleType("droidtop.host")
fake_host.call = fake_call
fake_pkg = types.ModuleType("droidtop")
fake_pkg.__path__ = []
fake_pkg.host = fake_host
sys.modules["droidtop"] = fake_pkg
sys.modules["droidtop.host"] = fake_host

sys.path.insert(0, os.path.join(HERE, "src"))
import plugin  # noqa: E402


def send(point, op, **args):
    return json.loads(plugin.handle(json.dumps({"point": point, "version": 1, "op": op, "args": args})))


class PluginTest(unittest.TestCase):
    def setUp(self):
        calls.clear()
        store.clear()

    def facets(self):
        reply = send("ui.facets", "get", target="settings.page")
        self.assertTrue(reply["ok"], reply)
        return {f["id"]: f for f in reply["data"]["facets"]}

    def test_the_settings_page_starts_with_the_defaults(self):
        facets = self.facets()
        self.assertEqual(True, facets["enabled"]["value"])
        self.assertEqual("Hello", facets["greeting"]["value"])
        self.assertEqual("Hello!", facets["now"]["value"])
        for facet in facets.values():
            self.assertEqual(["settings.page"], facet["targets"])

    def test_a_change_is_kept_and_shown(self):
        self.assertTrue(send("ui.facets", "setGreeting", value="Good morning")["ok"])
        self.assertTrue(send("ui.facets", "setEnabled", value=False)["ok"])
        facets = self.facets()
        self.assertEqual("Good morning", facets["greeting"]["value"])
        self.assertEqual("Off", facets["now"]["value"])

    def test_bad_values_are_refused(self):
        self.assertEqual("INVALID_ARGS", send("ui.facets", "setEnabled", value="yes")["error"]["code"])
        self.assertEqual("INVALID_ARGS", send("ui.facets", "setGreeting", value="  ")["error"]["code"])

    def test_an_undeclared_point_is_unsupported(self):
        self.assertEqual("UNSUPPORTED", send("library.sources", "search", query="x")["error"]["code"])
        self.assertEqual("INVALID_ARGS", json.loads(plugin.handle("not json"))["error"]["code"])

    def test_the_manifest_declares_what_the_plugin_answers(self):
        manifest = json.load(open(os.path.join(HERE, "manifest.template.json")))
        self.assertEqual(manifest["origin"], manifest["id"].split(".")[0])
        self.assertEqual(["ui.facets"], [p["point"] for p in manifest["provides"]])
        self.assertEqual("python", manifest["kind"])


if __name__ == "__main__":
    unittest.main()
