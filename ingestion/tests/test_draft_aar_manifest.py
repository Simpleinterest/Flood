import json

from scripts import draft_aar_manifest


def test_draft_pdf_paths_resolve_from_the_manifest(tmp_path):
    sources = tmp_path / "data" / "aar" / "sources"
    sources.mkdir(parents=True)
    pdf = sources / "report.pdf"
    pdf.write_bytes(b"not really a pdf")
    out = tmp_path / "data" / "aar" / "manifest.draft.json"

    assert draft_aar_manifest.main(["--sources", str(sources), "--output", str(out)]) == 0

    entry = json.loads(out.read_text())["documents"][0]
    assert entry["local_pdf_path"] == "sources/report.pdf"
    assert (out.parent / entry["local_pdf_path"]).resolve() == pdf.resolve()
