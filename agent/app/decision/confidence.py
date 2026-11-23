"""Calibrated confidence scoring for decisions.

Phase 2: Implements confidence calibration with Platt scaling or isotonic regression
fallback to heuristic score when calibration data is insufficient.
"""
from __future__ import annotations

import math
from typing import Any


class ConfidenceCalibrator:
    """Calibrates raw strategy scores to probabilities.

    Uses simple logistic calibration (Platt scaling) with online updates.
    Falls back to raw heuristic when insufficient calibration data.
    """

    def __init__(self, min_samples: int = 50):
        """Initialize calibrator.

        Args:
            min_samples: Minimum samples needed for calibration (default 50)
        """
        self.min_samples = min_samples
        self.a = 0.0  # Calibration parameter A
        self.b = 0.0  # Calibration parameter B
        self.samples: list[tuple[float, int]] = []  # (score, outcome)
        self._fitted = False

    def add_outcome(self, score: float, success: bool) -> None:
        """Add outcome for online calibration update.

        Args:
            score: Raw heuristic score (0-100)
            success: Whether the trade was profitable
        """
        self.samples.append((score, 1 if success else 0))
        if len(self.samples) >= self.min_samples and not self._fitted:
            self._fit()
        elif self._fitted:
            self._update_online(score, 1 if success else 0)

    def _fit(self) -> None:
        """Fit Platt scaling parameters using logistic regression."""
        if len(self.samples) < 10:
            return

        # Simple Platt scaling: P(y=1|score) = 1 / (1 + exp(A*score + B))
        # Use iterative method to find A, B
        pos_scores = [s for s, o in self.samples if o == 1]
        neg_scores = [s for s, o in self.samples if o == 0]

        if pos_scores and neg_scores:
            # Initialize A, B based on score distributions
            self.a = -0.1
            self.b = math.log(len(neg_scores) / len(pos_scores))

            # Simple gradient descent for Platt scaling
            for _ in range(100):
                grad_a = 0.0
                grad_b = 0.0
                for s, o in self.samples:
                    p = self._predict_raw(s)
                    error = p - o
                    grad_a += error * s
                    grad_b += error

                self.a -= 0.01 * grad_a
                self.b -= 0.01 * grad_b

                if abs(grad_a) < 0.001 and abs(grad_b) < 0.001:
                    break

            self._fitted = True

    def _update_online(self, score: float, outcome: int) -> None:
        """Online update of calibration parameters (single step)."""
        if not self._fitted:
            return
        p = self._predict_raw(score)
        error = p - outcome
        self.a -= 0.001 * error * score
        self.b -= 0.001 * error

    def _predict_raw(self, score: float) -> float:
        """Raw calibrated probability."""
        return 1.0 / (1.0 + math.exp(self.a * score + self.b))

    def calibrate(self, score: float) -> float:
        """Calibrate a raw score to 0-100 confidence.

        Args:
            score: Raw heuristic score (0-100)

        Returns:
            Calibrated confidence score (0-100)
        """
        if not self._fitted or len(self.samples) < self.min_samples:
            # Fallback: return heuristic score as-is
            return score

        prob = self._predict_raw(score)
        return prob * 100.0

    def get_stats(self) -> dict[str, Any]:
        """Get calibration statistics."""
        if not self.samples:
            return {"status": "no_data", "samples": 0}

        outcomes = [o for _, o in self.samples]
        return {
            "status": "calibrated" if self._fitted else "collecting",
            "samples": len(self.samples),
            "positive_rate": sum(outcomes) / len(outcomes) if outcomes else 0,
            "fitted": self._fitted,
            "params": {"a": self.a, "b": self.b} if self._fitted else None,
        }


def heuristic_confidence(
    aggregate_score: float,
    risk_approved: bool,
    conflict_ratio: float,
    volatility_score: float,
) -> float:
    """Compute heuristic confidence from multiple factors.

    Factors:
    - Aggregate strategy score (primary)
    - Risk approval (hard gate)
    - Signal conflict (reduces confidence)
    - Volatility (high volatility reduces confidence)

    Returns:
        Heuristic confidence 0-100
    """
    if not risk_approved:
        return 0.0

    # Base from aggregate score
    base = aggregate_score

    # Conflict penalty: linear reduction based on conflict ratio
    conflict_penalty = conflict_ratio * 30.0  # Up to 30 points

    # Volatility penalty: higher vol = lower confidence
    vol_penalty = volatility_score * 15.0  # Up to 15 points

    confidence = base - conflict_penalty - vol_penalty

    return max(0.0, min(100.0, confidence))