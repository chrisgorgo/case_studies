'''
Created on 24 Nov 2011

@author: filo
'''
import os,re
import glob
import dicom
def analyze_dicoms(sdir):
    
    patients = {}
    for subject in os.listdir(sdir):
        cur_patient = {}
        subdirs = os.listdir(os.path.join(sdir, subject))
        assert len(subdirs) == 1
        cur_dir = os.path.join(sdir, subject, subdirs[0])
        cur_patient['subdir'] = os.path.join(subject, subdirs[0])
        cur_dir_list = [os.path.join(cur_dir,x) for x in os.listdir(cur_dir) if re.match(".*[0-9]+", x)]
        cur_dir_list = filter(lambda x: os.path.isdir(x), cur_dir_list)
        print cur_dir_list
        
        for seq_dir in cur_dir_list:
            first_dcm = glob.glob(seq_dir+"/*.dcm")[0]
            ds = dicom.read_file(first_dcm, force=True)
            cur_patient['name'] = ds.PatientsName
            cur_patient['StudyID'] = ds.StudyID
            if ds.SeriesDescription == "COR 3D IR PREP":
                cur_patient['T1'] = ds.SeriesNumber
            elif ds.SeriesDescription == "Axial T2":
                cur_patient['T2'] = ds.SeriesNumber
            elif ds.SeriesDescription == "DTI 64G 2.0 mm isotropic":
                cur_patient['DWI'] = ds.SeriesNumber
            if ds.SeriesDescription in ['finger foot lips', 'silent verb generation', 'overt word repetition', 'line bisection']:
                if 'tasks' not in cur_patient.keys():
                    cur_patient['tasks'] = {}
                if ds.SeriesDescription == 'silent verb generation':
                    cur_patient['tasks']['covert_verb_generation'] = ds.SeriesNumber
                else:
                    cur_patient['tasks'][ds.SeriesDescription.replace(" ", "_")] = ds.SeriesNumber
        
        
        patients[cur_patient['name']] = cur_patient
        
    return patients