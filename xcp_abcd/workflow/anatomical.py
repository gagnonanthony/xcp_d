# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
fectch anatomical files/resmapleing surfaces to fsl32k 
^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: init_structral_wf

"""

import os
import fnmatch, re
from pathlib import Path
import numpy as np
from templateflow.api import get as get_template
from ..utils import collect_data,select_registrationfile,CiftiSurfaceResample
from nipype.interfaces.freesurfer import MRIsConvert
from ..interfaces.connectivity import ApplyTransformsx
from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from pkg_resources import resource_filename as pkgrf
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype import MapNode as MapNode


def init_anatomical_wf(
     omp_nthreads,
     bids_dir,
     subject_id,
     output_dir,
     t1w_to_mni,
     name='anatomical_wf',
      ):
     workflow = Workflow(name=name)

     outputnode = pe.Node(niu.IdentityInterface(
        fields=['t1w_mni','seg_mni','wm_surf_left','pial_surf_left','midthick_surf_letf','inf_surf_left',
        'wm_surf_right','pial_surf_right','midthick_surf_right','inf_surf_right']),
        name='outputnode')

     MNI92FSL  = pkgrf('xcp_abcd', 'data/transform/FSL2MNI9Composite.h5')
     mnitemplate = str(get_template(template='MNI152NLin6Asym',resolution=2, suffix='T1w')[-1])
     layout,subj_data = collect_data(bids_dir=bids_dir,participant_label=subject_id)
     
     all_t1w = subj_data['t1w'] 
     for i in all_t1w:
          ii = os.path.basename(i)
          if  not fnmatch.fnmatch(ii,'*_space-*'):
               t1w = i

     all_seg = subj_data['seg']
     for i in all_seg:
          ii=os.path.basename(i)
          if  not (fnmatch.fnmatch(ii,'*_space-*') or fnmatch.fnmatch(ii,'*aseg*')):
               seg = i
     t1w_to_mni = select_registrationfile(subj_data=subj_data)
     
     t1w_transform = pe.Node(ApplyTransformsx(input_image=t1w,num_threads=2,rreference_image=mnitemplate,
                       transforms=[str(t1w_to_mni),str(MNI92FSL)],interpolation='NearestNeighbor',
                       input_image_type=3, dimension=3),
                       name="t1w_transform", mem_gb=2)

     seg_transform = pe.Node(ApplyTransformsx(input_image=seg,num_threads=2,rreference_image=mnitemplate,
                       transforms=[str(t1w_to_mni),str(MNI92FSL)],interpolation="MultiLabel",
                       input_image_type=3, dimension=3),
                       name="seg_transform", mem_gb=2)

     workflow.connect([
          (t1w_transform,outputnode,[('output_image','t1w_mni')])
          (seg_transform,outputnode,[('output_image','seg_mni')])
         ])

     #verify fresurfer directory

     p = Path(bids_dir)
     freesufer_path = Path(str(p.parent)+'/freesurfer')
     if freesufer_path.is_dir(): 
          all_files  =list(layout.get_files())
          L_inflated_surf  = fnmatch.filter(all_files,'*hemi-L_inflated.surf.gii')
          R_inflated_surf  = fnmatch.filter(all_files,'*hemi-R_inflated.surf.gii')
          L_midthick_surf  = fnmatch.filter(all_files,'*hemi-L_midthickness.surf.gii')
          R_midthick_surf  = fnmatch.filter(all_files,'*hemi-R_midthickness.surf.gii')
          L_pial_surf  = fnmatch.filter(all_files,'*hemi-L_pial.surf.gii')
          R_pial_surf  = fnmatch.filter(all_files,'*hemi-R_pial.surf.gii')
          L_wm_surf  = fnmatch.filter(all_files,'*hemi-L_smoothwm.surf.gii')
          R_wm_surf  = fnmatch.filter(all_files,'*hemi-R_smoothwm.surf.gii')

          # get sphere surfaces to be converted
          if 'sub-' not in subject_id:
               subid ='sub-'+ subject_id
          else:
               subid = subject_id
          
          left_sphere = str(freesufer_path)+'/'+subid+'/surf/lh.sphere.reg'
          right_sphere = str(freesufer_path)+'/'+subid+'/surf/rh.sphere.reg'  
          
          left_sphere_fsLR = str(get_template(template='fsLR',hemi='L',density='32k',suffix='sphere')[0])
          right_sphere_fsLR = str(get_template(template='fsLR',hemi='R',density='32k',suffix='sphere')[0]) 

          # nodes for letf and right in node
          left_sphere_mris = pe.Node(MRIsConvert(out_datatype='gii',in_file=left_sphere),name='left_sphere')
          right_sphere_mris = pe.Node(MRIsConvert(out_datatype='gii',in_file=right_sphere),name='right_sphere')
          
         
          ## surface resample to fsl32k
          left_wm_surf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_wm_surf), name="left_wm_surf",mem_gb=2)
          left_pial_surf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_pial_surf), name="left_pial_surf",mem_gb=2)
          left_midthick_surf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_midthick_surf), name="left_midthick_surf",mem_gb=2)
          left_inf_surf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_inflated_surf), name="left_inflated_surf",mem_gb=2)
          

          right_wm_surf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_wm_surf), name="right_wm_surf",mem_gb=2)
          right_pial_surf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_pial_surf), name="right_pial_surf",mem_gb=2)
          right_midthick_surf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_midthick_surf), name="right_midthick_surf",mem_gb=2)
          right_inf_surf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_inflated_surf), name="right_inflated_surf",mem_gb=2)

          workflow.connect([ 
               (left_sphere_mris,left_wm_surf,[('out_file','new_sphere')]),
               (left_sphere_mris,left_pial_surf,[('out_file','new_sphere')]),
               (left_sphere_mris,left_midthick_surf,[('out_file','new_sphere')]),
               (left_sphere_mris,left_inf_surf,[('out_file','new_sphere')]),

               (right_sphere_mris,right_wm_surf,[('out_file','new_sphere')]),
               (right_sphere_mris,right_pial_surf,[('out_file','new_sphere')]),
               (right_sphere_mris,right_midthick_surf,[('out_file','new_sphere')]),
               (right_sphere_mris,right_inf_surf,[('out_file','new_sphere')]),

               (left_wm_surf,outputnode,[('out_file','wm_surf_left')]),
               (left_pial_surf,outputnode,[('out_file','pial_surf_left')]),
               (left_midthick_surf,outputnode,[('out_file','midthick_surf_left')]),
               (left_inf_surf,outputnode,[('out_file','inf_surf_left')]),

               (right_wm_surf,outputnode,[('out_file','wm_surf_right')]),
               (right_pial_surf,outputnode,[('out_file','pial_surf_right')]),
               (right_midthick_surf,outputnode,[('out_file','midthick_surf_right')]),
               (right_inf_surf,outputnode,[('out_file','inf_surf_right')]),
              ])          
     return workflow

























