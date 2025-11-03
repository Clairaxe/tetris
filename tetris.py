from expyriment import design, control, stimuli, misc
from expyriment.misc.constants import C_WHITE, C_BLACK, K_SPACE
import os, sys, random

EXP_NAME = "Tetris"
IMG_DIR = "images"
SUBJECT_ID = 1

exp = design.Experiment(name=EXP_NAME, background_colour=C_WHITE, foreground_colour=C_BLACK)
exp.add_data_variable_names(["subject_id", "trial_num", "stim_name", "kind", "RT_ms", "correct"])
control.set_develop_mode()      # comment out for real timing
control.initialize(exp)

ww, wl = exp.screen.size

# handes stimulus loadings etc. 

def load_photo_stim(path):
    return stimuli.Picture(path)

def split_stims(path):
    img_dir = os.path.join(os.path.dirname(sys.argv[0]), path)
    all_files = [f for f in os.listdir(img_dir) if f.endswith(".png")]
    if not all_files:
        raise FileNotFoundError("No .png files found in ./images/")

    square   = [os.path.join(img_dir, f) for f in all_files if f == "square.png"]
    match    = [os.path.join(img_dir, f) for f in all_files if f.startswith("match_")]
    mismatch = [os.path.join(img_dir, f) for f in all_files if f.startswith("mismatch_")]
    bottom   = [os.path.join(img_dir, f) for f in all_files if f.startswith("bottom_")]

    square_stims   = [load_photo_stim(p) for p in square]
    match_stims    = [load_photo_stim(p) for p in match]
    mismatch_stims = [load_photo_stim(p) for p in mismatch]
    bottom_stims   = [load_photo_stim(p) for p in bottom]

    for cat in [square_stims, match_stims, mismatch_stims, bottom_stims]:
        for s in cat:
            s.preload()

    print(f"Loaded: square={len(square_stims)}, match={len(match_stims)}, mismatch={len(mismatch_stims)}, bottom={len(bottom_stims)}")
    return square_stims, match_stims, mismatch_stims, bottom_stims

# handles the color border 

def make_frames():
    """Prebuild and preload the 3 frame variants"""
    verts = misc.geometry.vertices_frame((ww, wl), frame_thickness=10)
    fr_neutral = stimuli.Shape(vertex_list=verts, colour=(0, 0, 0))     # black
    fr_correct = stimuli.Shape(vertex_list=verts, colour=(0, 255, 0))   # green
    fr_error   = stimuli.Shape(vertex_list=verts, colour=(255, 0, 0))   # red
    for fr in (fr_neutral, fr_correct, fr_error):
        fr.preload()
    return {"neutral": fr_neutral, "correct": fr_correct, "error": fr_error}

FRAMES = make_frames()

def present_with_frame(content_stim=None, frame_key="neutral", clear=True):
    if clear:
        exp.screen.clear()
    if content_stim is not None:
        content_stim.present(clear=False, update=False)
    FRAMES[frame_key].present(clear=False, update=True)

# trial creation

def make_stim_list(square, match, mismatch, bottom):
    """
    Construct trials with hard constraints:
      - Counts: 24 target, 24 potential, 24 mismatch, 12 bottom (total 84)
      - No adjacent targets
      - Every target is preceded by potential or mismatch (never by bottom)
      - Exactly 12 targets preceded by potential and 12 by mismatch

    Strategy (robust, no random reshuffle loops):
      - Build 24 [preceder, target] pairs (12 'potential' preceders + 12 'mismatch' preceders)
      - Build remaining distractors: 12 'potential' + 12 'mismatch' + 12 'bottom'
      - Distribute the 36 extras across 25 gaps around the 24 pairs
      - Stitch gaps and pairs -> final list
    """
    # Basic sanity on inputs
    if not square:
        raise RuntimeError("No 'square' stimulus found.")
    if len(match) == 0 or len(mismatch) == 0 or len(bottom) == 0:
        raise RuntimeError("Need non-empty match/mismatch/bottom pools.")

    # --- Build the 24 preceders: 12 potential + 12 mismatch ---
    # We sample with replacement from provided pools to avoid exhausting them.
    preceders = (
        [{"stim": random.choice(match),    "kind": "potential"} for _ in range(12)] +
        [{"stim": random.choice(mismatch), "kind": "mismatch"}  for _ in range(12)]
    )
    random.shuffle(preceders)

    # --- Build the 24 targets (use square[0] or sample if multiple provided) ---
    target_stim = random.choice(square)
    targets = [{"stim": target_stim, "kind": "target"} for _ in range(24)]

    # --- Pair them: [preceder, target] ---
    pairs = []
    for prec, tgt in zip(preceders, targets):
        pairs.append([prec, tgt])

    # --- Remaining distractors: 12 potential + 12 mismatch + 12 bottom = 36 ---
    extras = (
        [{"stim": random.choice(match),    "kind": "potential"} for _ in range(12)] +
        [{"stim": random.choice(mismatch), "kind": "mismatch"}  for _ in range(12)] +
        [{"stim": random.choice(bottom),   "kind": "bottom"}    for _ in range(12)]
    )
    random.shuffle(extras)

    # --- Distribute extras across 25 gaps (before, between, after the 24 pairs) ---
    gaps = [[] for _ in range(25)]
    for ex in extras:
        gaps[random.randrange(25)].append(ex)

    # --- Stitch final sequence: gap0 + pair0 + gap1 + pair1 + ... + gap24 ---
    trials = []
    for i in range(24):
        trials.extend(gaps[i])
        trials.extend(pairs[i])  # (preceder, target)
    trials.extend(gaps[24])

    # --- Sanity checks (fail fast if constraints are broken) ---
    total_target   = sum(t["kind"] == "target"    for t in trials)
    total_potential= sum(t["kind"] == "potential" for t in trials)
    total_mismatch = sum(t["kind"] == "mismatch"  for t in trials)
    total_bottom   = sum(t["kind"] == "bottom"    for t in trials)
    assert total_target == 24 and total_potential == 24 and total_mismatch == 24 and total_bottom == 12, \
        f"Counts off: target={total_target}, potential={total_potential}, mismatch={total_mismatch}, bottom={total_bottom}"

    # No adjacent targets
    assert all(not (a["kind"] == "target" and b["kind"] == "target")
               for a, b in zip(trials, trials[1:])), "Adjacent targets found."

    # Preceder balance and validity
    preceded_by_pot = 0
    preceded_by_mis = 0
    for i in range(1, len(trials)):
        if trials[i]["kind"] == "target":
            pk = trials[i-1]["kind"]
            assert pk in {"potential", "mismatch"}, "A target is not preceded by potential/mismatch."
            if pk == "potential":
                preceded_by_pot += 1
            elif pk == "mismatch":
                preceded_by_mis += 1
    assert preceded_by_pot == 12 and preceded_by_mis == 12, \
        f"Preceder imbalance: potential={preceded_by_pot}, mismatch={preceded_by_mis}"

    return trials

# instructions

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

# trial
def run_trial_list(trials):
    # Pre-blank before first trial
    exp.keyboard.clear()
    present_with_frame(content_stim=None, frame_key="neutral", clear=True)
    misc.Clock().wait(200)

    for i, tr in enumerate(trials, start=1):
        stim = tr["stim"]
        kind = tr["kind"]
        is_target = (kind == "target")
        answered = False
        rt = None

        # ---------- Stimulus epoch (600 ms) ----------
        present_with_frame(content_stim=stim, frame_key="neutral", clear=True)
        key, rt1 = exp.keyboard.wait([K_SPACE], duration=600)
        if key == K_SPACE:
            answered = True
            rt = rt1

        # ---------- Transition to BLANK (stimulus OFF at 600 ms, always) ----------
        # Show blank + appropriate frame immediately after the stim window ends
        if answered:
            # If a response happened during the stim window, show colored frame over blank
            present_with_frame(content_stim=None,
                               frame_key=("correct" if is_target else "error"),
                               clear=True)
        else:
            # No response yet: show neutral frame over blank
            present_with_frame(content_stim=None, frame_key="neutral", clear=True)

        # ---------- Blank epoch (up to 1200 ms) ----------
        blank_total = 1200
        if not answered:
            # Accept response during the blank; keep blank on screen regardless
            key2, rt2 = exp.keyboard.wait([K_SPACE], duration=blank_total)
            if key2 == K_SPACE:
                answered = True
                rt = 600 + rt2  # accumulate RT across epochs
                # Swap to colored frame but stay on the same blank (single flip)
                FRAMES["correct" if is_target else "error"].present(clear=False, update=True)
                # Wait the remaining blank time so total blank stays 1200 ms
                remaining = max(0, blank_total - rt2)
                if remaining > 0:
                    misc.Clock().wait(remaining)
            else:
                # No response during blank; we've already displayed the full 1200 ms
                pass
        else:
            # Already answered during the stimulus epoch; keep the colored frame on blank for full 1200 ms
            misc.Clock().wait(blank_total)

        # ---------- Feedback flash (200 ms) ----------
        if answered:
            present_with_frame(content_stim=None,
                               frame_key=("correct" if is_target else "error"),
                               clear=True)
            misc.Clock().wait(200)

        # ---------- Save data ----------
        correct = (answered and is_target) or (not answered and not is_target)
        exp.data.add([
            SUBJECT_ID,
            i,
            getattr(stim, "filename", "unknown"),
            kind,
            rt if rt else "",
            correct
        ])

# run experiment

def run_experiment():
    square, match, mismatch, bottom = split_stims(IMG_DIR)
    trials = make_stim_list(square, match, mismatch, bottom)

    control.start(subject_id=SUBJECT_ID)

    show_instructions()
    run_trial_list(trials)

    end = stimuli.TextScreen("End", "Thank you for participating!\n\nPress SPACE to finish.")
    end.present()
    exp.keyboard.wait([K_SPACE])
    control.end()

# main
run_experiment()

### TODO ###
# 1) exact timing (take time of drawing into account)
# 2) when SPACE in pressed, the image disappears (and i dont think we want that)