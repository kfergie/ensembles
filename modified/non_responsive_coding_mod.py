import numpy as np
import pandas as pd
import os
import sys
import h5py
import matplotlib.pyplot as plt

def cre_2_layer(cre_line):
    '''Returns the layer associated with a given Cre line. 

    Parameters
    ----------
    cre_line:
        string detailing the specific Cre line.

    Returns
    -------
    unspecified variable:
        the specific layer associated with a given Cre line. 
    '''
    if cre_line == 'Cux2-CreERT2':
        return 'Layer 2/3 & 4'
    elif cre_line == 'Emx1-IRES-Cre':
        return 'Pan excitatory expression'
    elif cre_line == 'Nr5a1-Cre':
        return 'Layer 4'
    elif cre_line == 'Rbp4-Cre_KL100':
        return 'Layer 5'
    elif cre_line == 'Rorb-IRES2-Cre':
        return 'Layer 4'
    elif cre_line == 'Scnn1a-Tg3-Cre':
        return 'Layer 4'
    else:
        return ValueError('Cre line not found.')

def get_exp_container_dataframe(boc, exp_container_id):
    '''Creates a pandas dataframe for a single experimental container.
    
    Parameters
    ---------- 
    boc:
        BrainObservatoryCache variable 

    exp_container: 
        the experimental container id for one mouse
    
    Returns
    ------- 
    expt_container_df: 
        dataframe for all experimental data corresponding to a single experimental container id
    '''
    # grab the session info for the given experiment 
    exp_session_info = boc.get_ophys_experiments(experiment_container_ids=[exp_container_id]) 
    # create data frame of experimental sessions in our container
    exp_session_df = pd.DataFrame(exp_session_info) 
    return exp_session_df

def get_session_ids(boc, exp_list):
    '''Extracts the session ids for a given list of experiment container ids.

    Parameters
    ----------

    boc:
        BrainObservatoryCache variable 

   	exp_list: 
        a list of experimental containers ids for the mice of interest
    
    Returns
    ------- 
    session_ids: 
        a dictionary whose keys are experiment container ids and corresponding values are dictionaries pairing session type [A,B,C/C2] with session ID
    
    NOTE: C and C2 are mutually exclusive options. Mice run before 09/2016 at the Allen are run on procedure C.
    After this date, an additional sparse noise stimuli is added to the session and it is renamed session C2 for all future mice
    '''
    # create empty dictionary using the experiment container ids
    session_ids = {exp_id : {} for exp_id in exp_list}
    # extract the session metadata for all experiments
    exp_session_info = boc.get_ophys_experiments(experiment_container_ids=exp_list)
    # iterate over the sessions
    for session in exp_session_info:
    	# grab the experiment container id, session type, and session id
    	exp_id = session['experiment_container_id']
    	## TODO(?): rename session_id_C2 to session_id_C (although this may not be necessary)
    	session_type = session['session_type']
    	session_id = session['id']
    	# toss the session id into the corresponding dictionary
    	session_ids[exp_id][session_type] = session_id
    return session_ids

def get_dataset(boc, exp_list, session_type):
    '''Retrieve datasets of a specific session type for a list of experimental containers.

    Parameters
    ---------- 

    boc:
        BrainObservatoryCache variable 

    exp_list:
        list of experimental containers
    
    session_type: 
        choose from one of the following: ['session_id_A', 'session_id_B', or 'session_id_C']
 
    Returns
    -------
    datasets:
        dictionary whose keys are experiment container ids and values are the dataset object
    '''
    datasets = {}
    # grab the session ids
    session_ids = get_session_ids(boc, exp_list)
    # iterate over the experiment ids
    for exp in exp_list:
        # grab the dataset; oddly enough this function only takes one id at a time 
        dataset = boc.get_ophys_experiment_data(ophys_experiment_id=(session_ids[exp][session_type]))
        datasets[exp] = dataset

    return datasets

####

def get_epoch_table(exps, datasets):
    '''
    Creates dictionary where value is experimental container number key is the epoch table associated with exp container for a given session type
     INPUT:
        exps: list of experimental containers
        datasets: dataset varialbe attained from function get_dataset()
     OUTPUT: 
         epochtable: list of epochs (stimulus type for session type A, B, or C) with start and stop frame numbers for each epoch
            note: each exp container has its own unique epochtable
    NOTE: This for loop will take at least 5 minutes to run
    '''
    epochtable={}
    for exp in exps:
        epochtable[exp]=datasets[exp].get_stimulus_epoch_table()
    return epochtable

def create_delta_traces(datasets, exps, epochtable):
    """Retrieve calcium traces by epoch (stimulus type) from a dictionary of datasets of a given type (session A, B, or C)
            for a list of experimental containers.
            exps must be same list used in get_dataset() function
            dataset must be generated by get_dataset() function
    INPUT:
        exps: list of experimental containers
        datasets: dataset varialbe attained from function get_dataset()
        epochtable: use dictionary from get_epoch_tables() function where values=exp cont's and keys=epoch tables
    OUTPUT: 
       
        ca_by_exp: this is a dictionary where each value is an experimental container
            each key is a nested dictionary where value/key pairs are epoch type and its corresponsing ca2+ trace
                note: if a stimulus type is present more than once in a session, its traces are concatenated into one trace
    NOTE: This for loop is inefficient and will take a minute to run
            """
    delta_traces={}
    ca_by_exp={}
    for exp in exp_lis:
        X=datasets[exp].get_dff_traces()
        if exp==exp_lis[0]:
            epochtable_list=epochtable[exps[0]]['stimulus'].unique()
        timestamps=X[0]
        trace=X[1]
        delta_traces[exp]=[timestamps, trace]
        ca_trace_by_epoch={}
        for stim_n in epochtable_list:
            curr_ca = []
            for ind, stim_row in epochtable[exps[0]].iterrows():
                if stim_row['stimulus'] == stim_n:
                    Ca=delta_traces[exp][1]
                    curr_ca.append(Ca[:, stim_row['start'] : stim_row['end']])
            curr_ca = np.concatenate(curr_ca, axis=1)
            ca_trace_by_epoch[stim_n] = curr_ca
        ca_by_exp[exp]=ca_trace_by_epoch
    return ca_by_exp

def get_epoch_list(exps, epochtable):
    """Creates list of stimulus types for given session
     INPUT:
        exps: list of experimental containers
        epochtalbe: Use epochtable attained from function get_epoch_table
     OUTPUT: 
         epochtable_list: a list of epoch type (stimulus type) for a given session type (A, B, or C)
            note: this is universal for all experimental containers and only indicates stimulus type present in session"""
    epochtable_list=epochtable[exps[0]]['stimulus'].unique()
    return epochtable_list

def get_stim_dict(exps, datasets):
    """ Creates dictionary to determine timing of different images in natural scenes epoch
    INPUT:
        exps: list of experimental containers
        datasets: dataset varialbe attained from function get_dataset()
    OUTPUT:
        stim_dict: a dictionary where each value is an experimental container id
            each key is the frame numbers for individual images presented during natural scenes"""
    stim_dict={}
    for exp in exps:
        temp_exp_df=datasets[exp]
        stim_dict[exp]=temp_exp_df.get_stimulus_table(stimulus_name='natural_scenes')
    return stim_dict

def get_responsivity_status(exps, cell_specimens, sessiontype):
    """ Creates a dictionary cell_categories
        Value=exp container id
        keys= dictionaries for different categories of responsivity
    Input:
        exps: list of experimental containers
        cell_specimens=DataFrame for all cell related information for Brain Observatory cache
        sessiontype: choose from one of the following: ['session_id_A', 'session_id_B', or 'session_id_C']
    Output:
        cell_categories:dictionary of dictionaries indicating responsivity profiles
    """
    ns_nor_={}
    sg_nor_={}
    dg_nor_={}
    nor_={}
    all_={}

    for exp in exps:
        #Isolate cells for experimental container id
        expt_container_id=exp
        specimens=cell_specimens[(cell_specimens['experiment_container_id']==expt_container_id)]
        all_[exp]=specimens['cell_specimen_id']
    
        #Totally non-responsive cells
        isnor = ((specimens.p_dg>0.05) | (specimens.peak_dff_dg<3)) & ((specimens.p_sg>0.05) | (specimens.peak_dff_sg<3)) & ((specimens.p_ns>0.05) | (specimens.peak_dff_ns<3)) & (specimens.rf_chi2_lsn>0.05)
        nor=specimens[isnor] 
        nor_[exp]=nor['cell_specimen_id']
    
        #Non-responsive to ns
        if sessiontype=='session_id_B':
            isepochnor=((specimens.p_ns>0.05) | (specimens.peak_dff_ns<3))
            ns_nor=specimens[~isnor & isepochnor]
            ns_nor_[exp]=ns_nor['cell_specimen_id']
    
        #Non-responsive to dg
        if sessiontype=='session_id_A':
            isepochnor=((specimens.p_dg>0.05) | (specimens.peak_dff_dg<3))
            dg_nor=specimens[~isnor & isepochnor]
            dg_nor_[exp]=dg_nor['cell_specimen_id']
    
        #Non-responsive to sg
        if sessiontype=='session_id_B':
            isepochnor=((specimens.p_sg>0.05) | (specimens.peak_dff_sg<3))
            sg_nor=specimens[~isnor & isepochnor]
            sg_nor_[exp]=sg_nor['cell_specimen_id']
    if sessiontype=='session_id_A':
        cell_categories={'nor_':nor_, 'all_':all_, 'dg_nor_':dg_nor_}
    if sessiontype=='session_id_B':
        cell_categories={'nor_':nor_, 'ns_nor_':ns_nor_, 'sg_nor_':sg_nor_, 'all_':all_}
    if sessiontype=='session_id_C':
        cell_categories={'nor_':nor_, 'all_':all_}
    return cell_categories

def get_cell_indices(exps, datasets):
    """Creates a dictionary with values as exp container ids
        keys are a dictionary containing cell ids paired with cell indices
        INPUT:
            exps: list of experimental containers
            datasets: dataset varialbe attained from function get_dataset()
        OUTPUT:
            Dictionary, cell_indices_by_expcontainer, pairing cell indices with cell ids"""
    cell_indices_by_expcontainer={}
    
    for exp in exps:
    
        # Create dictionary for id to index map for each exp container
        specimen_index_map = {}
    
        # Get cell specimen ids for session B
        specimens_lis=datasets[exp].get_cell_specimen_ids()
    
        #Get cell indices for session B
        specimen_id_temp=datasets[exp].get_cell_specimen_indices(specimens_lis)
    
        # Create map
        specimen_index_map.update({spid: spind for spid, spind in zip(specimens_lis, specimen_id_temp)})
    
        # Update exp container with id to index map
        cell_indices_by_expcontainer[exp]=specimen_index_map
        
    return cell_indices_by_expcontainer

def get_responsivity_status(exps, cell_specimens, sessiontype):
    """ Creates a dictionary cell_categories
        Value=exp container id
        keys= dictionaries for different categories of responsivity
    Input:
        exps: list of experimental containers
        cell_specimens=DataFrame for all cell related information for Brain Observatory cache
        sessiontype: choose from one of the following: ['session_id_A', 'session_id_B', or 'session_id_C']
    Output:
        cell_categories:dictionary of dictionaries indicating responsivity profiles
    """
    ns_nor_={}
    sg_nor_={}
    dg_nor_={}
    nor_={}
    all_={}

    for exp in exps:
        #Isolate cells for experimental container id
        expt_container_id=exp
        specimens=cell_specimens[(cell_specimens['experiment_container_id']==expt_container_id)]
        all_[exp]=specimens['cell_specimen_id']
    
        #Totally non-responsive cells
        isnor = ((specimens.p_dg>0.05) | (specimens.peak_dff_dg<3)) & ((specimens.p_sg>0.05) | (specimens.peak_dff_sg<3)) & ((specimens.p_ns>0.05) | (specimens.peak_dff_ns<3)) & (specimens.rf_chi2_lsn>0.05)
        nor=specimens[isnor] 
        nor_[exp]=nor['cell_specimen_id']
    
        #Non-responsive to ns
        if sessiontype=='session_id_B':
            isepochnor=((specimens.p_ns>0.05) | (specimens.peak_dff_ns<3))
            ns_nor=specimens[~isnor & isepochnor]
            ns_nor_[exp]=ns_nor['cell_specimen_id']
    
        #Non-responsive to dg
        if sessiontype=='session_id_A':
            isepochnor=((specimens.p_dg>0.05) | (specimens.peak_dff_dg<3))
            dg_nor=specimens[~isnor & isepochnor]
            dg_nor_[exp]=dg_nor['cell_specimen_id']
    
        #Non-responsive to sg
        if sessiontype=='session_id_B':
            isepochnor=((specimens.p_sg>0.05) | (specimens.peak_dff_sg<3))
            sg_nor=specimens[~isnor & isepochnor]
            sg_nor_[exp]=sg_nor['cell_specimen_id']
    if sessiontype=='session_id_A':
        cell_categories={'nor_':nor_, 'all_':all_, 'dg_nor_':dg_nor_}
    if sessiontype=='session_id_B':
        cell_categories={'nor_':nor_, 'ns_nor_':ns_nor_, 'sg_nor_':sg_nor_, 'all_':all_}
    if sessiontype=='session_id_C':
        cell_categories={'nor_':nor_, 'all_':all_}
    return cell_categories

def get_cell_indices(exps, datasets):
    """Creates a dictionary with values as exp container ids
        keys are a dictionary containing cell ids paired with cell indices
        INPUT:
            exps: list of experimental containers
            datasets: dataset varialbe attained from function get_dataset()
        OUTPUT:
            Dictionary, cell_indices_by_expcontainer, pairing cell indices with cell ids"""
    cell_indices_by_expcontainer={}
    
    for exp in exps:
    
        # Create dictionary for id to index map for each exp container
        specimen_index_map = {}
    
        # Get cell specimen ids for session B
        specimens_lis=datasets[exp].get_cell_specimen_ids()
    
        #Get cell indices for session B
        specimen_id_temp=datasets[exp].get_cell_specimen_indices(specimens_lis)
    
        # Create map
        specimen_index_map.update({spid: spind for spid, spind in zip(specimens_lis, specimen_id_temp)})
    
        # Update exp container with id to index map
        cell_indices_by_expcontainer[exp]=specimen_index_map
        
    return cell_indices_by_expcontainer