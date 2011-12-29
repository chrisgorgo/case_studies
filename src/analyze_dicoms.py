'''
Created on 24 Nov 2011

@author: filo
'''
import os,re
import glob
import dicom

def update(up_collection, cur_collection, overwrite):
    exclude_keys = ['StudyID', 'subdir', 'name']
    for key1, value1 in cur_collection.iteritems():
        if (overwrite or key1 not in up_collection) and key1 not in exclude_keys:
            if isinstance(value1, dict):
                update(up_collection[key1], value1, overwrite)
            else:
                up_collection[key1] = value1

def analyze_dicoms(sdir, exclude):
    
    patients = {}
    for subject in os.listdir(sdir):
        if int(subject.split("_")[-1]) in [int(s) for s in exclude]:
            continue
        cur_patient = {}
        subdirs = os.listdir(os.path.join(sdir, subject))
        assert len(subdirs) == 1
        cur_dir = os.path.join(sdir, subject, subdirs[0])
        cur_subdir = os.path.join(subject, subdirs[0])
        cur_patient['subdir'] = os.path.join(subject, subdirs[0])
        cur_dir_list = [os.path.join(cur_dir,x) for x in os.listdir(cur_dir) if re.match(".*[0-9]+", x)]
        cur_dir_list = filter(lambda x: os.path.isdir(x), cur_dir_list)
        print cur_dir_list
        
        for seq_dir in cur_dir_list:
            first_dcm = glob.glob(seq_dir+"/*.dcm")[0]
            ds = dicom.read_file(first_dcm, force=True)
            cur_patient['name'] = ds.PatientsName
            cur_patient['StudyID'] = ds.StudyID
            if ds.PatientsName in patients:
                ser_num = "../../" + cur_subdir + "/" + str(ds.SeriesNumber)
            else:
                ser_num = str(ds.SeriesNumber)
            if ds.SeriesDescription == "COR 3D IR PREP":
                cur_patient['T1'] = ser_num
            elif ds.SeriesDescription == "Axial T2":
                cur_patient['T2'] = ser_num
            elif ds.SeriesDescription == "DTI 64G 2.0 mm isotropic":
                cur_patient['DWI'] = ser_num
            print ds.SeriesDescription
            if ds.SeriesDescription in ['finger foot lips', 'silent verb generation', 'word repetition', 'line bisection']:
                if len(glob.glob(seq_dir+"/*.dcm")) > 180:
                    if 'tasks' not in cur_patient.keys():
                        cur_patient['tasks'] = {}
                    if ds.SeriesDescription == 'silent verb generation':
                        cur_patient['tasks']['covert_verb_generation'] = ser_num
                    elif ds.SeriesDescription == 'word repetition':
                        cur_patient['tasks']['overt_word_repetition'] = ser_num
                    else:
                        cur_patient['tasks'][ds.SeriesDescription.replace(" ", "_")] = ser_num
        
        if ds.PatientsName not in patients:
            patients[cur_patient['name']] = cur_patient
        else:
            cur_study_id = cur_patient['StudyID']
            prev_study_id = patients[cur_patient['name']]['StudyID']
            cur_collection = cur_patient
            up_collection = patients[cur_patient['name']]
            update(up_collection, cur_collection, cur_study_id > prev_study_id)
        
    return patients