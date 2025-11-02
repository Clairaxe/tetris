from expyriment import design, control, stimuli
from expyriment.misc.constants import C_WHITE, C_BLACK, C_BLUE,C_RED,C_GREEN,C_EXPYRIMENT_ORANGE, K_1, K_2, K_SPACE


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
    if conditions met:
        continue
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
color_names= ["red","blue","green","orange"]
color_codes = [C_RED,C_BLUE,C_GREEN,C_EXPYRIMENT_ORANGE]
code_color_match = {
    "RED":C_RED,
    "BLUE":C_BLUE,
    "ORANGE":C_EXPYRIMENT_ORANGE,
    "GREEN":C_GREEN
}
def get_color_name(color):
    for name, code in code_color_match.items():
        if color == code:
            return name

""" Stimuli """
def trial_combo():
    color_id_rand = design.randomize.rand_element(range(len(color_names)))
    color_name = color_names[color_id_rand]
    match=design.randomize.coin_flip()
    if match:
        color = color_codes[color_id_rand]
        trial_type = "match"
    else:
        colors = [code for i,code in enumerate(color_codes) if i != color_id_rand]
        color = design.randomize.rand_element(colors)
        trial_type = "mismatch"
    
    text = stimuli.TextLine(color_name,text_colour=color)
    text.preload()

    return text, trial_type
    

keys_chars = {
    49: 'K_1',
    50: 'K_2',
    32: 'sPACE'
}

""" Experiment """
def run_trial():
    fixation = stimuli.FixCross(size=(150, 150), line_width=10, position=[0 , 0])
    fixation.preload()
    for block in range(2):
        text = stimuli.TextScreen(f"Stroop Effect Block:{block+1}", "After 0.5 seconds of the fixcross you will see a word, if the color of the word matches the text color press 1, if not press 2. \n---Press SPACE to continue")
        text.present(True,True)
        exp.keyboard.wait() 
        for trial in range(16):
            fixation.present(True, True)
            exp.clock.wait(500)
            color_text, trial_type = trial_combo()
            color_text.present(True,True)
            t0=exp.clock.time
            pressed, _ = exp.keyboard.wait(keys = [K_1, K_2, K_SPACE])
            t1=exp.clock.time
            if pressed == K_1 and trial_type == "match" or pressed == K_2 and trial_type == "mismatch":
                exp.data.add([block+1,
                              trial+1,
                              trial_type,
                              color_text.text,
                              get_color_name(color_text.text_colour),
                              t1-t0,
                              1])
            else:
                exp.data.add([block+1,
                              trial+1,
                              trial_type,
                              color_text.text,
                              get_color_name(color_text.text_colour),
                              t1-t0,
                              0])

control.start(subject_id=1)

run_trial()
    
control.end()