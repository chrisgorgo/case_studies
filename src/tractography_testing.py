import os
import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.io as nio           # Data i/o
import nipype.interfaces.fsl as fsl

info = dict(phsamples = [['bedpostx/postproc','subject_id',  'merge_phsamples/mapflow/_merge_phsamples*/ph*samples_merged']], 
            thsamples = [['bedpostx/postproc','subject_id', 'merge_thsamples/mapflow/_merge_thsamples*/th*samples_merged']], 
            fsamples = [['bedpostx/postproc','subject_id', 'merge_fsamples/mapflow/_merge_fsamples*/f*samples_merged']], 
            mask = [['preprocess', 'subject_id',  'bet/*_mask']]
            )

subject_id = '2402571160_20101210'

datasource =pe.Node(interface=nio.DataGrabber(infields=['subject_id'], outfields=info.keys()), name="datasource")

datasource.inputs.base_directory = '/media/data/2010reliability/workdir/pipeline/'
datasource.inputs.template = 'proc_dwi/%s/_subject_id_%s/%s.nii'
datasource.inputs.subject_id = subject_id
datasource.inputs.template_args = info

probtractx = pe.Node(interface=fsl.ProbTrackX(), name="probtractx")
probtractx.inputs.seed = [[63,56,38],
                          [64,81,39],
                          [51,70,60],#cortex
                          [52,70,61],#cortex
                          [58,68,62],#cortex
                          [55,70,54],
                          [55,70,47]]
probtractx.inputs.opd = True
probtractx.inputs.loop_check = True
probtractx.inputs.c_thresh = 0.2
probtractx.inputs.n_steps = 2000
probtractx.inputs.step_length = 0.5
probtractx.inputs.n_samples = 10000


main_pipeline = pe.Workflow(name="pipeline")
main_pipeline.base_dir = os.path.join('/media/data/2010reliability/',"probtract_testing")

main_pipeline.connect([(datasource, probtractx, [("phsamples", "phsamples"),
                                                 ("thsamples", "thsamples"),
                                                 ("fsamples", "fsamples"),
                                                 ("mask", "mask")])
                      ])

main_pipeline.run()

