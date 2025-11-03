from expyriment import design, control, stimuli, misc
from expyriment.misc.constants import C_WHITE, C_BLACK, K_SPACE
import os, sys, random
from collections import Counter, defaultdict

# Config
EXPERIMENT_NAME = "Full-5x5 Task"
IMG_DIR = "images"
SUBJECT_ID = 1

# Durations (ms)
PHASE_STIM_MS = 600
PHASE_BLANK_MS = 1200
BORDER_FLASH_MS = 200

# experiment init
exp = design.Experiment(
    name=EXPERIMENT_NAME,
    background_colour=C_WHITE,
    foreground_colour=C_BLACK
)
exp.add_data_variable_names(
    ["block", "trial_number", "kind", "image_name", "rt_ms", "pressed", "correct"]
)
control.set_develop_mode()
control.initialize(exp)
ww, wl = exp.screen.size

# helpers
def load(stims):
    for s in stims:
        s.preload()

def load_photo_stim(path):
    # Centered by default
    return stimuli.Picture(path)

def split_stims(path_dir):
    img_dir = os.path.join(os.path.dirname(sys.argv[0]), path_dir)
    if not os.path.exists(img_dir):
        raise FileNotFoundError(f"Image directory not found: {img_dir}")

    all_png = [f for f in os.listdir(img_dir) if f.endswith(".png")]
    if not all_png:
        raise FileNotFoundError("No .png files found in ./images/")

    square_files   = [f for f in all_png if f == "square.png"]
    match_files    = sorted([f for f in all_png if f.startswith("match_")])
    mismatch_files = sorted([f for f in all_png if f.startswith("mismatch_")])
    bottom_files   = sorted([f for f in all_png if f.startswith("bottom_")])

    if len(square_files) != 1:
        raise RuntimeError("Expect exactly one 'square.png'.")

    if len(match_files) != 6 or len(mismatch_files) != 6 or len(bottom_files) != 6:
        raise RuntimeError("Expect match_1..6, mismatch_1..6, bottom_1..6.")

    # Build stimuli dicts with image name for logging
    square_path = os.path.join(img_dir, square_files[0])
    square_stim = load_photo_stim(square_path)

    def mk_stims(files):
        out = []
        for f in files:
            p = os.path.join(img_dir, f)
            out.append({"stim": load_photo_stim(p), "name": f})
        return out

    match_stims = mk_stims(match_files)
    mismatch_stims = mk_stims(mismatch_files)
    bottom_stims = mk_stims(bottom_files)

    # Preload
    load([square_stim] + [d["stim"] for d in match_stims + mismatch_stims + bottom_stims])

    return square_stim, match_stims, mismatch_stims, bottom_stims

def build_balanced_trials(square_stim, match_stims, mismatch_stims, bottom_stims):
    """
      Images present:
        bottom_1..6, match_1..6, mismatch_1..6, square
      Counts per image:
        match_i:     4 each  (24 total potential)
        mismatch_i:  4 each  (24 total mismatch)
        bottom_i:    2 each  (12 total bottom)
        square:      24 total targets
      Constraints:
        * No adjacent targets
        * Exactly 12 targets preceded by 'potential' (match) and 12 by 'mismatch'
        * Targets are never preceded by 'bottom'
    """

    # Expand non-target pools with exact counts
    def expand(items, count_each, kind):
        bag = []
        for d in items:
            for _ in range(count_each):
                bag.append({"kind": kind, "stim": d["stim"], "name": d["name"]})
        return bag

    non_targets = []
    non_targets += expand(match_stims,    4, "potential")    # 24
    non_targets += expand(mismatch_stims, 4, "mismatch")     # 24
    non_targets += expand(bottom_stims,   2, "bottom")       # 12
    assert len(non_targets) == 60

    # Shuffle non-targets
    random.shuffle(non_targets)

    # Choose exactly 12 potentials and 12 mismatches that will be followed by a target
    potential_idxs = [i for i, t in enumerate(non_targets) if t["kind"] == "potential"]
    mismatch_idxs  = [i for i, t in enumerate(non_targets) if t["kind"] == "mismatch"]

    chosen_p = set(random.sample(potential_idxs, 12))
    chosen_m = set(random.sample(mismatch_idxs, 12))

    # Mark flags on a copy
    for i, t in enumerate(non_targets):
        t["followed_by_target"] = (i in chosen_p) or (i in chosen_m)

    # Assemble final trial list: for each non-target, append it; if flagged, append a target after it
    trials = []
    for t in non_targets:
        trials.append({
            "kind": t["kind"],
            "stim": t["stim"],
            "name": t["name"],
            "is_target": False
        })
        if t["followed_by_target"]:
            trials.append({
                "kind": "target",
                "stim": square_stim,
                "name": "square.png",
                "is_target": True
            })

    return trials

# frames
def make_frame(colour_rgb):
    vertices = misc.geometry.vertices_frame((ww, wl), frame_thickness=10)
    fr = stimuli.Shape(vertex_list=vertices, colour=colour_rgb)
    fr.preload()
    return fr

FRAMES = {
    "neutral": make_frame((0, 0, 0)),
    "correct": make_frame((0, 255, 0)),
    "incorrect": make_frame((255, 0, 0)),
}

def present_with_frame(content_stim=None, frame_key="neutral", clear=True, update=True):
    if content_stim is not None:
        content_stim.present(clear=clear, update=False)
        FRAMES[frame_key].present(clear=False, update=update)
    else:
        FRAMES[frame_key].present(clear=clear, update=update)

def show_instructions():
    instructions = stimuli.TextScreen(
        "Welcome!",
        "Press the SPACEBAR only when you see a full 5x5 square.\n\n"
        "Do NOT press for any other shapes.\n\n"
        "Try to be fast but accurate.\n\n"
        "Press SPACE to begin."
    )
    instructions.present()
    exp.keyboard.wait([K_SPACE])

    exp.keyboard.clear()
    present_with_frame(content_stim=None, frame_key="neutral", clear=True)
    misc.Clock().wait(300)

# trials
def run_trial_list(trials, block=1):
    clock = misc.Clock()
    trial_nr = 0

    for tr in trials:
        trial_nr += 1
        is_target = tr["is_target"]
        stim = tr["stim"]
        img_name = tr["name"]

        # Phase 1: stimulus + frame, monitor SPACE for PHASE_STIM_MS
        rt = None
        pressed = False
        correct = None

        t0 = clock.time
        present_with_frame(stim, "neutral", clear=True, update=True)
        # Wait for response within the remaining time after draw
        t1 = clock.time
        remain = max(0, PHASE_STIM_MS - (t1 - t0))
        key, rt1 = exp.keyboard.wait([K_SPACE], duration=remain)

        if key == K_SPACE:
            pressed = True
            correct = bool(is_target)
            rt = rt1  # Expyriment returns RT in ms since present()
            # Flash feedback for 200 ms
            present_with_frame(stim, "correct" if correct else "incorrect", clear=True, update=True)
            misc.Clock().wait(BORDER_FLASH_MS)
            # Return to neutral for leftover of the phase (if any)
            elapsed = (clock.time - t0)
            leftover = max(0, PHASE_STIM_MS - elapsed)
            if leftover > 0:
                present_with_frame(stim, "neutral", clear=True, update=True)
                misc.Clock().wait(leftover)

        else:
            pressed = False
            correct = (not is_target)  # no press is correct if not a target

        # Log phase 1 result
        exp.data.add(
            [block, trial_nr, ("target" if is_target else tr["kind"]), img_name, rt if rt is not None else -1,
             int(pressed), int(correct)]
        )

        # Phase 2: blank frame, still monitor for PHASE_BLANK_MS
        # Reset for phase-2 press
        t0 = clock.time
        present_with_frame(None, "neutral", clear=True, update=True)
        t1 = clock.time
        remain = max(0, PHASE_BLANK_MS - (t1 - t0))
        key, rt2 = exp.keyboard.wait([K_SPACE], duration=remain)

        if key == K_SPACE:
            # Late press: evaluate against same target label
            pressed2 = True
            correct2 = bool(is_target)
            # Flash only 200 ms
            present_with_frame(None, "correct" if correct2 else "incorrect", clear=True, update=True)
            misc.Clock().wait(BORDER_FLASH_MS)
            # Then neutral for remainder
            elapsed = (clock.time - t0)
            leftover = max(0, PHASE_BLANK_MS - elapsed)
            if leftover > 0:
                present_with_frame(None, "neutral", clear=True, update=True)
                misc.Clock().wait(leftover)

            exp.data.add([block, trial_nr, ("target" if is_target else tr["kind"]), img_name,
                          rt2 if rt2 is not None else -1, int(pressed2), int(correct2)])
        else:
            pressed2 = False
            correct2 = (not is_target)
            exp.data.add([block, trial_nr, ("target" if is_target else tr["kind"]), img_name,
                          -1, int(pressed2), int(correct2)])

def run_experiment():
    square, match, mismatch, bottom = split_stims(IMG_DIR)
    trials = build_balanced_trials(square, match, mismatch, bottom)

    control.start(subject_id=SUBJECT_ID)

    show_instructions()
    run_trial_list(trials)

    end = stimuli.TextScreen("End", "Thank you for participating!\n\nPress SPACE to finish.")
    end.present()
    exp.keyboard.wait([K_SPACE])
    control.end()

# main
run_experiment()