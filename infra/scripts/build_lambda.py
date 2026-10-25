"""Construit, et publie avec --publish, le zip de chaque Lambda Python du workspace.

    uv run infra/scripts/build_lambda.py                         # toutes les Lambdas de lambdas/*
    uv run infra/scripts/build_lambda.py ingest-bodacc           # une seule
    uv run infra/scripts/build_lambda.py --publish --profile data-platform

Une Lambda = un membre uv dans lambdas/<dossier>/ ; son `name` (pyproject) est son identifiant partout :
zip local build/<name>.zip, objet s3://<artifacts>/lambdas/<name>/<sha256>.zip, clé de `local.lambdas` en Terraform.

Build, deux installations dans le même dossier :
  1. les dépendances tierces du membre, versions du lock, en roues binaires Linux uniquement
     (`--only-binary :all:` : jamais de compilation sur le Mac, qui produirait du code macOS) ;
  2. les membres du workspace (le membre et ses dépendances internes), purs Python, sans leurs dépendances.
Puis un zip reproductible : mêmes fichiers → mêmes octets → même hash.

Publication : le zip va sous une clé adressée par son contenu (déjà présente = rien à envoyer), puis le
pointeur lambdas/<name>/current.json, lu par Terraform, désigne la version à déployer (réécrit seulement
s'il change). Bucket : data-platform-artifacts-<account_id>, créé par infra/bootstrap/.
"""

import argparse
import base64
import hashlib
import json
import subprocess
import tempfile
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAMBDAS_DIR = ROOT / "lambdas"
BUILD_DIR = ROOT / "build"
PLATFORM = "aarch64-manylinux2014"  # Lambda arm64 (Graviton)
PYTHON_VERSION = "3.12"  # runtime python3.12
REGION = "eu-west-3"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)  # plus petite date possible dans un zip
EXCLUDED_DIRS = {"__pycache__", "bin"}  # bytecode compilé sur le Mac, scripts CLI inutiles en Lambda


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def lambda_names() -> list[str]:
    """`name` de chaque membre de lambdas/*, triés : la convention remplace toute liste tenue à la main."""
    return sorted(tomllib.loads(p.read_text())["project"]["name"] for p in LAMBDAS_DIR.glob("*/pyproject.toml"))


def export(package: str, output: Path, *flags: str) -> Path:
    """Dépendances runtime du membre, versions exactes du lock (`--frozen` : le lock n'est jamais modifié)."""
    run(
        "uv",
        "export",
        "--package",
        package,
        "--no-dev",
        "--no-hashes",
        "--frozen",
        "--quiet",
        "-o",
        str(output),
        *flags,
    )
    return output


def install(package: str, target: Path, work: Path) -> None:
    common = [
        "--quiet",
        "--target",
        str(target),
        "--python-platform",
        PLATFORM,
        "--python-version",
        PYTHON_VERSION,
        "--no-installer-metadata",
        "--no-compile-bytecode",
    ]
    third_party = export(package, work / "third_party.txt", "--no-emit-workspace")
    run("uv", "pip", "install", *common, "--only-binary", ":all:", "-r", str(third_party))
    # Les membres apparaissent dans l'export comme des chemins locaux (`./packages/bodacc-client`).
    listing = export(package, work / "all.txt", "--no-editable").read_text().splitlines()
    members = [line.strip() for line in listing if line.startswith("./")]
    run("uv", "pip", "install", *common, "--no-deps", *members)


def write_zip(source: Path, archive: Path) -> None:
    files = sorted(p for p in source.rglob("*") if p.is_file() and not EXCLUDED_DIRS & set(p.relative_to(source).parts))
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=FIXED_DATE)
            info.external_attr = 0o644 << 16  # rw-r--r-- : lisible par l'utilisateur du runtime
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())


def build(package: str) -> Path:
    BUILD_DIR.mkdir(exist_ok=True)
    archive = BUILD_DIR / f"{package}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        work, target = Path(tmp), Path(tmp) / "package"
        install(package, target, work)
        write_zip(target, archive)
    return archive


def publish(s3, bucket: str, package: str, archive: Path) -> str:
    """Envoie le zip sous son hash s'il n'y est pas déjà, puis met à jour le pointeur s'il a changé."""
    data = archive.read_bytes()
    digest = hashlib.sha256(data)
    key = f"lambdas/{package}/{digest.hexdigest()}.zip"
    pointer_key = f"lambdas/{package}/current.json"

    existing = s3.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1).get("KeyCount", 0)
    if not existing:
        s3.upload_file(str(archive), bucket, key, ExtraArgs={"ContentType": "application/zip"})

    try:
        current = json.loads(s3.get_object(Bucket=bucket, Key=pointer_key)["Body"].read())
    except s3.exceptions.NoSuchKey:
        current = {}
    if current.get("key") == key:
        return f"à jour ({key})"

    pointer = {
        "key": key,
        # Même calcul que `filebase64sha256()` de Terraform : source_code_hash de la fonction.
        "base64sha256": base64.b64encode(digest.digest()).decode(),
        "size": len(data),
        "git_commit": run("git", "rev-parse", "HEAD"),
        "git_dirty": bool(run("git", "status", "--porcelain")),
        "published_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    s3.put_object(
        Bucket=bucket,
        Key=pointer_key,
        Body=json.dumps(pointer, indent=2).encode(),
        ContentType="application/json",  # sinon le data source aws_s3_object de Terraform ne lit pas le corps
    )
    return f"{'déjà envoyé' if existing else 'envoyé'}, pointeur → {key}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("packages", nargs="*", help="noms des membres (défaut : toutes les Lambdas de lambdas/*)")
    parser.add_argument("--publish", action="store_true", help="envoie les zips dans le bucket artefacts")
    parser.add_argument("--profile", default=None, help="profil AWS CLI (absent en CI : identifiants OIDC)")
    args = parser.parse_args()

    known = lambda_names()
    unknown = sorted(set(args.packages) - set(known))
    if unknown:
        parser.error(f"Lambda inconnue : {', '.join(unknown)} (connues : {', '.join(known)})")

    s3 = bucket = None
    if args.publish:
        import boto3  # seulement pour publier : le build seul ne demande pas d'identifiants AWS

        session = boto3.Session(profile_name=args.profile, region_name=REGION)
        bucket = f"data-platform-artifacts-{session.client('sts').get_caller_identity()['Account']}"
        s3 = session.client("s3")

    for package in args.packages or known:
        archive = build(package)
        size = archive.stat().st_size / 1e6
        status = publish(s3, bucket, package, archive) if args.publish else "non publié"
        print(f"{package} : {archive.relative_to(ROOT)} {size:.1f} Mo, {status}")


if __name__ == "__main__":
    main()
