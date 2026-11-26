"""Simple local deployment for the Lab 10 app.

Each run copies the application into a new release folder, points the
``current`` symlink at it, smoke-tests the deployed code and removes old
releases (keeping the last few so a rollback is just a symlink change).

Usage: python deploy.py [DEPLOY_DIR]
"""
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone

APP_FILES = ["app.py", "requirements.txt"]
KEEP_RELEASES = 5
EXPECTED_OUTPUT = "Hello, World from Jad Moharam!"


def default_deploy_dir():
    base = os.environ.get("JENKINS_HOME", os.path.expanduser("~"))
    return os.path.join(base, "deployments", "python-app")


def release_name():
    build = os.environ.get("BUILD_NUMBER", "local")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"build-{build}-{stamp}"


def copy_release(src_dir, release_dir):
    os.makedirs(release_dir)
    for name in APP_FILES:
        shutil.copy2(os.path.join(src_dir, name), release_dir)
    info = {
        "build_number": os.environ.get("BUILD_NUMBER", "local"),
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "deployed_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(release_dir, "release.json"), "w") as f:
        json.dump(info, f, indent=2)


def switch_current(deploy_dir, release_dir):
    """Atomically repoint the ``current`` symlink at the new release."""
    current = os.path.join(deploy_dir, "current")
    tmp_link = current + ".tmp"
    if os.path.lexists(tmp_link):
        os.remove(tmp_link)
    os.symlink(release_dir, tmp_link)
    os.replace(tmp_link, current)
    return current


def smoke_test(current):
    """Import the deployed app and check it returns the expected greeting."""
    spec = importlib.util.spec_from_file_location(
        "deployed_app", os.path.join(current, "app.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = module.greet("World")
    if output != EXPECTED_OUTPUT:
        raise RuntimeError(f"Smoke test failed: got {output!r}")
    return output


def prune(deploy_dir, keep=KEEP_RELEASES):
    """Delete all but the newest ``keep`` releases (never the live one)."""
    releases_dir = os.path.join(deploy_dir, "releases")
    live = os.path.realpath(os.path.join(deploy_dir, "current"))
    paths = [os.path.join(releases_dir, n) for n in os.listdir(releases_dir)]
    paths.sort(key=lambda p: os.stat(p).st_mtime_ns)
    old = [p for p in paths[:-keep] if os.path.realpath(p) != live]
    for path in old:
        shutil.rmtree(path)
    return len(paths) - len(old)


def deploy(src_dir=".", deploy_dir=None):
    deploy_dir = deploy_dir or default_deploy_dir()
    release_dir = os.path.join(deploy_dir, "releases", release_name())
    copy_release(src_dir, release_dir)
    current = switch_current(deploy_dir, release_dir)
    output = smoke_test(current)
    kept = prune(deploy_dir)
    return release_dir, output, kept


def main():
    deploy_dir = sys.argv[1] if len(sys.argv) > 1 else None
    release_dir, output, kept = deploy(".", deploy_dir)
    print(f"Deployed release: {release_dir}")
    print(f"Smoke test output: {output}")
    print(f"Releases kept: {kept}")


if __name__ == "__main__":
    main()
