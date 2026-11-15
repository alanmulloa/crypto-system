from app.evaluation.generic_prospective_runner import _net_return


def test_generic_net_return_applies_costs():
    gross_like = _net_return(
        100.0,
        101.0,
        fee_bps=10.0,
        slippage_bps=5.0,
    )
    assert 0.0 < gross_like < 1.0
