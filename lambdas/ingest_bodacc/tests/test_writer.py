import gzip
import hashlib
import json

from ingest_bodacc.writer import PartStats, write_jsonl_gz

ROWS = [
    {"id": "A202602011", "familleavis": "collective", "tribunal": "Greffe du Tribunal de Commerce de Bourg-en-Bresse"},
    {"id": "A202602012", "familleavis": "immatriculation", "commercant": "Société Générale de Négoce"},
    {"id": "B202602011", "familleavis": "radiation", "listepersonnes": None},
]


def test_une_ligne_json_par_annonce(tmp_path):
    path = tmp_path / "part-0001.jsonl.gz"

    write_jsonl_gz(ROWS, path)

    lines = gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()
    assert [json.loads(line) for line in lines] == ROWS


def test_accents_conserves_sans_echappement(tmp_path):
    path = tmp_path / "part.jsonl.gz"

    write_jsonl_gz(ROWS, path)

    raw = gzip.decompress(path.read_bytes())
    assert "Société Générale de Négoce".encode() in raw
    assert b"\\u00e9" not in raw


def test_memes_annonces_memes_octets_quel_que_soit_le_nom_du_fichier(tmp_path):
    # Le nom du fichier et l'heure vont dans l'en-tête gzip par défaut : les deux doivent être neutralisés.
    a, b = tmp_path / "tmpa1b2c3", tmp_path / "part-0001.jsonl.gz"

    write_jsonl_gz(ROWS, a)
    write_jsonl_gz(ROWS, b)

    assert a.read_bytes() == b.read_bytes()


def test_ordre_des_cles_sans_effet_sur_le_hash(tmp_path):
    inverse = [dict(reversed(list(row.items()))) for row in ROWS]

    s1 = write_jsonl_gz(ROWS, tmp_path / "a.gz")
    s2 = write_jsonl_gz(inverse, tmp_path / "b.gz")

    assert s1.sha256 == s2.sha256


def test_ordre_des_annonces_change_le_hash(tmp_path):
    # D'où `order_by=id` dans le client (étape 3) : le fichier dépend de l'ordre de lecture.
    s1 = write_jsonl_gz(ROWS, tmp_path / "a.gz")
    s2 = write_jsonl_gz(list(reversed(ROWS)), tmp_path / "b.gz")

    assert s1.sha256 != s2.sha256


def test_statistiques_du_fichier(tmp_path):
    path = tmp_path / "part.jsonl.gz"

    stats = write_jsonl_gz(ROWS, path)

    raw = gzip.decompress(path.read_bytes())
    assert stats == PartStats(
        count=3,
        sha256=hashlib.sha256(raw).hexdigest(),
        raw_bytes=len(raw),
        gz_bytes=path.stat().st_size,
    )


def test_consomme_un_generateur_en_un_seul_passage(tmp_path):
    stats = write_jsonl_gz((row for row in ROWS), tmp_path / "part.jsonl.gz")

    assert stats.count == 3


def test_journee_vide_fichier_gzip_valide(tmp_path):
    # Un dimanche : 0 annonce, mais un fichier lisible et un hash connu (celui du contenu vide).
    path = tmp_path / "part.jsonl.gz"

    stats = write_jsonl_gz([], path)

    assert gzip.decompress(path.read_bytes()) == b""
    assert stats.count == 0
    assert stats.sha256 == hashlib.sha256(b"").hexdigest()
