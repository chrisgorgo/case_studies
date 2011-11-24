import nipype.interfaces.utility as util     # utility
import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.io as nio           # Data i/o
import nipype.interfaces.spm as spm
import nipype.interfaces.matlab as mlab      # how to run matlab
from helper_functions import create_pipeline_functional_run

from variables import *
from exclude_patients import exclude_patients
#from nipype.workflows.mrtrix.diffusion import create_mrtrix_dti_pipeline
from neuroutils.nii2dcm import Nifti2DICOM
from analyze_dicoms import analyze_dicoms
import glob
from nipype.interfaces.dcm2nii import Dcm2nii

mlab.MatlabCommand.set_default_paths("/usr/share/spm8/")

def create_process_patient_data_workflow(data_dir, work_dir, results_dir, patient_info):
    
    main_pipeline = pe.Workflow(name="pipeline")
    main_pipeline.base_dir = os.path.join(work_dir, patient_info['name'].replace(" ", "_"))

    tasks_infosource = pe.Node(interface=util.IdentityInterface(fields=['task_name']),
                               name="tasks_infosource")
    tasks_infosource.iterables = ('task_name', patient_info['tasks'].keys())
    
    func_datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_subdir', 
                                                                  'seq_no'],
                                                   outfields=['func']),
                         name = 'func_datasource')
    
    func_datasource.inputs.base_directory = data_dir
    func_datasource.inputs.template = '%s/%d/*.dcm'
    func_datasource.inputs.template_args = dict(func = [['subject_subdir', 
                                                         'seq_no']],
                                           )
    func_datasource.inputs.subject_subdir = patient_info['subdir']
    
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
    
    thr_method_infosource = pe.Node(interface=util.IdentityInterface(fields=['thr_method']),
                                  name="thr_method_infosource")
    thr_method_infosource.iterables = ('thr_method', thr_methods)
    
    struct_datasource.inputs.sort_filelist = True
    
    functional_run = create_pipeline_functional_run(name="functional_run", series_format="4d")

    datasink = pe.Node(interface = nio.DataSink(), name='datasink')
    datasink.inputs.base_directory = os.path.join(results_dir, patient_info['name'].replace(" ", "_"))
    
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

    coregister_T2 = pe.Node(interface=spm.Coregister(), name="coregister_T2")
    coregister_T2.inputs.jobtype="estwrite"
    
    nii2dcm = pe.MapNode(interface=Nifti2DICOM(), iterfield=['nifti_file', 'description'], 
                         name="nii2dcm")
    nii2dcm.inputs.overlay = True
    nii2dcm.inputs.UID_suffix = 100
    
    main_pipeline.connect([(T12nii, coregister_T2, [('reoriented_files', 'target')]),
                           (T22nii, coregister_T2, [('converted_files', 'source')]),
                           
                           (thr_method_infosource, functional_run, [('thr_method', 'model.thr_method_inputspec.thr_method'),
                                                                    ('thr_method', 'report.visualise_thresholded_stat.inputnode.prefix')]),
                           (func2nii, functional_run, [("converted_files", "inputnode.func")]),
                           (T12nii, functional_run, [("reoriented_files","inputnode.struct")]),
                           (tasks_infosource, functional_run, [(('task_name', getConditions), 'inputnode.conditions'),
                                                                (('task_name', getDurations), 'inputnode.durations'),
                                                                (('task_name', getTR), 'inputnode.TR'),
                                                                (('task_name', getContrasts), 'inputnode.contrasts'),
                                                                (('task_name', getUnits), 'inputnode.units'),
                                                                (('task_name', getOnsets), 'inputnode.onsets'),
                                                                (('task_name', getSparse), 'inputnode.sparse'),
                                                                ('task_name', 'inputnode.task_name')]),                     
                           
                           (func_datasource, nii2dcm, [(('func', pickFirst), 'series_info_source_dicom')]),
                           (tasks_infosource,  nii2dcm, [(('task_name',getDicomDesc), 'description')]),
                           (struct_datasource, nii2dcm, [('T1', 'template_DICOMS')]),
                           (functional_run, nii2dcm, [('report.visualise_thresholded_stat.reslice_overlay.coregistered_source', 'nifti_file')]),
                           
                           (functional_run, datasink, [('report.visualise_unthresholded_stat.reslice_overlay.coregistered_source', 'volumes.t_maps.unthresholded')]),
                           (functional_run, datasink, [('report.visualise_thresholded_stat.reslice_overlay.coregistered_source', 'volumes.t_maps.thresholded')]),
                           (T12nii, datasink, [('reoriented_files', 'volumes.T1')]),
                           (coregister_T2, datasink, [('coregistered_source', 'volumes.T2')]),
                           (functional_run, datasink, [('report.psmerge_all.merged_file', 'reports')]),
                           (nii2dcm, datasink, [('DICOMs', 'neuronav_dicoms.t_maps.thresholded')])
                           ])
    return main_pipeline

if __name__ == '__main__':
    patients = analyze_dicoms(data_dir)
    for patient_info in patients.values():
        if patient_info['name'] in exclude_patients:
            continue
        if 'line_bisection' in patient_info['tasks']:
            patient_info['tasks'].pop('line_bisection')
        main_pipeline = create_process_patient_data_workflow(data_dir, working_dir, results_dir, patient_info)
        main_pipeline.run(plugin_args={'n_procs': 4})
        main_pipeline.write_graph()
