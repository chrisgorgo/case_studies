import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.io as nio           # Data i/o
import nipype.interfaces.spm as spm
import nipype.interfaces.matlab as mlab      # how to run matlab
import nipype.interfaces.fsl as fsl
from helper_functions import (create_pipeline_functional_run)

from StringIO import StringIO
from nipype.interfaces.io import DataSink, SQLiteSink
from variables import *

mlab.MatlabCommand.set_default_paths("/usr/share/spm8/")


subjects_infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_id']),
                              name="subjects_infosource")
subjects_infosource.iterables = ('subject_id', subjects)

tasks_infosource = pe.Node(interface=util.IdentityInterface(fields=['task_name']),
                           name="tasks_infosource")
tasks_infosource.iterables = ('task_name', tasks)

thr_method_infosource = pe.Node(interface=util.IdentityInterface(fields=['thr_method']),
                              name="thr_method_infosource")
thr_method_infosource.iterables = ('thr_method', thr_methods)

roi_infosource = pe.Node(interface=util.IdentityInterface(fields=['roi']),
                              name="roi_infosource")
roi_infosource.iterables = ('roi', roi)

datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id', 'task_name'],
                                               outfields=['func', 'T1']),
                     name = 'datasource')

datasource.inputs.base_directory = data_dir
datasource.inputs.template = '%s/*[0-9]_%s*.nii'
datasource.inputs.template_args = dict(func = [['subject_id', 'task_name']],
                                       T1 = [['subject_id', 'o_COR_3D_IR_PREP']])
datasource.inputs.sort_filelist = True

functional_run = create_pipeline_functional_run(name="functional_run", series_format="4d")



datasink = pe.Node(interface = DataSink(), name='datasink')
datasink.inputs.base_directory = results_dir
datasink.inputs.regexp_substitutions = [
                                        #(r'(?P<root>/home/filo/workspace/2010reliability/results/)(?P<b1>.*)(?P<subject_id>_subject_id.*/)(?P<b2>.*)(?P<task_name>_task_name.*/)(?P<b3>.*)',
                                        # r'\g<root>\g<task_name>\g<b1>\g<b2>\g<subject_id>\g<b3>'),
                                        (r'(?P<r1>_[^-/]*)(?P<id>[0-9]+)(?P<r2>[/])', r'/\g<id>'),
                                        #(r'_task_name_', r''),
                                        #(r'(?P<subject_id>_subject_id[^/]*)([/])', r'\g<subject_id>_')
                                        ]

#sqlitesink = pe.MapNode(interface = SQLiteSink(input_names=["subject_id",
#                                                            "session",
#                                                            'task_name', 
#                                                            'contrast_name',
#                                                            'cluster_forming_threshold',
#                                                            'cluster_forming_threshold_fwe',
#                                                            'selected_model',
#                                                            'activation_forced',
#                                                            'n_clusters',
#                                                            'pre_topo_n_clusters',
#                                                            'roi']), 
#                        name="sqlitesink", 
#                        iterfield=["contrast_name", 'cluster_forming_threshold',
#                                                            'selected_model',
#                                                            'activation_forced',
#                                                            'n_clusters',
#                                                            'pre_topo_n_clusters',
#                                                            'cluster_forming_threshold_fwe'])
#sqlitesink.inputs.database_file = dbfile
#sqlitesink.inputs.table_name = "reliability2010_ggmm_thresholding"

def getReportFilename(subject_id):
    return "subject_%s_report.pdf"%subject_id

def getConditions(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['conditions']
    
def getOnsets(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['onsets']
    
def getDurations(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['durations']

def getTR(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['TR']

def getContrasts(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['contrasts']

def getDiffLabels(task_name):
    from variables import design_parameters
    return [contrast[0] + "_diff.nii" for contrast in design_parameters[task_name]['contrasts']]

def getUnits(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['units']

def getSparse(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['sparse']

def getAtlasLabels(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['atlas_labels']

def getDilation(task_name):
    from variables import design_parameters
    return design_parameters[task_name]['dilation']

def pickFirst(l):
    return l[0]

def pickSecond(l):
    return l[1]

def getSessionId(session, subject_id):
    s = {"8d80a62b-aa21-49bd-b8ca-9bc678ffe7b0": ["16841", "16849"],
         "08143633-aec2-49a9-81cf-45867827b871": ["17100", "17107"],
         '3a3e1a6f-dc92-412c-870a-74e4f4e85ddb': ["17168", "17180"],
         '8bb20980-2dc4-4da9-9065-879e2e7e1fbe': ["16889", "16907"],
         '90bafbe8-c67f-4388-b677-27fcf2427c71': ["16846", "16854"],
         '94cfb26f-0060-4c44-b59f-702ca61143ca': ["16967", "16978"],
         'c2cc1c59-df88-4366-9f99-73b722235789': ["16864", "16874"],
         'cf48f394-1912-4202-89f7-dbf8ef9d6e19': ["17119", "17132"],
         'df4808a4-ecce-4d0a-9fe2-535c0720ec17': ["17363", "17373"],
         'e094aae5-8387-4b5c-bf56-df4a88623c5d': ["17142", "17149"]}
    return s[subject_id][{"first":0, "second":1}[session]]

def get_vox_dims(volume):
    import nibabel as nb
    if isinstance(volume, list):
        volume = volume[0]
    nii = nb.load(volume)
    hdr = nii.get_header()
    voxdims = hdr.get_zooms()
    return [float(voxdims[0]), float(voxdims[1]), float(voxdims[2])]

get_onsets = pe.Node(interface=util.Function(input_names=['task_name', 'line_bisection_log', 'delay'], 
                                                    output_names=['onsets'], 
                                                    function=getOnsets),
                     name="get_onsets")
get_onsets.inputs.delay = 4*2.5

main_pipeline = pe.Workflow(name="pipeline")
main_pipeline.base_dir = working_dir

reslice_roi_mask = pe.Node(interface=spm.Coregister(), name="reslice_roi_mask")
reslice_roi_mask.inputs.jobtype="write"
reslice_roi_mask.inputs.write_interp = 0
reslice_roi_mask.inputs.target = "/media/data/2010reliability/episize.nii"

def dilateROIMask(filename, dilation_size):
    import numpy as np
    import nibabel as nb
    from scipy.ndimage.morphology import grey_dilation
    import os
    
    nii = nb.load(filename)
    origdata = nii.get_data()
    newdata = grey_dilation(origdata , (2 * dilation_size + 1,
                                       2 * dilation_size + 1,
                                       2 * dilation_size + 1))
    nb.save(nb.Nifti1Image(newdata, nii.get_affine(), nii.get_header()), 'dialted_mask.nii')
    return os.path.abspath('dialted_mask.nii')

dilate_roi_mask = pe.Node(interface=util.Function(input_names=['filename', 'dilation_size'], 
                                                  output_names=['dilated_file'],
                                                  function=dilateROIMask),
                          name = 'dilate_roi_mask')

def getMaskFile(subject_id, task_name):
    from variables import design_parameters, lefties
    if subject_id in lefties and task_name == "finger_foot_lips":
        return design_parameters[task_name]['mask_file'].replace("left", "right")
    else:
        return design_parameters[task_name]['mask_file']
    
get_mask_file = pe.Node(interface=util.Function(function=getMaskFile,
                                                input_names=['subject_id', 'task_name'],
                                                output_names = "mask_file"),
                        name="get_mask_file")
main_pipeline.connect([(tasks_infosource, get_mask_file, [('task_name', 'task_name')]),
                       (subjects_infosource, get_mask_file, [('subject_id', 'subject_id')]),
                       (get_mask_file, dilate_roi_mask, [('mask_file', 'filename')]),
                       (tasks_infosource, dilate_roi_mask, [(('task_name', getDilation), 'dilation_size')]),
                       (dilate_roi_mask, reslice_roi_mask, [('dilated_file',"source")]),
                       ])



main_pipeline.connect([(subjects_infosource, datasource, [('subject_id', 'subject_id')]),
                       (tasks_infosource, datasource, [('task_name', 'task_name')]),
                       
                       (thr_method_infosource, functional_run, [('thr_method', 'model.thr_method_inputspec.thr_method'),
                                                                ('thr_method', 'report.visualise_thresholded_stat.inputnode.prefix')]),
                       (roi_infosource, functional_run, [('roi', 'model.roi_inputspec.roi')]),
                       (datasource, functional_run, [("func", "inputnode.func"),
                                                     ("T1","inputnode.struct")]),
                       (tasks_infosource, functional_run, [(('task_name', getConditions), 'inputnode.conditions'),
                                                                         (('task_name', getDurations), 'inputnode.durations'),
                                                                         (('task_name', getTR), 'inputnode.TR'),
                                                                         (('task_name', getContrasts), 'inputnode.contrasts'),
                                                                         (('task_name', getUnits), 'inputnode.units'),
                                                                         (('task_name', getOnsets), 'inputnode.onsets'),
                                                                         (('task_name', getSparse), 'inputnode.sparse'),
                                                                         ('task_name', 'inputnode.task_name')]),
                       (reslice_roi_mask, functional_run, [('coregistered_source','inputnode.mask_file')]),                       

                       (functional_run, datasink, [('report.visualise_thresholded_stat.reslice_overlay.coregistered_source', 'volumes.t_maps.thresholded')]),
                       (functional_run, datasink, [('report.visualise_unthresholded_stat.reslice_overlay.coregistered_source', 'volumes.t_maps.unthresholded')]),
                       (datasource, datasink, [("T1","volumes.T1")]),
                       
                       (functional_run, datasink, [('report.psmerge_all.merged_file', 'reports')]),
#                       (functional_run, datasink, [('preproc_func.pre_ica.report_dir', 'reports.pre_ica')]),
#                       (functional_run, datasink, [('preproc_func.post_ica.report_dir', 'reports.post_ica')]),
                       
#                       (subjects_infosource, sqlitesink, [('subject_id', 'subject_id')]),
#                       (tasks_infosource, sqlitesink, [('task_name', 'task_name'),
#                                                       (('task_name', getStatLabels), 'contrast_name')]),
#                       (roi_infosource, sqlitesink, [('roi', 'roi')]),
#                       (functional_run, sqlitesink, [('model.threshold_topo_ggmm.ggmm.threshold','cluster_forming_threshold'),
#                                                     ('model.threshold_topo_fdr.cluster_forming_thr','cluster_forming_threshold_fwe'),
#                                                     ('model.threshold_topo_ggmm.ggmm.selected_model', 'selected_model'),
#                                                     ('model.threshold_topo_ggmm.topo_fdr.activation_forced','activation_forced'),
#                                                     ('model.threshold_topo_ggmm.topo_fdr.n_clusters','n_clusters'),
#                                                     ('model.threshold_topo_ggmm.topo_fdr.pre_topo_n_clusters', 'pre_topo_n_clusters')])
                
                       ])

if __name__ == '__main__':
    main_pipeline.run(plugin_args={'n_procs': 4})
    main_pipeline.write_graph()
