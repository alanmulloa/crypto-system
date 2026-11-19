from app.evaluation.generic_prospective_runner_cli import DAY_MS


def test_public_runner_day_constant():
    assert DAY_MS == 86_400_000
