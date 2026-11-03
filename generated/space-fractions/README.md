# Space Fractions

Space Fractions is a small, self-contained native desktop game for practicing
sixth-grade fraction skills. The player answers ten multiple-choice fraction
questions while managing a score, a three-life budget, and a per-question
timer.

The supplied architecture documentation described a cloud microservices/web
learning tool. Because this deliverable is explicitly a playable native desktop
game with no web front end, the implementation intentionally adapts those
component boundaries to a local Tkinter application:

| Architecture concept | Implementation |
| --- | --- |
| `GameComponent` | `space_fractions/engine.py` + `space_fractions/gui.py` |
| `QuestionComponent` | `space_fractions/questions.py` |
| `UserComponent` / play-game flow | local player session in `GameEngine` |
| Admin "update questions" workflow | represented by generated question rules and optional `config.json`; there is no separate admin UI |
| Cloud services (Redis, PostgreSQL, OAuth2, k8s) | not used in the desktop build; local-only configuration is the sensible replacement |

## Requirements

- Python 3.10 or newer
- Tkinter, which is included with the standard Python installer on Windows and macOS.
  - Debian/Ubuntu: `sudo apt-get install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`

No third-party Python packages are required.

## Setup

```bash
# Optional: create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# No package installation is needed for the game or its tests.
```

## Run the game

```bash
python main.py
```

Or:

```bash
python -m space_fractions.gui
```

## Controls

- Main menu: click **Start Mission**, **Help**, or **Quit**.
- During a question: click an answer button or press `1`, `2`, `3`, or `4`.
- Each question has 30 seconds. A timeout counts as a wrong answer.
- Game over: click **Play Again** or press `R`; click **Main Menu** or press `M`.

## Scoring and feedback

- Correct answer: `10 + 5 * (difficulty - 1) + streak bonus` points.
- Streak bonus: `2` points per previous correct answer, capped at five previous
  answers (`max_streak_bonus = 5`).
- Wrong answer or timeout: no points, streak resets, and one life is lost.
- The game ends after all questions are answered or lives reach zero.
- The final screen shows score, correct count, accuracy, and a rank:
  Ace Pilot, Flight Commander, Cadet, or Rookie.

## Configuration

The game runs with built-in defaults and does not require a configuration file.
To customize gameplay, copy `config.example.json` to `config.json` in the
project root and edit it. Invalid or missing values fall back to safe defaults.

```json
{
  "question_count": 10,
  "starting_lives": 3,
  "seconds_per_question": 30,
  "base_points": 10,
  "difficulty_bonus": 5,
  "streak_bonus": 2,
  "max_streak_bonus": 5,
  "feedback_delay_ms": 1700
}
```

## Run the tests

The test suite uses only Python's standard-library `unittest`:

```bash
python -m unittest discover -s tests -v
```

The tests cover the core rules: fraction generation, correct answers, scoring,
lives, streaks, timeout behavior, game-over conditions, and restart.

## Directory structure

```text
.
├── main.py                    # Desktop entry point
├── requirements.txt           # Dependency manifest (stdlib only)
├── config.example.json        # Optional gameplay settings example
├── README.md
├── space_fractions/
│   ├── __init__.py
│   ├── engine.py              # Game state, score, lives, streak, progression
│   ├── questions.py           # Fraction question generation
│   ├── settings.py            # Defaults and optional JSON overrides
│   └── gui.py                 # Tkinter screens, controls, timer, feedback
└── tests/
    ├── __init__.py
    ├── test_engine.py         # Core game-rule tests
    └── test_questions.py      # Question-generation tests
```

## Requirements-to-code mapping

- **Play game (FR-1 / `PlayGame` use case):** `gui.py` main menu and mission
  screen, `engine.py` play session.
- **View score (ViewScore use case):** HUD and final game-over screen.
- **View help (ViewHelp use case):** Help screen in `gui.py`.
- **Question management (QuestionComponent / Update Questions):**
  `questions.py` generates valid fraction questions. Custom behavior is
  available through `config.json`; no admin editor is implemented.
- **Game state ownership:** `GameEngine` owns score, lives, streak, and cursor.
- **Question ownership:** `questions.py` owns question data generation and
  validation.

## Manual smoke-test checklist

1. Run `python main.py` from the project root.
2. Verify the main menu appears with title and three buttons.
3. Click **Help**, verify instructions, then return to the menu.
4. Click **Start Mission**.
5. Verify the first question, four answers, score, lives, timer, and rocket are visible.
6. Answer correctly with a mouse click and verify positive feedback and score.
7. Answer another question with a keyboard key (`1`-`4`).
8. Let one question time out and verify a life is lost.
9. Finish or lose all lives, then verify the final score screen appears.
10. Click **Play Again** and verify a fresh mission starts.
11. Run `python -m unittest discover -s tests -v` and verify all tests pass.

## Assumptions and known limitations

- The cloud architecture, multi-user authentication, and separate admin UI are
  intentionally out of scope for this local desktop build.
- The documented 99.99% uptime and 1% error budget conflict. For a local game
  this is not meaningful; the README uses the local desktop assumption instead.
- Question generation is random and not persisted to a database. Each game is
  a fresh in-memory session.
- The GUI has been written for desktop Tkinter and is not a web application.
- Tests validate core rules and question mathematics, not pixel-level UI
  behavior. Automated GUI interaction tests are not included.
