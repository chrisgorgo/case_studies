from nipype.utils.config import config
import os
from StringIO import StringIO

b22 = [442, 446, 458, 460, 764, 765, 766, 767]
b45 = [602, 603,]
b44 = [689, 690, 748, 749,]
right_parietal = [int(a) for a in ['777',
 '778',
 '780',
 '782',
 '786',
 '793',
 '795',
 '797',
 '798',
 '802',
 '806',
 '807',
 '858',
 '859',
 '862',
 '864',
 '875',
 '880',
 '881',
 '883',
 '889',
 '892',
 '894',
 '896',
 '928',
 '930',
 '964',
 '966',
 '970',
 '972',
 '975',
 '977',
 '987',
 '989',
 '991',
 '993',
 '997',
 '998',
 '1000',
 '1015',
 '1019',
 '1038',
 '1040',
 '1042',
 '1044',
 '1050',
 '1062',
 '1066',
 '1067',
 '1072',
 '1073',
 '1081',
 '1096',
 '1098',
 '1099',
 '1102',
 '1105']]


design_parameters = {'finger_foot_lips':{'conditions': ['Finger', 'Foot', 'Lips'],
                                         'units': 'scans',
                                         'onsets': [[0, 36, 72, 108, 144],
                                                    [12, 48, 84, 120, 156],
                                                    [24, 60, 96, 132, 168]],
                                         'durations': [[6], [6], [6]],
                                         'sparse': False,
                                         'TR': 2.5, 
                                         'contrasts': [('Finger','T', ['Finger'],[1]),
                                                       ('Foot','T', ['Foot'],[1]),
                                                       ('Lips','T', ['Lips'],[1]),
                                                       ('Finger_vs_Other', 'T',['Finger','Foot','Lips'], [1,    -0.5,-0.5]),
                                                       ('Foot_vs_Other', 'T',  ['Finger','Foot','Lips'], [-0.5,  1,  -0.5]),
                                                       ('Lips_vs_Other', 'T',  ['Finger','Foot','Lips'], [-0.5, -0.5, 1  ])
                                                       ],
                                         'mask_file': '/media/data/2010reliability/Masks/ROI_Motor_cortex_MNI_bin_left.nii',
                                         'atlas_labels': [804,805,806,807,808],
                                         'dilation': 2},
                     "overt_verb_generation":{'conditions': ['Task'],
                                              'units': 'scans',
                                              'onsets': [[0, 12, 24, 36, 48, 60, 72]],
                                              'durations': [[6]],
                                              'sparse': True,
                                              'TR': 5.0,
                                              'contrasts': [('Task','T', ['Task'],[1])],
                                              'atlas_labels': b45 + b44,
                                              'mask_file': '/media/data/2010reliability/Masks/ROI_Broca_area_MNI.img',
                                              'dilation': 6},
                     "overt_word_repetition": {'conditions':['Task'],
                                               'units': 'scans',
                                               'onsets': [[0, 12, 24, 36, 48, 60]],
                                               'durations': [[6]],
                                               'sparse': True,
                                               'TR': 5.0,
                                               'contrasts': [('Task','T', ['Task'],[1])],
                                               'atlas_labels': b22,
                                               'mask_file': '/media/data/2010reliability/Masks/ROI_Wernicke_area_MNI.img',
                                               'dilation': 12},
                     'covert_verb_generation':{'conditions': ['Task'],
                                               'units': 'scans',
                                               'onsets': [[0, 24, 48, 72, 96, 120, 144]],
                                               'durations': [[12]],
                                               'sparse': False,
                                               'TR': 2.5,
                                               'contrasts': [('Task','T', ['Task'],[1])],
                                               'atlas_labels': b45 + b44,
                                               'mask_file': '/media/data/2010reliability/Masks/ROI_Broca_area_MNI.img',
                                               'dilation': 6},
                     'line_bisection':{'conditions': ['Correct_Task', 'Incorrect_Task', 'No_Response_Task',
                                                      'Correct_Control', 'Incorrect_Control', 'No_Response_Control'],
                                       'units': 'secs',
                                       'onsets': [[  16.25,   81.25,  146.25,  211.25,  276.25,  341.25,  406.25, 471.25, 536.25],
                                                  [  48.75,  113.75,  178.75,  243.75,  308.75,  373.75,  438.75, 503.75, 568.75]],
                                       'durations': [[0], [0], [0], [0], [0], [0]],
                                       'sparse': False,
                                       'TR': 2.5,
                                       'contrasts': [('Task_All_Greater_Than_Control_All','T', ['Correct_Task', 'Incorrect_Task', 'No_Response_Task',
                                                      'Correct_Control', 'Incorrect_Control', 'No_Response_Control'],[1,1,1,-1,-1,-1]),
                                                     ('Task_Answered_Greater_Than_Control_Answered','T', ['Correct_Task', 'Incorrect_Task', 
                                                      'Correct_Control', 'Incorrect_Control'],[1,1,-1,-1]),
                                                     ('Task_Correct_Greater_Than_Control_Correct','T', ['Correct_Task', 'Correct_Control'],[1,-1]),
                                                     ('Correct_Greater_Than_Incorrect','T', ['Correct_Task', 'Incorrect_Task',
                                                      'Correct_Control', 'Incorrect_Control'],[1,-1,1,-1])],
                                       'atlas_labels': right_parietal,
                                       'dilation': 2}
                     }

def getStatLabels(task_name):
    from variables import design_parameters
    return [contrast[0] for contrast in design_parameters[task_name]['contrasts']]

data_dir = '/media/data/case_studies/data'
results_dir = "/home/filo/workspace/case_studies/results"
working_dir = '/media/data/case_studies/workdir_fmri'
dbfile = os.path.join(results_dir, "results.db")
tasks = ["finger_foot_lips", "covert_verb_generation", "overt_word_repetition"]#, 'overt_verb_generation']#"line_bisection"]# 'overt_verb_generation', "covert_verb_generation", "finger_foot_lips", "overt_word_repetition"]#, "]
thr_methods = ['topo_fdr','topo_ggmm']
sessions = ['first', 'second']
roi = [False]#,False]

subjects = ['CaseStudy03']

lefties = []

config.readfp(StringIO("""
[logging]
workflow_level = DEBUG
filemanip_level = DEBUG
interface_level = DEBUG

[execution]
stop_on_first_crash = true
stop_on_first_rerun = false
hash_method = timestamp
remove_unnecessary_outputs = true
#plugin = MultiProc
"""))