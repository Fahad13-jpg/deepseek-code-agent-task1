"""Game-state engine for Space Fractions.

The engine owns score, lives, streak, and question progression. It has no
Tkinter dependency, so the same rules are exercised directly by unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
import random

from .questions import FractionQuestion, generate_question_set


@dataclass(frozen=True)
class AnswerOutcome:
    """The result of submitting one answer."""

    correct: bool
    timed_out: bool
    points_awarded: int
    score: int
    lives_remaining: int
    streak: int
    game_over: bool
    correct_index: int
    selected_index: int
    explanation: str


class GameEngine:
    """Encapsulates one play-through of Space Fractions."""

    def __init__(
        self,
        question_count: int = 10,
        starting_lives: int = 3,
        base_points: int = 10,
        difficulty_bonus: int = 5,
        streak_bonus: int = 2,
        max_streak_bonus: int = 5,
        seed: int | None = None,
    ) -> None:
        self.question_count = int(question_count)
        self.starting_lives = int(starting_lives)
        self.base_points = int(base_points)
        self.difficulty_bonus = int(difficulty_bonus)
        self.streak_bonus = int(streak_bonus)
        self.max_streak_bonus = int(max_streak_bonus)
        self.seed = seed

        self.questions: list[FractionQuestion] = []
        self.score = 0
        self.lives = self.starting_lives
        self.streak = 0
        self.answered = 0
        self.correct_answers = 0
        self.finished = True
        self._cursor = 0

    def start_new_game(self) -> None:
        """Reset all state and generate a fresh question list."""
        rng = random.Random(self.seed)
        self.questions = generate_question_set(self.question_count, rng=rng)
        self.score = 0
        self.lives = self.starting_lives
        self.streak = 0
        self.answered = 0
        self.correct_answers = 0
        self.finished = False
        self._cursor = 0

    @property
    def current_question(self) -> FractionQuestion | None:
        if self.finished or not self.questions:
            return None
        if self._cursor >= len(self.questions):
            return None
        return self.questions[self._cursor]

    @property
    def remaining_questions(self) -> int:
        if self.finished:
            return 0
        return len(self.questions) - self._cursor

    @property
    def progress_text(self) -> str:
        if not self.questions:
            return "0/0"
        return f"{self.answered + 1}/{len(self.questions)}"

    def submit_answer(self, selected_index: int, timed_out: bool = False) -> AnswerOutcome:
        """Record the selected answer and advance the game.

        Raises ``RuntimeError`` if no question is currently available.
        """
        question = self.current_question
        if question is None:
            raise RuntimeError("No current question is available.")

        selected_index = int(selected_index)
        correct = selected_index == question.correct_index
        points = 0

        if correct:
            self.correct_answers += 1
            streak_before = self.streak
            self.streak += 1
            streak_amount = min(streak_before, self.max_streak_bonus) * self.streak_bonus
            points = (
                self.base_points
                + (question.difficulty - 1) * self.difficulty_bonus
                + streak_amount
            )
            self.score += points
        else:
            self.streak = 0
            self.lives = max(0, self.lives - 1)

        self.answered += 1
        self._cursor += 1

        game_over = (
            self.lives <= 0
            or self._cursor >= len(self.questions)
        )
        if game_over:
            self.finished = True

        return AnswerOutcome(
            correct=correct,
            timed_out=bool(timed_out),
            points_awarded=points,
            score=self.score,
            lives_remaining=self.lives,
            streak=self.streak,
            game_over=game_over,
            correct_index=question.correct_index,
            selected_index=selected_index,
            explanation=question.explanation,
        )

    def time_out(self) -> AnswerOutcome:
        """Submit a timeout as an incorrect answer without selecting a choice."""
        question = self.current_question
        if question is None:
            raise RuntimeError("No current question is available.")
        return self.submit_answer(-1, timed_out=True)

    def final_percentage(self) -> float:
        if self.question_count == 0:
            return 0.0
        return self.correct_answers / self.question_count * 100.0
