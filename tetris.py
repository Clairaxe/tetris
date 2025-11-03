from expyriment import design, control, stimuli, misc
from expyriment.misc.constants import C_WHITE, C_BLACK, K_SPACE
import os, sys, random

"""
Confusing Possible Objects for Actual Objects:

Task: Go/No-Go — press SPACE only when the full 5x5 square appears (target).
Other stimuli (potential, no_potential, bottom-only) require no response.

Timing: 
- Stimulus on screen for 600 ms
- Then blank for 1200 ms
- Responses accepted for entire 1800 ms
- Feedback flash (if any) lasts 200 ms

Trial structure:
- 24 target
- 24 potential (6 images x 4 repetitions)
- 24 no_potential (6 images x 4 repetitions)
- 12 bottom-only (6 images x 2 repetitions)
- 84 total trials
- Half of targets preceded by potential, half by no_potential
"""

# ----------------------------------------------------------------------
# Global settings
# ----------------------------------------------------------------------

exp = design.Experiment(name="Tetris Detection", background_colour=C_WHITE, foreground_colour=C_BLACK)
exp.add_data_variable_names(["subject_id", "trial_id", "stim_name", "stim_type", "is_target", "RT_ms", "correct"])
control.set_develop_mode()
control.initialize(exp)

SUBJECT_ID = 1
IMG_DIR = "images"
ww, wl = exp.screen.size

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def timed_draw(stims):
    """Present a list of stimuli and return the draw time (ms)."""
    clock = misc.Clock()
    t0 = clock.time
    for stim in stims:
        stim.present()
    t1 = clock.time
    return t1 - t0

def present_for(stims, t=1000):
    """Present stimuli for a fixed duration (accounting for draw time)."""
    clock = misc.Clock()
    draw_time = timed_draw(stims)
    clock.wait(t - draw_time)

def window(color):
    """Create a colored border frame (used for feedback)."""
    vertices = misc.geometry.vertices_frame((ww, wl), frame_thickness=10)
    frame = stimuli.Shape(vertex_list=vertices, colour=color)
    frame.preload()
    return frame

# ----------------------------------------------------------------------
# Stimulus loading
# ----------------------------------------------------------------------

def load_stimuli_from_folder(path):
    img_dir = os.path.join(os.path.dirname(sys.argv[0]), path)
    if not os.path.exists(img_dir):
        raise FileNotFoundError(f"Image directory not found: {img_dir}")

    all_files = [f for f in os.listdir(img_dir) if f.endswith(".png")]
    if not all_files:
        raise FileNotFoundError("No .png files found in ./images/")

    stims = {
        "target": [stimuli.Picture(os.path.join(img_dir, f)) for f in all_files if f == "target.png"],
        "potential": [stimuli.Picture(os.path.join(img_dir, f)) for f in all_files if f.startswith("potential_")],
        "no_potential": [stimuli.Picture(os.path.join(img_dir, f)) for f in all_files if f.startswith("no_potential_")],
        "bottom": [stimuli.Picture(os.path.join(img_dir, f)) for f in all_files if f.startswith("bottom_")],
    }

    for cat in stims.values():
        for stim in cat:
            stim.preload()

    return stims

# ----------------------------------------------------------------------
# Trial list creation
# ----------------------------------------------------------------------

def make_trial_list(stims):
    """Create 84 trials with correct repetition structure."""
    trials = []

    # 24 target (same image repeated 24×)
    for _ in range(24):
        stim = stims["target"][0]
        trials.append({"stim_type": "target", "stim": stim,
                       "stim_name": os.path.basename(stim.filename),
                       "is_target": True})

    # 24 potential (6 images × 4)
    for s in stims["potential"]:
        for _ in range(4):
            trials.append({"stim_type": "potential", "stim": s,
                           "stim_name": os.path.basename(s.filename),
                           "is_target": False})

    # 24 no-potential (6 images × 4)
    for s in stims["no_potential"]:
        for _ in range(4):
            trials.append({"stim_type": "no_potential", "stim": s,
                           "stim_name": os.path.basename(s.filename),
                           "is_target": False})

    # 12 bottom-only (6 images × 2)
    for s in stims["bottom"]:
        for _ in range(2):
            trials.append({"stim_type": "bottom", "stim": s,
                           "stim_name": os.path.basename(s.filename),
                           "is_target": False})

    return trials

def make_trial_sequence(stims):
    """Create sequence with half targets preceded by potential, half by no_potential."""
    targets = [{"stim_type": "target", "stim": stims["target"][0],
                "stim_name": "target.png", "is_target": True} for _ in range(24)]

    potential_trials = [{"stim_type": "potential", "stim": s,
                         "stim_name": os.path.basename(s.filename), "is_target": False}
                        for s in stims["potential"] for _ in range(4)]
    no_potential_trials = [{"stim_type": "no_potential", "stim": s,
                            "stim_name": os.path.basename(s.filename), "is_target": False}
                           for s in stims["no_potential"] for _ in range(4)]
    bottom_trials = [{"stim_type": "bottom", "stim": s,
                      "stim_name": os.path.basename(s.filename), "is_target": False}
                     for s in stims["bottom"] for _ in range(2)]

    random.shuffle(potential_trials)
    random.shuffle(no_potential_trials)
    random.shuffle(bottom_trials)

    seq = []
    # 12 potential–target pairs
    for _ in range(12):
        seq.append(potential_trials.pop())
        seq.append(targets.pop())
    # 12 no_potential–target pairs
    for _ in range(12):
        seq.append(no_potential_trials.pop())
        seq.append(targets.pop())

    # add remaining potential, no_potential, bottom randomly
    leftover = potential_trials + no_potential_trials + bottom_trials
    random.shuffle(leftover)
    seq += leftover
    random.shuffle(seq)

    return seq

# ----------------------------------------------------------------------
# Instructions phase
# ----------------------------------------------------------------------

def show_instructions(stims):
    examples = [
        ("target", "Press the spacebar!"),
        ("potential", "DO NOT press the spacebar!"),
        ("no_potential", "DO NOT press the spacebar!"),
        ("bottom", "DO NOT press the spacebar!"),
    ]
    for cat, msg in examples:
        stim = random.choice(stims[cat])
        stim.present(clear=True)
        text = stimuli.TextLine(msg, position=(0, -wl // 3))
        text.present(clear=False, update=True)
        exp.keyboard.wait([K_SPACE])
    final = stimuli.TextScreen(
        "Ready?",
        "Press SPACE only when you see a full 5×5 square.\n\n"
        "Try to be fast and precise.\n\nPress SPACE to begin."
    )
    final.present()
    exp.keyboard.wait([K_SPACE])

# ----------------------------------------------------------------------
# Trial procedure
# ----------------------------------------------------------------------

def run_trial(trial_id, stim, stim_name, stim_type, is_target):
    clock = misc.Clock()
    frame_black = window((0, 0, 0))

    # --- Present stimulus (600 ms) ---
    stim.present(clear=True, update=False)
    frame_black.present(clear=False, update=True)

    # Accept responses for total 1800 ms
    key, rt = exp.keyboard.wait([K_SPACE], duration=1800)
    response_taken = key == K_SPACE

    # --- Feedback (only if pressed) ---
    if response_taken:
        correct = is_target
        color = (0, 255, 0) if correct else (255, 0, 0)
        fb = window(color)
        present_for([fb], t=200)
    else:
        correct = not is_target

    # Ensure total trial duration = 1800 ms
    elapsed = clock.time
    remaining = max(0, 1800 - elapsed)
    clock.wait(remaining)

    # --- Save data ---
    exp.data.add([SUBJECT_ID, trial_id, stim_name, stim_type, is_target, rt if rt else "", correct])

# ----------------------------------------------------------------------
# Experiment control
# ----------------------------------------------------------------------

def run_experiment():
    stims = load_stimuli_from_folder(IMG_DIR)
    trials = make_trial_sequence(stims)

    control.start(subject_id=SUBJECT_ID)

    show_instructions(stims)

    for i, trial in enumerate(trials, 1):
        run_trial(i, trial["stim"], trial["stim_name"], trial["stim_type"], trial["is_target"])

    end = stimuli.TextScreen("Over", "Thank you for your participation!")
    end.present()
    exp.keyboard.wait([K_SPACE])
    control.end()


run_experiment()