from expyriment import design, control, stimuli, misc
from expyriment.misc.constants import C_WHITE, C_BLACK, C_BLUE,C_RED,C_GREEN,C_EXPYRIMENT_ORANGE, K_1, K_2, K_SPACE
import os, sys
import random

'''

cycle(grid):
    for 600ms
        input = keyboard
        render window(answer_taken, full=grid.match)
        render grid
    for 1200ms
        input = keyboard
        render window(answer_taken, full=grid.match)

window(answer_taken=False,full=None):
    if answer_taken == True and full == True:
        return the window green
    elif answer_taken == True and full == False:
        return the window red
    else 
        return the window black

class Grid(grid_combinations):
    grid = rand.choice(grid_combinations)
    while 1:
        if conditions met:
            break
        else:
            grid = rand.choice(grid_combinations)
    match = grid.match

experiment(grid_combinations):
    grid = Grid(grid_combinations)
    for i in range(84)
        cycle(grid)
        
'''

""" Global settings """
exp = design.Experiment(name="Stroop", background_colour=C_WHITE, foreground_colour=C_BLACK)
exp.add_data_variable_names(["trial block","trial number", "trial type", "word","text color", "RTs(ms)", "accuracy"])
control.set_develop_mode()
control.initialize(exp)

ww, wl = exp.screen.size

IMG_DIR = "images"

def load(stims):
    for stim in stims:
        stim.preload()
    

def timed_draw(stims):
    clock = misc.Clock()
    t0 = clock.time
    for stim in stims:
        stim.present()
    t1 = clock.time
    return t1-t0
    # return the time it took to draw

def present_for(stims, t=1000):
    clock = misc.Clock()
    time = timed_draw(stims)
    clock.wait(t-time)

""" Stimuli """
def load_photo_stim(path):
    stim = stimuli.Picture(path, (0.0))
    return stim

def split_stims(path):
    img_dir = os.path.join(os.path.dirname(sys.argv[0]), path)
    if not os.path.exists(img_dir):
        raise FileNotFoundError(f"Image directory not found: {img_dir}")

    all_files = [f for f in os.listdir(img_dir) if f.endswith(".png")]
    if not all_files:
        raise FileNotFoundError("No .png files found in ./images/")
    
    square = [os.path.join(img_dir,f) for f in all_files if f == "square.png"]
    mismatch = [os.path.join(img_dir,f) for f in all_files if f.startswith("mismatch_")]
    match = [os.path.join(img_dir,f) for f in all_files if f.startswith("match_")]
    bottom = [os.path.join(img_dir,f) for f in all_files if f.startswith("bottom_")]

    mismatch.sort()
    match.sort()
    bottom.sort()
    square_stims   = [load_photo_stim(p) for p in square]
    match_stims    = [load_photo_stim(p) for p in match]
    mismatch_stims = [load_photo_stim(p) for p in mismatch]
    bottom_stims   = [load_photo_stim(p) for p in bottom]
    
    load(square_stims)
    load(match_stims)
    load(mismatch_stims)
    load(bottom_stims)

    return square_stims, match_stims, mismatch_stims, bottom_stims


def make_stim_list(square, match, mismatch, bottom):
    trials = (
    [{"stim": random.choice(square),   "kind": "target"}      for _ in range(24)] +
    [{"stim": random.choice(match),    "kind": "potential"}   for _ in range(24)] +
    [{"stim": random.choice(mismatch), "kind": "non_potential"}for _ in range(24)] +
    [{"stim": random.choice(bottom),   "kind": "non_potential"}      for _ in range(12)]#make sure the bottoms are considered non-potential
    )

    random.shuffle(trials)

    def nex_kind(i):
        if i == len(trials) - 1:
            return None
        k = trials[i+1]["kind"]
        return k
    
    while True:
        potentials = sum(1 for i,t in enumerate(trials[:-1]) if t["kind"] == "target" and nex_kind(i)=="potential")
        non_potentials = sum(1 for i,t in enumerate(trials[:-1]) if t["kind"] == "target" and nex_kind(i)=="non_potential")
        if potentials==non_potentials:
            break

        random.shuffle(trials)

    return trials


def window(answer_taken, target):
    vertices = misc.geometry.vertices_frame((ww/2,wl/2), frame_thickness=30)
    if answer_taken and target == True:
        frame = stimuli.Shape(vertex_list=vertices,colour=(0,255,0))
        load([frame])
        return frame
    elif answer_taken and target == False:
        frame = stimuli.Shape(vertex_list=vertices,colour=(255,0,0))
        load([frame])
        return frame
    else:
        frame = stimuli.Shape(vertex_list=vertices,colour=(255,255,255))
        load([frame])
        return frame



keys_chars = {
    49: 'K_1',
    50: 'K_2',
    32: 'sPACE'
}

""" Experiment """
def run_trial():
    square, match, mismatch, bottom = split_stims(IMG_DIR)
    trial_list = make_stim_list(square=square,match=match,mismatch=mismatch,bottom=bottom)
    answer = False

    for stim in trial_list:
        ##frame with the stim with constant check 600ms
        for _ in range(120):
            stim.present(clear=True,present=False)
            target = stim["kind"] == "potential"
            frame = window(answer, target=target)
            frame.present(clear=False, present=True)
            key, _ =  exp.keyboard.wait(keys = K_SPACE, duration = 5)
            answer = key == K_SPACE
        ##blank frame with constant check 1200ms
        for _ in range(240):
            frame = window(answer, target=target)
            frame.present(clear=True, present=True)
            key, _ =  exp.keyboard.wait(keys = K_SPACE, duration = 5)
            answer = key == K_SPACE



control.start(subject_id=1)

run_trial()
    
control.end()