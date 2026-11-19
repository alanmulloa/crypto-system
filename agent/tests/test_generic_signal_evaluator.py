from app.evaluation.generic_signal_evaluator import evaluate_operator


def test_generic_rule_operators():
    assert evaluate_operator(0.7, "<=", 0.75)
    assert evaluate_operator(85.0, ">=", 85.0)
    assert evaluate_operator(20.0, "<", 30.0)
    assert evaluate_operator(4.6, ">", 4.5)
    assert evaluate_operator(
        "lower_highs_lower_lows",
        "==",
        "lower_highs_lower_lows",
    )
