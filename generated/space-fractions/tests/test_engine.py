"""Unit tests for the Space Fractions game engine."""

import unittest

from space_fractions.engine import GameEngine


class GameEngineTests(unittest.TestCase):
    def make_engine(self, count: int = 4, lives: int = 3) -> GameEngine:
        engine = GameEngine(question_count=count, starting_lives=lives, seed=7)
        engine.start_new_game()
        return engine

    def test_new_game_starts_active_with_expected_state(self) -> None:
        engine = self.make_engine(4, 3)
        self.assertFalse(engine.finished)
        self.assertEqual(engine.score, 0)
        self.assertEqual(engine.lives, 3)
        self.assertIsNotNone(engine.current_question)
        self.assertEqual(engine.remaining_questions, 4)

    def test_correct_answer_awards_points_and_advances(self) -> None:
        engine = self.make_engine()
        first = engine.current_question
        outcome = engine.submit_answer(first.correct_index)
        self.assertTrue(outcome.correct)
        self.assertGreater(outcome.points_awarded, 0)
        self.assertEqual(engine.score, outcome.points_awarded)
        self.assertEqual(engine.lives, 3)
        self.assertEqual(engine.streak, 1)
        self.assertEqual(engine.answered, 1)
        self.assertIsNotNone(engine.current_question)

    def test_wrong_answer_loses_life_and_resets_streak(self) -> None:
        engine = self.make_engine()
        first = engine.current_question
        wrong = (first.correct_index + 1) % len(first.choices)
        outcome = engine.submit_answer(wrong)
        self.assertFalse(outcome.correct)
        self.assertEqual(outcome.points_awarded, 0)
        self.assertEqual(engine.lives, 2)
        self.assertEqual(engine.streak, 0)
        self.assertEqual(engine.score, 0)

    def test_streak_bonus_grows_until_cap(self) -> None:
        engine = GameEngine(
            question_count=6,
            starting_lives=3,
            base_points=10,
            difficulty_bonus=5,
            streak_bonus=2,
            max_streak_bonus=5,
            seed=11,
        )
        engine.start_new_game()
        total = 0
        previous_streak = 0
        for _ in range(4):
            question = engine.current_question
            self.assertIsNotNone(question)
            outcome = engine.submit_answer(question.correct_index)
            self.assertTrue(outcome.correct)
            total += outcome.points_awarded
            if previous_streak == 0:
                self.assertEqual(outcome.points_awarded, 10 + (question.difficulty - 1) * 5)
            else:
                expected_bonus = min(previous_streak, 5) * 2
                self.assertEqual(
                    outcome.points_awarded,
                    10 + (question.difficulty - 1) * 5 + expected_bonus,
                )
            previous_streak = engine.streak
        self.assertEqual(engine.score, total)

    def test_timeout_is_incorrect_and_loses_life(self) -> None:
        engine = self.make_engine()
        outcome = engine.time_out()
        self.assertFalse(outcome.correct)
        self.assertTrue(outcome.timed_out)
        self.assertEqual(engine.lives, 2)
        self.assertEqual(engine.score, 0)

    def test_game_ends_when_lives_reach_zero(self) -> None:
        engine = self.make_engine(count=10, lives=2)
        while engine.lives > 0:
            question = engine.current_question
            self.assertIsNotNone(question)
            wrong = (question.correct_index + 1) % len(question.choices)
            engine.submit_answer(wrong)
        self.assertTrue(engine.finished)
        self.assertEqual(engine.lives, 0)
        self.assertIsNone(engine.current_question)

    def test_game_ends_after_all_questions(self) -> None:
        engine = self.make_engine(count=3, lives=5)
        while not engine.finished:
            question = engine.current_question
            self.assertIsNotNone(question)
            engine.submit_answer(question.correct_index)
        self.assertTrue(engine.finished)
        self.assertEqual(engine.answered, 3)
        self.assertEqual(engine.correct_answers, 3)
        self.assertIsNone(engine.current_question)

    def test_restart_resets_all_progress(self) -> None:
        engine = self.make_engine(count=3, lives=3)
        first = engine.current_question
        engine.submit_answer((first.correct_index + 1) % len(first.choices))
        engine.start_new_game()
        self.assertFalse(engine.finished)
        self.assertEqual(engine.score, 0)
        self.assertEqual(engine.lives, 3)
        self.assertEqual(engine.answered, 0)
        self.assertEqual(engine.correct_answers, 0)
        self.assertIsNotNone(engine.current_question)

    def test_submit_with_no_current_question_raises(self) -> None:
        engine = GameEngine(question_count=1, starting_lives=1, seed=5)
        # Not started.
        with self.assertRaises(RuntimeError):
            engine.submit_answer(0)

    def test_final_percentage_uses_question_count(self) -> None:
        engine = self.make_engine(count=4, lives=5)
        engine.submit_answer(engine.current_question.correct_index)
        self.assertEqual(engine.final_percentage(), 25.0)


if __name__ == "__main__":
    unittest.main()
