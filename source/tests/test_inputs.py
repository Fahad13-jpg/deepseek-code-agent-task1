from pathlib import Path

import pytest

from codeagent.inputs import preprocess, read_markdown

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_supplied_files_are_preserved_and_all_diagrams_extracted():
    data = preprocess(EXAMPLES / "Architecture_Documentation.md", EXAMPLES / "Architecture_View.md")
    assert len(data["diagrams"]) == 13  # Eleven types; sequence and collaboration each have two examples.
    assert data["diagrams"][0]["name"] == "UseCaseDiagram"
    assert "AdminComponent" in data["views"]["text"]
    assert data["architecture"]["requirement_ids"] == ["ASR-1", "ASR-2", "FR-1", "NFR-1"]
    assert len(data["warnings"]) == 3
    assert len(data["architecture"]["sha256"]) == 64


def test_code_fence_headings_are_not_document_headings(tmp_path):
    file = tmp_path / "input.md"
    file.write_text("# Real\n```python\n# comment\n```\n## Next\n", encoding="utf-8")
    data = read_markdown(file)
    assert [s["title"] for s in data["sections"]] == ["Real", "Next"]
    assert data["code_blocks"][0]["content"] == "# comment"


@pytest.mark.parametrize("text", ["", "\x00bad", "# Heading\n```python\nunclosed"])
def test_rejects_invalid_documents(tmp_path, text):
    path = tmp_path / "bad.md"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        read_markdown(path)


def test_same_input_rejected():
    file = EXAMPLES / "Architecture_View.md"
    with pytest.raises(ValueError):
        preprocess(file, file)
