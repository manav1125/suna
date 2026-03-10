from core.files.upload_handler import rewrite_attached_file_refs


def test_rewrite_attached_file_refs_updates_uploaded_file_markers():
    prompt = "Please review this file:\n[Uploaded File: uploads/report.pdf]"
    uploaded_files = [
        {
            "original_filename": "report.pdf",
            "reference_path": "uploads/report_1.pdf",
        }
    ]

    result = rewrite_attached_file_refs(prompt, uploaded_files)

    assert "[Uploaded File: uploads/report_1.pdf]" in result
    assert "[Uploaded File: uploads/report.pdf]" not in result
    assert "Attached file 'report.pdf' is stored at 'uploads/report_1.pdf'" in result


def test_rewrite_attached_file_refs_updates_arrow_style_markers():
    prompt = "[Attached: report.pdf (3.3 KB) -> uploads/report.pdf]"
    uploaded_files = [
        {
            "original_filename": "report.pdf",
            "reference_path": "uploads/report_1.pdf",
        }
    ]

    result = rewrite_attached_file_refs(prompt, uploaded_files)

    assert "-> uploads/report_1.pdf]" in result
    assert "-> uploads/report.pdf]" not in result


def test_rewrite_attached_file_refs_keeps_prompt_clean_when_no_rename():
    prompt = "[Uploaded File: uploads/report.pdf]"
    uploaded_files = [
        {
            "original_filename": "report.pdf",
            "reference_path": "uploads/report.pdf",
        }
    ]

    result = rewrite_attached_file_refs(prompt, uploaded_files)

    assert result == prompt
