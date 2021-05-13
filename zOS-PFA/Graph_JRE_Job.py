#####################################################################
#
#                     Predictive Failure Analysis (PFA)
#                     Graph JES2 Resource Data for Jobs
#
#This python script is for use with data that is collected, created,
#and written by the PFA_JES2_RESOURCE_EXHAUSTION check only. Its
#use with data from any other source will result in errors.
#
#Copyright 2021 IBM Corp.                                          
#                                                                   
#Licensed under the Apache License, Version 2.0 (the "License");   
#you may not use this file except in compliance with the License.  
#You may obtain a copy of the License at                           
#                                                                   
#http://www.apache.org/licenses/LICENSE-2.0                        
#                                                                   
#Unless required by applicable law or agreed to in writing,        
#software distributed under the License is distributed on an       
#"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,      
#either express or implied. See the License for the specific       
#language governing permissions and limitations under the License. 
#####################################################################

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import platform
import os

#Make sure we have plenty of potential data points to plot.
plt.rcParams['agg.path.chunksize']=10000
#Disable false positive warning
pd.options.mode.chained_assignment = None  # default='warn'
#Which system are we running on?
system = platform.system()

keys = {"JQE":"Q","SPOOL":"S","BERT":"B","JOE":"J"}
user_keys = ["JQE","SPOOL","BERT","JOE"]
asid_header_data = ["Key","JobName","TaskId","Start_Time","STCK_Time","Current_Usage","Date_Time"]
capacity_header_data = ["Resource","Capacity"]
data_types_dict={'Key':str,'JobName':str,'TaskId':str,'Start_Time':str,'STCK_Time':int,'Current_Usage':int,'Date_Time':str}
capacity_types_dict={"Resource":str,"Capacity":int}
check_name = "PFA_JES2_Resource_Exhaustion"
COLUMN_CHAR_LEN = 8

#Parse our command line arguments.
if(len(sys.argv) == 5):
    data_filepath = sys.argv[1]
    capacity_filepath = sys.argv[2]
    jobName = sys.argv[3]
    jobName = jobName.upper()
    key = sys.argv[4]
    key = key.upper()
    verbose = False
elif(len(sys.argv) == 6 and (sys.argv[5] == '-v' or sys.argv[5] == '-verbose')):
    data_filepath = sys.argv[1]
    capacity_filepath = sys.argv[2]    
    jobName = sys.argv[3]
    jobName = jobName.upper()
    key = sys.argv[4]
    key = key.upper()
    verbose = True
elif(len(sys.argv) == 2 and (sys.argv[1] == '-h' or sys.argv[1] == '-help')):
    print("The proper syntax for this script is the following:\n")
    print("'python Graph_JRE_Job.py data_file capacity_file job_name jes2_resource'.\n")
    print("Valid JES2 Resources are: " + str([key for key in user_keys]) + "\n")
    print("The file path value is case sensitive, but the JES2 resource and job_name values are not.\n")
    print("For example, if this script and the required files are in the same directory, and you want to graph the JES2 Spool data for Job3, you would type the following:\n")
    print("'python Graph_JRE_Job.py SY1.5day.All.data Capacity.data Job3 SPOOL'\n")
    print("You can also add -v to the end of the command for verbose mode. This option will print additional data ")
    print("that could help debug errors or verify the results. An example using verbose mode looks like the following:\n")
    print("'python Graph_JRE_Job.py SY1.5day.All.data Capacity.data Job3 BERT -v'\n")
    print("When this script is executed on z/OS, it saves the graph in a .pdf file that can be downloaded from the directory where this script was executed and displayed anywhere that supports displaying a .pdf file.")
    print("The file name is in the format of jobName_JESResource_graph.pdf.")
    print("For example, if you entered 'python Graph_JRE_Job.py SY1.5day.All.data Capacity.data Job3 SPOOL' on z/OS the saved file would be:")
    print("JOB3_SPOOL_graph.pdf and it would be located in the current working directory.")
    sys.exit()
else:
    raise Exception("The supplied arguments are not correct. Specify the data_file_path, capacity_filepath, job_name, and JES2 resource in that order. For help enter 'python Graph_JRE_Job.py -h'")

#Make sure we have proper input from the user.
if(not os.path.exists(data_filepath)):
    raise Exception("The specified file or filepath for the data file does not exist. Verify the file and filepath then try again.")

if(not os.path.exists(capacity_filepath)):
    raise Exception("The specified file or filepath for the capacity file does not exist. Verify the file and filepath then try again.")

if key not in user_keys:
    raise Exception("The specified resource does not exist. Specify a resource that exists.")

#Load up our data and assign correct header values so we can narrow it down to the pieces we want.
data_file = pd.read_csv(data_filepath,
                    sep="/|,",
                    names=asid_header_data,
                    header=None,
                    engine="python",
                    converters=data_types_dict)

capacity_file = pd.read_csv(capacity_filepath,
                    sep="/|,",
                    names=capacity_header_data,
                    header=None,
                    engine="python",
                    converters=capacity_types_dict)

#We need to make sure our jobName is left justified and the proper length.
#Otherwise we will not be able to find the correct data to graph.
if(len(jobName) < COLUMN_CHAR_LEN):
    jobName = jobName.ljust(COLUMN_CHAR_LEN)

#Make sure we have proper input from the user.    
if jobName not in data_file.values:
    raise Exception("The specified job name does not exist. Verify the job name and try again.")

user_key = key
key = keys[user_key]
user_key = user_key.ljust(COLUMN_CHAR_LEN)
data_file['Capacity'] = np.nan
NUM_TO_PRINT = 10
PDF_FILENAME = jobName.strip()+'_'+user_key.strip()+"_graph.pdf" #This is the name of the .pdf file that gets saved when this script is ran on z/OS

def process_data(data_file, capacity_file):
    the_capacity = capacity_file.loc[capacity_file['Resource'] == user_key,'Capacity'].values[0]
    the_data = data_file.loc[(data_file['Key'] == key) & (data_file['JobName'] == jobName)]
    the_data['Capacity'].fillna(the_capacity, inplace=True)
    the_data['Capacity'] = the_data['Capacity'].astype(int)
    the_data.loc[:,('Date_Time')] = pd.to_datetime(the_data['Date_Time'].astype(str), format='%Y%m%d%H%M%S')
    the_data = get_latest_time(the_data)
    if(verbose):
        print_details(the_data,NUM_TO_PRINT)
    return the_data

def graph_data(the_data):
    y_values = [0,(the_data['Capacity'].max())*.25,(the_data['Capacity'].max())*.50,(the_data['Capacity'].max())*.75,(the_data['Capacity'].max())]
    y_ticks = [str(int(y)) + user_key for y in y_values]
    fig, ax = plt.subplots()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax.plot(the_data['Date_Time'],the_data['Capacity'],'--r', label='Capacity')
    ax.plot(the_data['Date_Time'],the_data['Current_Usage']/1024,'-b', label='Current Usage')
    plt.xlabel('Month-Day Time')
    fig.suptitle(check_name + "\n" + jobName + '/' + user_key, fontsize=16)
    fig.autofmt_xdate()
    plt.yticks(y_values, y_ticks)
    ax.set_ylim(0,the_data['Capacity'].max()*1.10)
    ax.legend(bbox_to_anchor=(1.41, 1),loc="upper right")
    fig.subplots_adjust(right=0.75)
    if system != 'z/OS':
        plt.show();
    else:
        fig.savefig(PDF_FILENAME)

def print_details(data_frame,num_to_print):
    print("Now graphing " + check_name + " data on a " + system + " system.")
    print("The job_name is: " + jobName)
    print("The JES2 resource is: " + user_key)
    print("The data_filepath entered: " + data_filepath)
    print("The capacity_filepath entered was: " + capacity_filepath)
    print("\nPreview of the data being graphed:")
    print(data_frame.head(num_to_print).to_string(index=False))
 
def get_latest_time(our_data):
    #Need to verify that we are using the latest start time if multiple exist for the same ASID.
    list_data = our_data['Start_Time'].to_dict()
    #Here we make sure we get the latest start time.
    times_dict = {}
    for i in list_data:
        if list_data[i] in times_dict:
            times_dict[list_data[i]] += 1
        else:
            times_dict[list_data[i]] = 1
    if(len(times_dict) > 1):
        latest_time = max(times_dict.keys())
        our_data = our_data.loc[(our_data['Start_Time'] == latest_time)]
    return our_data

#Process and graph our data.
the_data = process_data(data_file, capacity_file)
jobName = jobName.strip()
user_key = user_key.strip()
graph_data(the_data)
    
if system == 'z/OS':
    print(PDF_FILENAME + ' has been created and is ready to be downloaded and viewed.')
