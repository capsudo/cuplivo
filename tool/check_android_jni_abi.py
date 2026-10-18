#!/usr/bin/env python3
"""Check JNI entry points in the actual, shrunk release APKs."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


def read_classes(apk, dexdump):
    classes = {}
    with tempfile.TemporaryDirectory() as directory, zipfile.ZipFile(apk) as archive:
        for name in archive.namelist():
            if not re.fullmatch(r"classes\d*\.dex", name):
                continue
            dex = Path(directory, name)
            dex.write_bytes(archive.read(name))
            dump = subprocess.run(
                [str(dexdump), str(dex)],
                capture_output=True,
                text=True,
                errors="replace",
                check=True,
            ).stdout
            for block in re.split(r"(?m)^Class #\d+", dump):
                descriptor = re.search(r"Class descriptor\s*:\s*'([^']+)'", block)
                if descriptor is None:
                    continue
                parent = re.search(r"Superclass\s*:\s*'([^']+)'", block)
                members = {}
                for member in re.finditer(
                    r"name\s*:\s*'([^']+)'\s+"
                    r"type\s*:\s*'([^']+)'\s+"
                    r"access\s*:\s*0x([0-9a-fA-F]+)",
                    block,
                ):
                    name, signature, access = member.groups()
                    members[name, signature] = int(access, 16)
                classes[descriptor.group(1)] = (
                    parent.group(1) if parent else None,
                    members,
                )
    return classes


def check(apk, dexdump):
    classes = read_classes(apk, dexdump)
    failures = []

    def require(class_name, name=None, signature=None, *, static=False):
        descriptor = "L" + class_name + ";"
        if descriptor not in classes:
            failures.append("missing JNI class: " + class_name)
            return
        if name is None:
            return
        current = descriptor
        while current in classes:
            parent, members = classes[current]
            access = members.get((name, signature))
            if access is not None and bool(access & 0x0008) == static:
                return
            current = parent
        failures.append(f"missing JNI member: {class_name}.{name}{signature}")

    require(
        "io/flutter/plugins/sharedpreferences/SharedPreferencesApiRegistrar",
        "getAll",
        "(Ljava/lang/String;Ljava/util/List;Lkotlin/coroutines/Continuation;)"
        "Ljava/lang/Object;",
    )
    require("kotlin/coroutines/Continuation", "resumeWith", "(Ljava/lang/Object;)V")
    require("kotlin/coroutines/intrinsics/CoroutineSingletons")
    require(
        "kotlin/coroutines/intrinsics/IntrinsicsKt",
        "getCOROUTINE_SUSPENDED",
        "()Ljava/lang/Object;",
        static=True,
    )
    require("kotlin/Result", "value", "Ljava/lang/Object;")
    require("kotlin/Result$Failure", "exception", "Ljava/lang/Throwable;")
    require("kotlin/Result$Failure", "<init>", "(Ljava/lang/Throwable;)V")
    require("kotlin/Unit", "INSTANCE", "Lkotlin/Unit;", static=True)
    for failure in failures:
        print(f"{apk.name}: {failure}")
    if not failures:
        print(f"{apk.name}: release JNI ABI verified")
    return not failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apks", nargs="+", type=Path)
    parser.add_argument("--dexdump", type=Path)
    args = parser.parse_args()
    dexdump = args.dexdump or shutil.which("dexdump")
    if dexdump is None:
        sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        candidates = sorted(Path(sdk).glob("build-tools/*/dexdump")) if sdk else []
        if not candidates:
            parser.error("dexdump not found; set ANDROID_HOME or pass --dexdump")
        dexdump = candidates[-1]
    results = [check(apk, dexdump) for apk in args.apks]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
