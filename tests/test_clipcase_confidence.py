from clipcase import export_markdown, parse_confidence_score, parse_markdown_table


def test_extracts_score_and_cleans_doc():
    raw = "| TC | ... |\n| TC-1 | ... |\n\nCONFIDENCE_SCORE: 0.87"
    doc, score = parse_confidence_score(raw)
    assert score == 0.87
    assert "CONFIDENCE_SCORE" not in doc
    assert doc == "| TC | ... |\n| TC-1 | ... |"


def test_handles_missing_line():
    raw = "| TC | ... |\n| TC-1 | ... |"
    doc, score = parse_confidence_score(raw)
    assert score is None
    assert doc == raw


def test_handles_integer_score():
    raw = "table\n\nCONFIDENCE_SCORE: 1"
    doc, score = parse_confidence_score(raw)
    assert score == 1.0
    assert doc == "table"


def test_export_markdown_includes_confidence_when_present(tmp_path):
    out = tmp_path / "test_cases.md"
    export_markdown(
        headers=["Test Case ID", "Test Case"],
        rows=[{"Test Case ID": "TC-1", "Test Case": "Verify login"}],
        output_path=str(out),
        video_name="demo.mov",
        flow_analysis="user logs in",
        confidence_score=0.87,
    )
    content = out.read_text()
    assert "Confidence (self-assessed by the model):** 87%" in content


def test_export_markdown_omits_confidence_when_none(tmp_path):
    out = tmp_path / "test_cases.md"
    export_markdown(
        headers=["Test Case ID", "Test Case"],
        rows=[{"Test Case ID": "TC-1", "Test Case": "Verify login"}],
        output_path=str(out),
        video_name="demo.mov",
        flow_analysis="user logs in",
    )
    content = out.read_text()
    assert "Confidence" not in content


def test_parse_markdown_table_tolerates_missing_wrapping_pipes():
    # Real Gemini output: no leading "|", and the trailing empty "Actual Outcome" cell is
    # dropped entirely rather than emitted as an empty "| |" cell.
    md = (
        "Test Case ID | Smoke | Test Case\n"
        "---|---|---\n"
        "GEN-001 | ☑ | Verify homepage loads. |\n"
        "GEN-002 | ☐ | Verify login form renders. |\n"
    )
    headers, rows = parse_markdown_table(md)
    assert headers == ["Test Case ID", "Smoke", "Test Case"]
    assert len(rows) == 2
    assert rows[0]["Test Case ID"] == "GEN-001"
    assert rows[0]["Test Case"] == "Verify homepage loads."


def test_parse_markdown_table_still_handles_fully_wrapped_rows():
    md = (
        "| Test Case ID | Smoke | Test Case |\n"
        "|---|---|---|\n"
        "| GEN-001 | ☑ | Verify homepage loads. |\n"
    )
    headers, rows = parse_markdown_table(md)
    assert headers == ["Test Case ID", "Smoke", "Test Case"]
    assert len(rows) == 1
    assert rows[0]["Test Case ID"] == "GEN-001"
