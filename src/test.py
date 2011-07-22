'''
Created on 8 Nov 2010

@author: filo
'''
from nipype.utils.filemanip import loadflat
from neuroutils import ThresholdGGMM

c = loadflat("/media/data/2010reliability/workdir/pipeline/line_bisection/model/threshold_topo_ggmm/_subject_id_20100929_16849/ggmm/crash-20101116-135736-filo-_ggmm2.npz")
n = c['node']
print n.inputs

ggmm = ThresholdGGMM(mask_file= n.inputs.mask_file, stat_image=n.inputs.stat_image)

ggmm.run()