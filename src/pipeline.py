import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.io as nio           # Data i/o
import nipype.interfaces.spm as spm
import nipype.interfaces.matlab as mlab      # how to run matlab
from helper_functions import create_pipeline_functional_run, create_dti_workflow

from patient_variables import *
from variables import *
from exclude_patients import exclude_patients
#from nipype.workflows.mrtrix.diffusion import create_mrtrix_dti_pipeline
from neuroutils.nii2dcm import Nifti2DICOM
from analyze_dicoms import analyze_dicoms
import glob
from nipype.interfaces.dcm2nii import Dcm2nii
import json
from nipype.interfaces import fsl

mlab.MatlabCommand.set_default_paths("/usr/share/spm8/")

def create_process_patient_data_workflow(data_dir, work_dir, results_dir, patient_info):
    
    #identifier = patient_info['name'].replace(" ", "_"
    identifier = str(patient_info['StudyID'])
    
    main_pipeline = pe.Workflow(name="pipeline")
    main_pipeline.base_dir = os.path.join(work_dir, identifier)

    tasks_infosource = pe.Node(interface=util.IdentityInterface(fields=['task_name']),
                               name="tasks_infosource")
    tasks_infosource.iterables = ('task_name', patient_info['tasks'].keys())
    
    func_datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_subdir', 
                                                                  'seq_no'],
                                                   outfields=['func']),
                         name = 'func_datasource')
    
    func_datasource.inputs.base_directory = data_dir
    func_datasource.inputs.template = '%s/%s/*.dcm'
    func_datasource.inputs.template_args = dict(func = [['subject_subdir', 
                                                         'seq_no']],
                                           )
    func_datasource.inputs.subject_subdir = patient_info['subdir']
    
    log_datasource = pe.Node(interface=util.IdentityInterface(fields=['line_bisection_log']),
                     name = 'log_datasource')
    log_datasource.inputs.line_bisection_log = log_dir + "/" + str(patient_info['StudyID']) + "-Line_Bisection.log"
    
    def task_name2_seq_no(patient_info, task_name):
        return patient_info['tasks'][task_name]
    
    get_seq_no = pe.Node(interface=util.Function(input_names=['patient_info', 
                                                              'task_name'], 
                                                 output_names=['seq_no'],
                                                 function = task_name2_seq_no),
                         name="get_seq_no")
    get_seq_no.inputs.patient_info = patient_info
    
    main_pipeline.connect([(tasks_infosource, get_seq_no, [('task_name','task_name')]),
                           (get_seq_no, func_datasource, [('seq_no', 'seq_no')])])
    
    func2nii = pe.Node(interface = Dcm2nii(), name="func2nii")
    func2nii.inputs.gzip_output = False
    func2nii.inputs.nii_output = True
    func2nii.inputs.anonymize = True
    
    def pickFirst(l):
        return l[0]
    
    main_pipeline.connect([(func_datasource, func2nii, [(('func', pickFirst), 'source_names')])])
    
    struct_datasource = pe.Node(interface=util.IdentityInterface(fields=['T1', 
                                                                         'DWI',
                                                                         'T2']),
                         name = 'struct_datasource')
    struct_datasource.inputs.T1 = glob.glob(os.path.join(data_dir, 
                                                         patient_info['subdir'], 
                                                         str(patient_info['T1'])) + "/*.dcm")
    struct_datasource.inputs.T2 = glob.glob(os.path.join(data_dir, 
                                                         patient_info['subdir'], 
                                                         str(patient_info['T2'])) + "/*.dcm")
    struct_datasource.inputs.DWI = glob.glob(os.path.join(data_dir, 
                                                         patient_info['subdir'], 
                                                         str(patient_info['DWI'])) + "/*.dcm")
    
    T12nii = func2nii.clone("T12nii")
    main_pipeline.connect([(struct_datasource, T12nii, [(('T1', pickFirst), 'source_names')])])
    T22nii = func2nii.clone("T22nii")
    main_pipeline.connect([(struct_datasource, T22nii, [(('T2', pickFirst), 'source_names')])])
    DWI2nii = func2nii.clone("DWI2nii")
    main_pipeline.connect([(struct_datasource, DWI2nii, [(('DWI', pickFirst), 'source_names')])])
    
    def ConditionalReslice(in_file, reference_file):
        import nibabel as nb
        nii = nb.load(in_file)
        if nii.get_shape()[0] != 128 or nii.get_shape()[1] != 128:
            import nipype.pipeline.engine as pe
            import nipype.interfaces.spm as spm
            import os
            reslice = pe.Node(spm.Coregister(), name='reslice')
            reslice.inputs.source = in_file
            reslice.inputs.target = reference_file
            reslice.inputs.jobtype = 'write'
            reslice.base_dir = os.getcwd()
            results = reslice.run()
            return results.outputs.coregistered_source
            
        else:
            return in_file
        
    cond_reslice = pe.Node(interface=util.Function(input_names=['in_file', 
                                                                 'reference_file'], 
                                                   output_names = ['out_file'], 
                                                   function = ConditionalReslice),
                           name = 'cond_reslice')
    cond_reslice.inputs.reference_file = os.path.join(results_dir, 'dwi_reference.nii')
    
    thr_method_infosource = pe.Node(interface=util.IdentityInterface(fields=['thr_method']),
                                  name="thr_method_infosource")
    thr_method_infosource.iterables = ('thr_method', thr_methods)
    
    struct_datasource.inputs.sort_filelist = True
    
    functional_run = create_pipeline_functional_run(name="functional_run", series_format="4d")
    
    dti_processing = create_dti_workflow()
    if int(patient_info['StudyID']) in dwi_bet_thr:
        dti_processing.inputs.mrtrix.bet.frac = dwi_bet_thr[int(patient_info['StudyID'])]

    datasink = pe.Node(interface = nio.DataSink(), name='datasink')
    datasink.inputs.base_directory = os.path.join(results_dir, identifier)
    
    def getReportFilename(subject_id):
        return "subject_%s_report.pdf"%subject_id
    
    def getConditions(task_name):
        from variables import design_parameters
        return design_parameters[task_name]['conditions']
        
    def getOnsets(task_name, line_bisection_log, delay):
        if task_name == "line_bisection":
            from parse_line_bisection_log import parse_line_bisection_log
            _,_,correct_pictures, incorrect_pictures, noresponse_pictures = parse_line_bisection_log(line_bisection_log, delay)
            return [correct_pictures["task"], incorrect_pictures["task"], noresponse_pictures["task"],
                    correct_pictures["rest"], incorrect_pictures["rest"], noresponse_pictures["rest"]]
        else:
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
    
    def getUnits(task_name):
        from variables import design_parameters
        return design_parameters[task_name]['units']
    
    def getSparse(task_name):
        from variables import design_parameters
        return design_parameters[task_name]['sparse'] 

    def getDicomDesc(task_name):
        from variables import design_parameters
        return [task_name + " " + contrast[0] for contrast in design_parameters[task_name]['contrasts']]
    
    get_onsets = pe.Node(interface=util.Function(input_names=['task_name', 'line_bisection_log', 'delay'], 
                                                        output_names=['onsets'], 
                                                        function=getOnsets),
                         name="get_onsets")
    get_onsets.inputs.delay = 4*2.5
    
    

    coregister_T2_to_T1 = pe.Node(interface=spm.Coregister(), name="coregister_T2_to_T1")
    coregister_T2_to_T1.inputs.jobtype="estwrite"
    
    coregister_T2_to_DWI = pe.Node(spm.Coregister(), name="coregister_T2_to_DWI")
    coregister_T2_to_DWI.inputs.jobtype="estwrite"
    coregister_t_maps_to_DWI = pe.Node(spm.Coregister(), name="coregister_t_maps_to_DWI")
    coregister_t_maps_to_DWI.inputs.jobtype="estwrite"
    coregister_t_maps_to_DWI.inputs.write_interp = 0
    
    bet = pe.Node(interface=fsl.BET(), name="bet")
    
    main_pipeline.connect([(T12nii, coregister_T2_to_T1, [('reoriented_files', 'target')]),
                           (T22nii, coregister_T2_to_T1, [('converted_files', 'source')]),
                           
                           (T12nii, bet, [('reoriented_files', 'in_file')]),
                           
                           (thr_method_infosource, functional_run, [('thr_method', 'model.thr_method_inputspec.thr_method'),
                                                                    ('thr_method', 'visualise_thresholded_stat.inputnode.prefix')]),
                           (func2nii, functional_run, [("converted_files", "inputnode.func")]),
                           (T12nii, functional_run, [("reoriented_files","inputnode.struct")]),
                           (tasks_infosource, functional_run, [(('task_name', getConditions), 'inputnode.conditions'),
                                                                (('task_name', getDurations), 'inputnode.durations'),
                                                                (('task_name', getTR), 'inputnode.TR'),
                                                                (('task_name', getContrasts), 'inputnode.contrasts'),
                                                                (('task_name', getUnits), 'inputnode.units'),
                                                                (('task_name', getSparse), 'inputnode.sparse'),
                                                                ('task_name', 'inputnode.task_name')]),     
                           (tasks_infosource, get_onsets, [('task_name', 'task_name')]),
                           (log_datasource, get_onsets, [('line_bisection_log', 'line_bisection_log')]),
                           (get_onsets, functional_run, [('onsets', 'inputnode.onsets')]),     
                           
                           (DWI2nii, cond_reslice, [('converted_files', 'in_file')]),
                           (cond_reslice, dti_processing, [('out_file', 'inputnode.dwi')]),
                           (DWI2nii, dti_processing, [('bvals', 'inputnode.bvals'),
                                                      ('bvecs', 'inputnode.bvecs')]),
                           (dti_processing, datasink, [('mrtrix.CSDstreamtrack.tracked', 'DTI.tracts')]),
                           
                           (T12nii, coregister_T2_to_DWI, [('reoriented_files', 'source')]),
                           (T12nii, coregister_t_maps_to_DWI, [('reoriented_files', 'source')]),
                           (coregister_T2_to_T1, coregister_T2_to_DWI, [('coregistered_source', 'apply_to_files')]),
                           (functional_run, coregister_t_maps_to_DWI, [('visualise_thresholded_stat.reslice_overlay.coregistered_source', 'apply_to_files')]),
                           (dti_processing, coregister_T2_to_DWI, [('mrtrix.bet.out_file', 'target')]),
                           (dti_processing, coregister_t_maps_to_DWI, [('mrtrix.bet.out_file', 'target')]),
                           
                           (coregister_T2_to_DWI, datasink, [('coregistered_source', 'DTI.coregistered_T1')]),
                           (coregister_T2_to_DWI, datasink, [('coregistered_files', 'DTI.coregistered_T2')]),
                           (coregister_t_maps_to_DWI, datasink, [('coregistered_files', 'DTI.coregistered_t_maps')]),
                           
                           (functional_run, datasink, [('report.visualise_unthresholded_stat.reslice_overlay.coregistered_source', 'volumes.t_maps.unthresholded')]),
                           (functional_run, datasink, [('visualise_thresholded_stat.reslice_overlay.coregistered_source', 'volumes.t_maps.thresholded')]),
                           (T12nii, datasink, [('reoriented_files', 'volumes.T1')]),
                           (bet, datasink, [('out_file', 'volumes.T1_no_skull')]),
                           (coregister_T2_to_T1, datasink, [('coregistered_source', 'volumes.T2')]),
                           (functional_run, datasink, [('report.psmerge_all.merged_file', 'reports')]),
                           (functional_run, datasink, [('visualise_thresholded_stat_merge.merged_file', 'reports.@thr')]),
                           (functional_run, datasink, [('model.threshold_topo_ggmm.ggmm.histogram', 'reports.@ggmm')]),
                           ])
    
    dicom_pipeline = pe.Workflow(name="pipeline")
    dicom_pipeline.base_dir = os.path.join(secure_dir, identifier)
    
    nii2dcm = pe.MapNode(interface=Nifti2DICOM(), iterfield=['nifti_file', 'description'], 
                         name="nii2dcm")
    nii2dcm.inputs.overlay = True
    nii2dcm.inputs.UID_suffix = 100
    
    tasks_infosource = pe.Node(interface=util.IdentityInterface(fields=['task_name']),
                               name="tasks_infosource")
    tasks_infosource.iterables = ('task_name', patient_info['tasks'].keys())
    
    thr_method_infosource = pe.Node(interface=util.IdentityInterface(fields=['thr_method']),
                                    name="thr_method_infosource")
    thr_method_infosource.iterables = ('thr_method', thr_methods)
    
    func_datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_subdir', 
                                                                  'seq_no'],
                                                   outfields=['func']),
                              name = 'func_datasource')
    
    func_datasource.inputs.base_directory = data_dir
    func_datasource.inputs.template = '%s/%s/*.dcm'
    func_datasource.inputs.template_args = dict(func = [['subject_subdir', 
                                                         'seq_no']])
    func_datasource.inputs.subject_subdir = patient_info['subdir']
    
    get_seq_no = pe.Node(interface=util.Function(input_names=['patient_info', 
                                                              'task_name'], 
                                                 output_names=['seq_no'],
                                                 function = task_name2_seq_no),
                         name="get_seq_no")
    get_seq_no.inputs.patient_info = patient_info
    
    dicom_pipeline.connect([(tasks_infosource, get_seq_no, [('task_name','task_name')]),
                           (get_seq_no, func_datasource, [('seq_no', 'seq_no')])])
    
    struct_datasource = pe.Node(interface=util.IdentityInterface(fields=['T1']),
                         name = 'struct_datasource')
    struct_datasource.inputs.T1 = glob.glob(os.path.join(data_dir, 
                                                         patient_info['subdir'], 
                                                         str(patient_info['T1'])) + "/*.dcm")
    
    t_maps_datasource = pe.Node(interface=nio.DataGrabber(infields=['identifier', 
                                                                    'task_name',
                                                                    'thr_method'],
                                                   outfields=['t_maps']),
                         name = 't_maps_datasource',
                         overwrite=True)
    
    t_maps_datasource.inputs.base_directory = results_dir
    t_maps_datasource.inputs.template = '%s/volumes/t_maps/thresholded/_task_name_%s/_thr_method_%s/_reslice_overlay*/*.img'
    t_maps_datasource.inputs.template_args = dict(t_maps = [['identifier', 
                                                                    'task_name',
                                                                    'thr_method']],
                                           )
    t_maps_datasource.inputs.identifier = identifier
    
    dicom_pipeline.connect([
                           (func_datasource, nii2dcm, [(('func', pickFirst), 'series_info_source_dicom')]),
                           (tasks_infosource,  nii2dcm, [(('task_name',getDicomDesc), 'description')]),
                           (struct_datasource, nii2dcm, [('T1', 'template_DICOMS')]),
                           (tasks_infosource, t_maps_datasource, [('task_name', 'task_name')]),
                           (thr_method_infosource, t_maps_datasource, [('thr_method', 'thr_method')]),
                           (t_maps_datasource, nii2dcm, [('t_maps', 'nifti_file')]),
                           ])

    
    return main_pipeline, dicom_pipeline

if __name__ == '__main__':
    patients = analyze_dicoms(data_dir, exclude_patients)
    if not skip_secure:
        json.dump(patients, open(os.path.join(secure_dir, "info.txt"),'w'))
    for patient_info in patients.values():
        main_pipeline, secure_pipeline = create_process_patient_data_workflow(data_dir, working_dir, results_dir, patient_info)
        main_pipeline.run(plugin_args={'n_procs': 4})
        #main_pipeline.write_graph()
        if not skip_secure:
            secure_pipeline.run(plugin_args={'n_procs': 4})
            secure_pipeline.write_graph()
