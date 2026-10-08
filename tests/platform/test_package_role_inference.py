from referee.ingestion.bundle import infer_role


def test_manuscript_name_is_not_misclassified_as_script_code():
    assert infer_role("manuscript.pdf") == "manuscript"
    assert infer_role("main_manuscript.docx") == "manuscript"


def test_role_hints_use_tokens_not_arbitrary_substrings():
    assert infer_role("metadata_study.pdf") == "manuscript"
    assert infer_role("study_data.xlsx") == "data"
    assert infer_role("supplementary_material.docx") == "supplement"
    assert infer_role("response_to_reviewers.docx") == "rebuttal"
    assert infer_role("reviewer_comments.docx") == "reviewer_comments"


def test_code_extension_takes_precedence_over_filename_hints():
    assert infer_role("data_analysis.py") == "code"
    assert infer_role("reviewer_script.ipynb") == "code"
