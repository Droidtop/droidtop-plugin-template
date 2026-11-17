# droidtop plugin template

A template for a [droidtop](https://github.com/Droidtop/droidtop) plugin. It holds a small working plugin, a settings
page with a switch and a greeting, and everything around it: the manifest, the build, signing, tests and a release
workflow. Press **Use this template**, rename the plugin, and replace `src/plugin.py` with what yours does.

To offer your plugins as a list people can add to droidtop, use
[droidtop-repo-template](https://github.com/Droidtop/droidtop-repo-template) as well.

## How a plugin is put together

A plugin is one signed bundle, `<id>.droidplugin.tar.xz`, that droidtop installs. It holds:

| File | What it is |
| --- | --- |
| `manifest.json` | Who the plugin is and what it may do. Built from `manifest.template.json`. |
| `manifest.jws` | The signature over the exact bytes of `manifest.json`, with this repository's certificate in it. |
| `plugin.py` (the payload) | The code. Every payload file is listed in the manifest with its SHA-256, and droidtop checks each one. |

droidtop runs nothing before the person approves the plugin, and every call the plugin makes goes through droidtop and
is checked against its manifest.

### The manifest

`manifest.template.json` is the manifest without the payload hashes, which `build.sh` adds.

| Field | Meaning |
| --- | --- |
| `id` | `<origin>.<name>`, lower case. Never changes once published. |
| `origin` | Your publisher id (see [Signing](#signing)). Every plugin you publish shares it. |
| `label`, `description` | What people see. Keep both short and plain. |
| `version` | The version you declare. CI publishes `<version>-<run number>`. Raise it whenever `src/`, `build.sh` or the template change; CI refuses a code change under the same version. |
| `kind` | How droidtop runs the plugin. This template is `python`: one `plugin.py` in droidtop's embedded interpreter, in its own contained process. Other kinds are `native_bundle` (a Kotlin entry point, with native libraries for arm64-v8a and x86_64), `flutter_embed` and `app_interface` (a plugin carried by an Android app). |
| `contractVersion` | The plugin API version it is written for. A droidtop too old for it refuses to install it. |
| `category` | Where it is listed: `sources`, `emulators`, `system`, `sync`, `integrations`, `appearance` or `other`. |
| `provides` | The extension points the plugin answers, each with its version and fields. droidtop calls only these. This example provides `ui.facets` for the `settings.page` target. |
| `permissions` | The host APIs it may use, each with a plain `reason` shown when the person approves it. The data API this example uses needs none. |
| `requestsRoot`, `abis` | Whether it asks for elevated access, and which CPU types a native payload is built for. |

droidtop's [docs/plugin-api.md](https://github.com/Droidtop/droidtop/blob/main/docs/plugin-api.md) lists every
extension point, permission and host API, the facets a plugin can draw, and the rules each comes with.

### The code

For a `python` plugin, droidtop imports `plugin.py` and calls `handle(call_json)` with each request:

    {"point": "ui.facets", "version": 1, "op": "get", "args": {"target": "settings.page"}}

It answers with JSON text, `{"ok": true, "data": ...}` or `{"ok": false, "error": {"code": ..., "message": ...}}`.
To reach droidtop it calls `droidtop.host.call(api, op, args)`, which droidtop places in `sys.modules` before the import.
A long task can run as a job (`start_job(job_id, call, progress)` and `cancel_job(job_id)`), shown in droidtop's
Downloads with its progress. Use the standard library only; the network goes through droidtop's `net` API.

On-screen text should say what happens in a few words. droidtop draws every screen itself, from the facets the plugin
returns, so a plugin looks like the rest of droidtop.

## Develop and test

    python3 test_plugin.py      # the tests, with a fake droidtop module
    ./build.sh                  # build/manifest.json and build/plugin.py, unsigned

The scripts need bash, Python 3, `tar` and `xz`, and `openssl` for the keys. They run on Linux, on macOS (`brew install
xz` if it is missing) and in Git Bash on Windows.

To try it on a device, sign a build (below) and open the `.droidplugin.tar.xz` from droidtop: Settings > Plugins > Get plugins >
Install plugin file.

## Signing

droidtop installs only signed bundles. Your keys form a short chain:

1. **Your root**, one per publisher. Its private key stays offline, on your own computer.
2. **A signing key for this repository**, issued by your root and kept in this repository's secrets. CI signs with it.
3. **`droidtop-plugin-key.json`**, committed here and attached to each release: your origin and the root certificate
   (public). When someone installs one of your plugins for the first time, droidtop shows that key's fingerprint and
   trusts it from then on. Your plugins are marked Unofficial; only droidtop's own are Official.

Make them with `tools/make_keys.sh` (openssl and Python 3):

    bash tools/make_keys.sh root yourorigin ~/yourorigin-keys
    bash tools/make_keys.sh plugin yourorigin yourorigin.hello ~/yourorigin-keys hello

The first writes `root.key` (**keep it offline; never commit it or put it in a secret**), `root.crt` and
`droidtop-plugin-key.json`. Commit `droidtop-plugin-key.json` here. The second writes `hello.key` and `hello.crt`. Put
their contents in this repository's secrets `PLUGIN_SIGNING_KEY` and `PLUGIN_SIGNING_CERT` (Settings > Secrets and
variables > Actions). A key made for `yourorigin.hello` signs only that plugin; give `yourorigin.*` to let one
repository sign several. Make one signing key per repository, all from the same root.

To sign by hand: `PLUGIN_SIGNING_KEY_FILE=<key> PLUGIN_SIGNING_CERT_FILE=<cert> ./sign.sh`.

## Releases and channels

On every push to the default branch, `.github/workflows/build.yml` tests, builds, signs and publishes a release
tagged `v<version>-<run>` with the bundle, its manifest and `droidtop-plugin-key.json`. Without the secrets it builds and
tests and stops there. Pull requests never sign.

A catalog lists a release by channel: a normal release is `stable`, a pre-release is `testing`, and a pre-release whose
tag starts with `plugin-unstable` or `plugin-build` is `unstable`. People choose how early they want versions.

**Listing in a catalog.** A catalog made from droidtop-repo-template lists every plugin repository in its organisation
that publishes signed releases. To have it list a release at once, set the repository variable `CATALOG_REPO` and the
secret `CATALOG_DISPATCH_TOKEN`; the workflow's last step explains them.

## Repository layout

| Path | What it is |
| --- | --- |
| `src/plugin.py` | The plugin. |
| `manifest.template.json` | The manifest, without payload hashes. |
| `build.sh`, `sign.sh` | Build the bundle's contents; sign and pack it. |
| `test_plugin.py` | The tests, run by CI before and after the build. |
| `tools/` | `make_keys.sh`, and the signing and verifying scripts droidtop's own tooling uses. |
| `tools/kotlin/` | The Kotlin plugin SDK, for a `native_bundle` plugin (below). |
| `CHANGELOG.md` | What each version changed. |

**Branches, for a larger plugin.** droidtop's own plugins keep the plugin's own code apart from what makes it a plugin:
a `creation` branch holds the core code and its tests, a `plugin-core` branch (the default) holds this wrapper (the
manifest, build, signing and changelog) and pins a `creation` commit, and a `plugin/stable` branch is the two combined,
which releases build from. A plugin built around another project's app keeps that project on an `upstream-sync`
branch instead of `creation`. A small plugin like this one needs none of that: one branch is fine.

**Kotlin plugins and the SDK.** A `native_bundle` plugin written in Kotlin talks to droidtop through the same broker
calls every time: one call and its error, a small HTTP request, a download as a droidtop job, its data files and a file
the person picks. `tools/kotlin/dev/droidtop/plugin/sdk/Host.kt` does all of that. Copy it unchanged to
`src/dev/droidtop/plugin/sdk/Host.kt`, subclass `Host` for your plugin's own calls, and add the copy to your Template
drift workflow, so a fix here reaches you as a new tag of this repository.

## Licence

GPL-3.0-only, as is droidtop. See [LICENSE](LICENSE). Your plugin may use any licence compatible with the code it
contains.
