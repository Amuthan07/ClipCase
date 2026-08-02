from eval.scorer import structural_accuracy


def test_all_actions_present_in_order():
    doc = "Verify user clicks Login. Verify user enters email. Verify user submits form."
    actions = ["clicks Login", "enters email", "submits form"]
    assert structural_accuracy(doc, actions) == 1.0


def test_missing_action_reduces_score():
    doc = "Verify user clicks Login. Verify user submits form."
    actions = ["clicks Login", "enters email", "submits form"]
    assert structural_accuracy(doc, actions) == 2 / 3


def test_out_of_order_action_not_credited():
    doc = "Verify user submits form. Verify user clicks Login."
    actions = ["clicks Login", "submits form"]
    # "clicks Login" matches first (cursor starts at 0), then "submits form" must be found
    # *after* that position - it isn't, since it appears earlier in the doc.
    assert structural_accuracy(doc, actions) == 0.5


def test_case_insensitive_matching():
    doc = "verify user CLICKS login"
    actions = ["Clicks Login"]
    assert structural_accuracy(doc, actions) == 1.0


def test_empty_ground_truth_returns_zero():
    assert structural_accuracy("anything", []) == 0.0


def test_no_matches_returns_zero():
    doc = "Nothing relevant here."
    actions = ["clicks Login", "submits form"]
    assert structural_accuracy(doc, actions) == 0.0
