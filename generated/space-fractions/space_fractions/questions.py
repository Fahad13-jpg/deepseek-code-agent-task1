"""Question generation for Space Fractions.

The game is deliberately self-contained and local. Question generation is kept
separate from the UI and game-state engine so the mathematical rules can be
tested without a display or timer.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import random
from typing import Sequence


@dataclass(frozen=True)
class FractionQuestion:
    """One multiple-choice fraction question.

    ``correct_index`` points into ``choices``. ``operands`` and ``answer`` are
    retained for explanations and tests; the UI only needs to render choices.
    """

    kind: str
    prompt: str
    choices: tuple[str, ...]
    correct_index: int
    explanation: str
    difficulty: int
    operands: tuple[Fraction, ...]
    answer: Fraction


def format_fraction(value: Fraction) -> str:
    """Return a compact human-readable fraction, e.g. ``3/4`` or ``2``."""
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _random_fraction(rng: random.Random, max_numerator: int, max_denominator: int) -> Fraction:
    numerator = rng.randint(1, max_numerator)
    denominator = rng.randint(2, max_denominator)
    return Fraction(numerator, denominator)


def _distinct_fractions(
    rng: random.Random,
    count: int,
    max_numerator: int,
    max_denominator: int,
) -> list[Fraction]:
    """Return ``count`` distinct fractions by value."""
    values: list[Fraction] = []
    attempts = 0
    while len(values) < count and attempts < 500:
        candidate = _random_fraction(rng, max_numerator, max_denominator)
        attempts += 1
        if candidate not in values:
            values.append(candidate)
    if len(values) < count:
        # Deterministic fallback; avoids an infinite loop if the random range
        # is too small for the requested number of distinct values.
        fallback = [Fraction(1, 2), Fraction(1, 3), Fraction(2, 3), Fraction(3, 4)]
        for candidate in fallback:
            if candidate not in values:
                values.append(candidate)
            if len(values) == count:
                break
    return values[:count]


def _scale_for_difficulty(difficulty: int) -> tuple[int, int]:
    """Map 1..3 to numerator/denominator limits for generation."""
    if difficulty <= 1:
        return 6, 8
    if difficulty == 2:
        return 10, 12
    return 15, 16


def generate_compare(difficulty: int, rng: random.Random) -> FractionQuestion:
    """Ask the player to identify the largest of four fractions."""
    max_num, max_den = _scale_for_difficulty(difficulty)
    values = _distinct_fractions(rng, 4, max_num, max_den)
    answer = max(values)
    choices = tuple(format_fraction(v) for v in values)
    correct_index = values.index(answer)
    return FractionQuestion(
        kind="compare",
        prompt="Which fraction has the greatest value?",
        choices=choices,
        correct_index=correct_index,
        explanation=f"The largest value is {format_fraction(answer)}.",
        difficulty=difficulty,
        operands=tuple(values),
        answer=answer,
    )


def generate_equivalent(difficulty: int, rng: random.Random) -> FractionQuestion:
    """Ask the player to choose a fraction equivalent to the target."""
    max_num, max_den = _scale_for_difficulty(difficulty)
    target = _random_fraction(rng, max_num, max_den)

    # One correct equivalent fraction plus three plausible distractors.
    scale = rng.randint(2, 4)
    correct = target * scale
    distractors = _distinct_fractions(rng, 3, max_num * scale, max_den * scale)
    while correct in distractors:
        distractors = _distinct_fractions(rng, 3, max_num * scale, max_den * scale)

    values = [correct] + distractors
    rng.shuffle(values)
    choices = tuple(format_fraction(v) for v in values)
    correct_index = values.index(correct)
    return FractionQuestion(
        kind="equivalent",
        prompt=f"Which fraction is equivalent to {format_fraction(target)}?",
        choices=choices,
        correct_index=correct_index,
        explanation=(
            f"{format_fraction(target)} is equivalent to {format_fraction(correct)}."
        ),
        difficulty=difficulty,
        operands=(target,),
        answer=correct,
    )


def generate_arithmetic(difficulty: int, rng: random.Random) -> FractionQuestion:
    """Ask a fraction addition, subtraction, or multiplication problem."""
    max_num, max_den = _scale_for_difficulty(difficulty)
    left = _random_fraction(rng, max_num, max_den)
    right = _random_fraction(rng, max_num, max_den)

    if difficulty == 1:
        operation = "+"
        answer = left + right
    elif difficulty == 2:
        operation = "-"
        if left < right:
            left, right = right, left
        answer = left - right
    else:
        operation = rng.choice(["+", "-", "×"])
        if operation == "+":
            answer = left + right
        elif operation == "-":
            if left < right:
                left, right = right, left
            answer = left - right
        else:
            answer = left * right

    distractors = _distinct_fractions(rng, 3, max_num * max_den, max_den * max_den)
    while answer in distractors:
        distractors = _distinct_fractions(rng, 3, max_num * max_den, max_den * max_den)

    values = [answer] + distractors
    rng.shuffle(values)
    choices = tuple(format_fraction(v) for v in values)
    correct_index = values.index(answer)

    symbol = operation
    prompt = f"What is {format_fraction(left)} {symbol} {format_fraction(right)}?"
    explanation = (
        f"{format_fraction(left)} {symbol} {format_fraction(right)} = "
        f"{format_fraction(answer)}."
    )
    return FractionQuestion(
        kind="arithmetic",
        prompt=prompt,
        choices=choices,
        correct_index=correct_index,
        explanation=explanation,
        difficulty=difficulty,
        operands=(left, right),
        answer=answer,
    )


def generate_question(
    difficulty: int | None = None,
    kind: str | None = None,
    rng: random.Random | None = None,
) -> FractionQuestion:
    """Generate a random question.

    ``rng`` defaults to a newly seeded ``random.Random`` for normal play, but
    callers (including tests) may provide a deterministic generator.
    """
    if rng is None:
        rng = random.Random()
    if difficulty is None:
        difficulty = rng.randint(1, 3)
    difficulty = max(1, min(3, int(difficulty)))

    kinds: Sequence[str] = ("compare", "equivalent", "arithmetic")
    if kind is None:
        kind = rng.choice(kinds)
    if kind not in kinds:
        raise ValueError(f"Unknown question kind: {kind}")

    if kind == "compare":
        return generate_compare(difficulty, rng)
    if kind == "equivalent":
        return generate_equivalent(difficulty, rng)
    return generate_arithmetic(difficulty, rng)


def generate_question_set(
    count: int = 10,
    rng: random.Random | None = None,
) -> list[FractionQuestion]:
    """Generate a complete randomized game question list."""
    if rng is None:
        rng = random.Random()
    questions: list[FractionQuestion] = []
    for index in range(int(count)):
        difficulty = 1 + (index % 3)
        questions.append(generate_question(difficulty=difficulty, rng=rng))
    return questions
