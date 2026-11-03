"""Tkinter desktop interface for Space Fractions."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from .engine import AnswerOutcome, GameEngine
from .questions import FractionQuestion
from .settings import load_settings

BG = "#070b1a"
PANEL = "#101731"
TEXT = "#eaf2ff"
MUTED = "#9fb3d1"
ACCENT = "#39d0ff"
CORRECT = "#3ddc84"
WRONG = "#ff5c7a"
BUTTON_BG = "#1b2652"
BUTTON_ACTIVE = "#283a75"


class SpaceFractionsApp(tk.Tk):
    """Main desktop application window and screen controller."""

    def __init__(self, settings_path: str = "config.json") -> None:
        super().__init__()
        self.title("Space Fractions")
        self.geometry("920x680")
        self.minsize(780, 620)
        self.configure(bg=BG)

        self.settings = load_settings(settings_path)
        self.engine: GameEngine | None = None
        self.screen = "menu"

        self._timer_job: str | None = None
        self._feedback_job: str | None = None
        self._answering = False
        self._time_left = self.settings["seconds_per_question"]
        self._last_outcome: AnswerOutcome | None = None

        self._title_font = tkfont.Font(family="Arial", size=30, weight="bold")
        self._heading_font = tkfont.Font(family="Arial", size=20, weight="bold")
        self._body_font = tkfont.Font(family="Arial", size=13)
        self._question_font = tkfont.Font(family="Arial", size=18, weight="bold")
        self._button_font = tkfont.Font(family="Arial", size=13, weight="bold")

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.bind("<KeyPress>", self._on_key)
        self.show_main_menu()

    # ------------------------------------------------------------------
    # Screen management
    # ------------------------------------------------------------------
    def _clear_container(self) -> None:
        self._cancel_jobs()
        for child in self.container.winfo_children():
            child.destroy()

    def _cancel_jobs(self) -> None:
        for job in (self._timer_job, self._feedback_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self._timer_job = None
        self._feedback_job = None

    def show_main_menu(self) -> None:
        self._clear_container()
        self.screen = "menu"

        title = tk.Label(
            self.container,
            text="SPACE FRACTIONS",
            font=self._title_font,
            bg=BG,
            fg=ACCENT,
        )
        title.pack(pady=(80, 8))

        subtitle = tk.Label(
            self.container,
            text="A fraction-skills training mission",
            font=self._body_font,
            bg=BG,
            fg=MUTED,
        )
        subtitle.pack(pady=(0, 40))

        self._menu_button("▶  Start Mission", self.start_game).pack(pady=8)
        self._menu_button("?  Help", self.show_help).pack(pady=8)
        self._menu_button("✕  Quit", self.destroy).pack(pady=8)

        hint = tk.Label(
            self.container,
            text="Keyboard: P = play   H = help   Q = quit",
            font=self._body_font,
            bg=BG,
            fg=MUTED,
        )
        hint.pack(side="bottom", pady=24)

    def show_help(self) -> None:
        self._clear_container()
        self.screen = "help"

        title = tk.Label(
            self.container,
            text="Mission Briefing",
            font=self._heading_font,
            bg=BG,
            fg=ACCENT,
        )
        title.pack(pady=(50, 16))

        lines = [
            "Answer 10 fraction questions to complete your mission.",
            "You have 3 lives and 30 seconds for each question.",
            "Use the buttons or press keys 1, 2, 3, and 4.",
            "Correct answers earn points. Streaks earn bonus points.",
            "A wrong answer or timeout costs one life.",
            "The mission ends when questions are done or lives reach zero.",
        ]
        for line in lines:
            tk.Label(
                self.container,
                text=line,
                font=self._body_font,
                bg=BG,
                fg=TEXT,
                justify="left",
            ).pack(anchor="w", padx=140, pady=4)

        self._menu_button("←  Back to Menu", self.show_main_menu).pack(pady=(30, 10))
        hint = tk.Label(
            self.container,
            text="Keyboard: B = back",
            font=self._body_font,
            bg=BG,
            fg=MUTED,
        )
        hint.pack(side="bottom", pady=16)

    def start_game(self) -> None:
        self._clear_container()
        self.screen = "game"

        self.engine = GameEngine(
            question_count=self.settings["question_count"],
            starting_lives=self.settings["starting_lives"],
            base_points=self.settings["base_points"],
            difficulty_bonus=self.settings["difficulty_bonus"],
            streak_bonus=self.settings["streak_bonus"],
            max_streak_bonus=self.settings["max_streak_bonus"],
        )
        self.engine.start_new_game()
        self._last_outcome = None
        self._answering = False

        self._build_game_screen()
        self._load_question()

    def _build_game_screen(self) -> None:
        assert self.engine is not None

        hud = tk.Frame(self.container, bg=PANEL, padx=18, pady=12)
        hud.pack(fill="x")

        self.score_label = tk.Label(
            hud, text="Score: 0", font=self._body_font, bg=PANEL, fg=TEXT
        )
        self.score_label.pack(side="left", padx=8)

        self.lives_label = tk.Label(
            hud,
            text=self._lives_text(),
            font=self._body_font,
            bg=PANEL,
            fg=WRONG,
        )
        self.lives_label.pack(side="left", padx=8)

        self.progress_label = tk.Label(
            hud, text="", font=self._body_font, bg=PANEL, fg=TEXT
        )
        self.progress_label.pack(side="left", padx=8)

        self.timer_label = tk.Label(
            hud,
            text=f"Time: {self.settings['seconds_per_question']}",
            font=self._body_font,
            bg=PANEL,
            fg=ACCENT,
        )
        self.timer_label.pack(side="right", padx=8)

        self.space_canvas = tk.Canvas(
            self.container, height=130, bg="#04060f", highlightthickness=0
        )
        self.space_canvas.pack(fill="x")
        self._draw_starfield()
        self._draw_rocket()

        self.prompt_label = tk.Label(
            self.container,
            text="",
            font=self._question_font,
            bg=BG,
            fg=TEXT,
            wraplength=820,
            justify="center",
        )
        self.prompt_label.pack(pady=(18, 12))

        self.feedback_label = tk.Label(
            self.container,
            text="",
            font=self._body_font,
            bg=BG,
            fg=MUTED,
            wraplength=820,
            justify="center",
        )
        self.feedback_label.pack(pady=(0, 14))

        answers = tk.Frame(self.container, bg=BG)
        answers.pack()
        self.answer_buttons: list[tk.Button] = []
        for index in range(4):
            button = tk.Button(
                answers,
                text="",
                font=self._button_font,
                width=30,
                height=2,
                bg=BUTTON_BG,
                fg=TEXT,
                activebackground=BUTTON_ACTIVE,
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                command=lambda selected=index: self._on_answer(selected),
            )
            button.grid(row=index // 2, column=index % 2, padx=8, pady=6)
            self.answer_buttons.append(button)

        hint = tk.Label(
            self.container,
            text="Press 1-4 to answer · 30 seconds per question",
            font=self._body_font,
            bg=BG,
            fg=MUTED,
        )
        hint.pack(side="bottom", pady=14)

    # ------------------------------------------------------------------
    # Question flow
    # ------------------------------------------------------------------
    def _load_question(self) -> None:
        assert self.engine is not None
        question = self.engine.current_question
        if question is None:
            self.show_game_over()
            return

        self._cancel_jobs()
        self._answering = False
        self._last_outcome = None

        self.prompt_label.configure(text=question.prompt)
        self.feedback_label.configure(text="Choose an answer or press 1-4.", fg=MUTED)
        self._update_hud(question)

        for index, button in enumerate(self.answer_buttons):
            if index < len(question.choices):
                button.configure(
                    text=f"{index + 1}.  {question.choices[index]}",
                    state="normal",
                    bg=BUTTON_BG,
                    fg=TEXT,
                )
            else:
                button.configure(text="", state="disabled")

        self._time_left = int(self.settings["seconds_per_question"])
        self._schedule_tick()

    def _schedule_tick(self) -> None:
        if self._timer_job is not None:
            try:
                self.after_cancel(self._timer_job)
            except tk.TclError:
                pass
        self._timer_job = self.after(1000, self._tick)

    def _tick(self) -> None:
        self._time_left -= 1
        self.timer_label.configure(text=f"Time: {max(0, self._time_left)}")
        if self._time_left <= 0:
            self._timer_job = None
            self._on_timeout()
        else:
            self._schedule_tick()

    def _on_answer(self, selected_index: int) -> None:
        if self._answering or self.engine is None or self.engine.current_question is None:
            return
        self._submit(selected_index, timed_out=False)

    def _on_timeout(self) -> None:
        if self._answering or self.engine is None or self.engine.current_question is None:
            return
        self._submit(None, timed_out=True)

    def _submit(self, selected_index: int | None, timed_out: bool) -> None:
        assert self.engine is not None
        self._cancel_jobs()
        self._answering = True

        for button in self.answer_buttons:
            button.configure(state="disabled")

        if timed_out:
            outcome = self.engine.time_out()
            feedback = "Time expired! The correct answer is shown below."
            color = WRONG
        else:
            assert selected_index is not None
            outcome = self.engine.submit_answer(selected_index)
            if outcome.correct:
                feedback = f"Correct! +{outcome.points_awarded} points."
                color = CORRECT
            else:
                feedback = "Not quite. The correct answer is shown below."
                color = WRONG

        self._last_outcome = outcome
        self._paint_result(outcome)
        self.feedback_label.configure(
            text=f"{feedback}\n{outcome.explanation}",
            fg=color,
        )
        self._update_hud(self.engine.current_question)
        self._draw_rocket()

        self._feedback_job = self.after(
            int(self.settings["feedback_delay_ms"]),
            self._after_feedback,
        )

    def _paint_result(self, outcome: AnswerOutcome) -> None:
        for index, button in enumerate(self.answer_buttons):
            if index == outcome.correct_index:
                button.configure(bg=CORRECT, fg="#04130b")
            elif index == outcome.selected_index:
                button.configure(bg=WRONG, fg="#1c0207")
            else:
                button.configure(bg="#0c1226", fg=MUTED)

    def _after_feedback(self) -> None:
        self._feedback_job = None
        if self._last_outcome is not None and self._last_outcome.game_over:
            self.show_game_over()
        else:
            self._load_question()

    def _update_hud(self, question: FractionQuestion | None) -> None:
        assert self.engine is not None
        self.score_label.configure(text=f"Score: {self.engine.score}")
        self.lives_label.configure(text=self._lives_text(), fg=WRONG)
        if question is not None:
            self.progress_label.configure(
                text=f"Question {self.engine.answered + 1}/{self.engine.question_count}"
            )

    def _lives_text(self) -> str:
        assert self.engine is not None
        return f"Lives: {'♥' * self.engine.lives}{'·' * (self.engine.starting_lives - self.engine.lives)}"

    # ------------------------------------------------------------------
    # Space visuals
    # ------------------------------------------------------------------
    def _draw_starfield(self) -> None:
        self.space_canvas.delete("all")
        width = max(self.space_canvas.winfo_width(), 900)
        height = 130
        for x in range(0, width, 36):
            for y in (18, 58, 98, 122):
                self.space_canvas.create_oval(x, y, x + 1, y + 1, fill="#8090b5", outline="")

    def _draw_rocket(self) -> None:
        if not hasattr(self, "space_canvas"):
            return
        width = max(self.space_canvas.winfo_width(), 900)
        self.space_canvas.delete("rocket")
        if self.engine is None:
            return

        progress = min(1.0, self.engine.answered / max(1, self.engine.question_count))
        x = 35 + progress * (width - 70)
        y = 70
        self.space_canvas.create_polygon(
            x, y - 20,
            x, y + 16,
            x + 38, y - 2,
            fill="#39d0ff",
            outline="#dff6ff",
            tags="rocket",
        )
        self.space_canvas.create_oval(
            x + 12, y - 4, x + 26, y + 10, fill="#101731", outline="", tags="rocket"
        )

    # ------------------------------------------------------------------
    # Game over
    # ------------------------------------------------------------------
    def show_game_over(self) -> None:
        self._clear_container()
        self.screen = "gameover"
        assert self.engine is not None

        title = tk.Label(
            self.container,
            text="MISSION COMPLETE" if self.engine.lives > 0 else "MISSION FAILED",
            font=self._title_font,
            bg=BG,
            fg=CORRECT if self.engine.lives > 0 else WRONG,
        )
        title.pack(pady=(60, 18))

        percentage = self.engine.final_percentage()
        rank = self._rank_for(percentage)
        stats = (
            f"Final Score: {self.engine.score}\n"
            f"Correct: {self.engine.correct_answers} / {self.engine.question_count}\n"
            f"Accuracy: {percentage:.0f}%\n"
            f"Rank: {rank}"
        )
        tk.Label(
            self.container,
            text=stats,
            font=self._heading_font,
            bg=BG,
            fg=TEXT,
            justify="center",
        ).pack(pady=14)

        self._menu_button("↻  Play Again", self.start_game).pack(pady=8)
        self._menu_button("⌂  Main Menu", self.show_main_menu).pack(pady=8)
        self._menu_button("✕  Quit", self.destroy).pack(pady=8)

        tk.Label(
            self.container,
            text="Keyboard: R = play again   M = main menu",
            font=self._body_font,
            bg=BG,
            fg=MUTED,
        ).pack(side="bottom", pady=18)

    @staticmethod
    def _rank_for(percentage: float) -> str:
        if percentage >= 90:
            return "Ace Pilot"
        if percentage >= 75:
            return "Flight Commander"
        if percentage >= 50:
            return "Cadet"
        return "Rookie"

    # ------------------------------------------------------------------
    # Shared widgets and keyboard
    # ------------------------------------------------------------------
    def _menu_button(self, text: str, command) -> tk.Button:
        return tk.Button(
            self.container,
            text=text,
            font=self._button_font,
            width=28,
            height=2,
            bg=BUTTON_BG,
            fg=TEXT,
            activebackground=BUTTON_ACTIVE,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            command=command,
        )

    def _on_key(self, event: tk.Event) -> None:
        key = event.char.lower()
        if self.screen == "menu":
            if key == "p":
                self.start_game()
            elif key == "h":
                self.show_help()
            elif key == "q":
                self.destroy()
        elif self.screen == "help":
            if key in ("b", "\r", " "):
                self.show_main_menu()
        elif self.screen == "game":
            if key in ("1", "2", "3", "4") and not self._answering:
                self._on_answer(int(key) - 1)
        elif self.screen == "gameover":
            if key == "r":
                self.start_game()
            elif key == "m":
                self.show_main_menu()


def run() -> None:
    """Launch the desktop application."""
    app = SpaceFractionsApp()
    app.mainloop()


if __name__ == "__main__":
    run()
