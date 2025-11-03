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

# handles stimulus loadings etc. 

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

# help

def reps(stim_list, kind, n):
        """Replicate each stimulus in stim_list exactly n times as separate items."""
        out = []
        for s in stim_list:
            for _ in range(n):
                out.append({"stim": s, "kind": kind, "image": getattr(s, "filename", "")})
        return out
    
# trial creation

def make_stim_list(square, match, mismatch, bottom):
    """
    Exact paper spec with minimal logic:
      - Images present: bottom_1..6, match_1..6, mismatch_1..6, square
      - Counts per image:
          match_i:     4 each  (24 total potential)
          mismatch_i:  4 each  (24 total mismatch)
          bottom_i:    2 each  (12 total bottom)
          square:      24 total targets
      - Constraints:
          * No adjacent targets
          * Exactly 12 targets preceded by 'potential' and 12 by 'mismatch'
          * Targets are never preceded by 'bottom'
    """

    # --- exact-repeat pools (per-image counts are fixed here) ---
    pot_all = reps(match,    "potential", 4)   # 6 * 4 = 24
    mis_all = reps(mismatch, "mismatch",  4)   # 6 * 4 = 24
    bot_all = reps(bottom,   "bottom",    2)   # 6 * 2 = 12
    tgt_all = [{"stim": square[0], "kind": "target", "image": getattr(square[0], "filename", "")} for _ in range(24)]

    # Shuffle within pools so each image’s instances are mixed
    random.shuffle(pot_all)
    random.shuffle(mis_all)
    random.shuffle(bot_all)

    # --- preceders for the 24 targets: 12 potential + 12 mismatch (balanced) ---
    prec_list = pot_all[:12] + mis_all[:12]
    random.shuffle(prec_list)

    # Remaining extras to distribute in gaps
    pot_left = pot_all[12:]   # 12 left
    mis_left = mis_all[12:]   # 12 left
    extras   = pot_left + mis_left + bot_all  # 12 + 12 + 12 = 36
    random.shuffle(extras)

    # --- build pairs [preceder, target] so targets can’t be adjacent ---
    pairs = []
    for prec, tgt in zip(prec_list, tgt_all):
        pairs.append([prec, tgt])

    # --- distribute extras across 25 gaps: before, between, after pairs ---
    gaps = [[] for _ in range(25)]
    for ex in extras:
        gaps[random.randrange(25)].append(ex)

    # --- stitch final sequence: gap0 + pair0 + gap1 + pair1 + ... + gap24 ---
    trials = []
    for i in range(24):
        trials.extend(gaps[i])
        trials.extend(pairs[i])
    trials.extend(gaps[24])

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

def flash(frame_key, over_stim=None, dur_ms=200):
    """Flash the border for 'dur_ms' without re-clearing or re-drawing content."""
    FRAMES[frame_key].present(clear=False, update=True)
    misc.Clock().wait(dur_ms)
    FRAMES["neutral"].present(clear=False, update=True)

def run_trial_list(trials):
    STIM_MS   = 600
    BLANK_MS  = 1200
    FLASH_MS  = 200
    SAFETY_MS = 50   # stop taking input a hair before each transition

    # settle
    exp.keyboard.clear()
    present_with_frame(None, "neutral", clear=True)
    misc.Clock().wait(200)

    for i, tr in enumerate(trials, start=1):
        stim      = tr["stim"]
        is_target = (tr["kind"] == "target")
        answered  = False
        rt        = None

        # ---- STIMULUS (exactly 600 ms; image stays up the whole time) ----
        exp.keyboard.clear()
        t0 = misc.Clock()
        present_with_frame(stim, "neutral", clear=True)

        # accept responses until a small buffer before the flip
        wait_ms = max(0, STIM_MS - SAFETY_MS)
        key, rt1 = exp.keyboard.wait([K_SPACE], duration=wait_ms)

        if key == K_SPACE:
            answered = True
            rt = rt1
            # flash 200 ms max, but never exceed the epoch
            left = max(0, STIM_MS - t0.time)
            flash("correct" if is_target else "error", over_stim=stim, dur_ms=min(FLASH_MS, left))

        # finish to 600 ms exactly (no more input)
        rem = max(0, STIM_MS - t0.time)
        if rem > 0:
            misc.Clock().wait(rem)

        # ---- BLANK (exactly 1200 ms) ----
        exp.keyboard.clear()
        t1 = misc.Clock()
        present_with_frame(None, "neutral", clear=True)

        if not answered:
            wait_ms = max(0, BLANK_MS - SAFETY_MS)
            key2, rt2 = exp.keyboard.wait([K_SPACE], duration=wait_ms)
            if key2 == K_SPACE:
                answered = True
                rt = STIM_MS + rt2
                left = max(0, BLANK_MS - t1.time)
                flash("correct" if is_target else "error", over_stim=None, dur_ms=min(FLASH_MS, left))

        # finish to 1200 ms exactly (no more input)
        rem = max(0, BLANK_MS - t1.time)
        if rem > 0:
            misc.Clock().wait(rem)

        # ---- SAVE ----
        correct = (answered and is_target) or (not answered and not is_target)
        exp.data.add([
            SUBJECT_ID, i, getattr(stim, "filename", "unknown"),
            tr["kind"], (rt if answered else ""), correct
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