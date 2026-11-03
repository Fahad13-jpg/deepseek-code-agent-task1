"""Unit tests for fraction question generation."""

import random
import unittest
from fractions import Fraction

from space_fractions.questions import (
    FractionQuestion,
    format_fraction,
    generate_arithmetic,
    generate_compare,
    generate_equivalent,
    generate_question,
    generate_question_set,
)


class QuestionGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rng = random.Random(42)

    def test_format_fraction_reduces_and_handles_whole_numbers(self) -> None:
        self.assertEqual(format_fraction(Fraction(2, 4)), "1/2")
        self.assertEqual(format_fraction(Fraction(4, 2)), "2")
        self.assertEqual(format_fraction(Fraction(3, 5)), "3/5")

    def test_compare_question_has_four_distinct_choices(self) -> None:
        question = generate_compare(2, self.rng)
        self.assertEqual(len(question.choices), 4)
        self.assertEqual(len(set(question.choices)), 4)
        self.assertEqual(question.correct_index, question.choices.index(
            format_fraction(max(question.operands))
        ))

    def test_equivalent_question_contains_correct_scaled_value(self) -> None:
        for _ in range(20):
            question = generate_equivalent(1, self.rng)
            self.assertIn(question.correct_index, range(4))
            selected = Fraction(question.choices[question.correct_index])
            self.assertEqual(selected, question.answer)
            scale = selected / question.operands[0]
            self.assertEqual(scale.denominator, 1)
            self.assertIn(scale.numerator, (2, 3, 4))

    def test_arithmetic_question_correct_choice_matches_operation(self) -> None:
        for kind in ("+", "-", "×"):
            for _ in range(10):
                question = generate_arithmetic(3, self.rng)
                selected = Fraction(question.choices[question.correct_index])
                self.assertEqual(selected, question.answer)
                self.assertEqual(selected, question.answer)

    def test_generate_question_rejects_unknown_kind(self) -> None:
        with self.assertRaises(ValueError):
            generate_question(kind="impossible", rng=self.rng)

    def test_generate_question_set_has_requested_count(self) -> None:
        questions = generate_question_set(12, rng=self.rng)
        self.assertEqual(len(questions), 12)
        for question in questions:
            self.assertIsInstance(question, FractionQuestion)
            self.assertIn(question.correct_index, range(len(question.choices)))

    def test_difficulty_cycles_are_consistent(self) -> None:
        questions = generate_question_set(6, rng=self.rng)
        self.assertEqual([q.difficulty for q in questions], [1, 2, 3, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
