######################
# Prepare workspace #
######################

# Import libraries
import time          # Time for time-related functions
import sys           # Sys for system-specific parameters and functions
import serial        # Serial for serial communication
import threading
import csv
import winsound
import random
import os
from pygame import mixer

# Import custom configuration module
import config as c
# Import playTime_threshold constant from the configuration module
#from config import playTime_threshold

##########
# Config #
##########

# Set program folder path
folderPath = "C:/Users/pchu/Documents/preferenceApparatus/Distortion_Clean/"

# Set folder path to save data
logFolder = folderPath + "LOGS/"

# Set arduino port
arduinoPort = "COM4"  

# Set folder path to stimulus
song_folderPath = folderPath + "stimulus/"

# Set folder path to stimulus A and stimulus B
stimA_folderPath = song_folderPath + "ran/"
stimB_folderPath = song_folderPath + "reg/"

# Set name of stimulus A and stimulus B
stimA = "ran"
stimB = "reg"

# Set number of stimulus in each folder
stim_no = 5

# Set stimulus trigger threshold: after bird on perch for ... seconds
threshold_time = 0.3

#############
# Functions #
#############

# Convert input from arduino (IR beam broken for perch: 1, 2 or 3) to actual stimulus (Silent, stimA or stimB)
def convert_to_stimulus(data):

    # Map the input data to the corresponding stimulus based on positions
    if data == "0": # IR beam not broken
         return "free"
    elif data == "1":
        return 'silent' if silent_position == 0 else (stimA if stimA_position == 0 else stimB)
    elif data == "2":
        return 'silent' if silent_position == 1 else (stimA if stimA_position == 1 else stimB)
    elif data == "3":
        return 'silent' if silent_position == 2 else (stimA if stimA_position == 2 else stimB)
    
# Get time accurate to ms
def get_time():
    t = time.gmtime()
    ms = int((time.time() % 1) * 1000)  # Extract milliseconds
    s = time.strftime('%H:%M:%S', t) + f'.{ms:03d}'
    return s

# Get date
def get_date():
	t = time.gmtime()
	s = str(t.tm_year) + '/' + str(t.tm_mon) + '/' + str(t.tm_mday)
	return s

# Play stimulus 
def play_mixer(file_path):
    mixer.music.load(file_path)
    mixer.music.play()

####################
# Create log file #
####################

# # Prompt user for input to create a log file name
# print('Please enter Log Command (e.g. Woody_02_SAB): ')

# # Read user input from standard input and remove newline character
# input = (sys.stdin.readline()).rstrip()

input = "Woody_02_ASB"

# Split input command using underscore as delimiter
parsed = input.split('_')

# Check if input has expected format (at least three parts separated by underscores)
if len(parsed) < 3:
    print('Wrong Input Format! Input format: Bird_trialNo_stimulus')
    exit()

# Extract experimental setting (e.g. SAB)
setting = parsed[2] 

# Check if the setting string is valid (contains 'S', 'A', and 'B')
if set('SAB') != set(setting):
    raise ValueError("Invalid setting. Please include 'S', 'A', and 'B'.")

# Create log file name using logFolder from configuration module and user input
logFile = logFolder + input 

##################
# Program set up #
##################

# Determine the positions of 'S', 'A', and 'B' in the setting
silent_position = setting.find('S')
stimA_position = setting.find('A')
stimB_position = setting.find('B')

# Set up serial read from arduino
baud = 9600  # Arduino Uno runs at 9600 baud
ser = serial.Serial(arduinoPort, baud)  
ser.reset_input_buffer() # Clear buffer before starting
print("Connected to Arduino port: " + arduinoPort) # Print message to screen

# Set up initial values 
data_exitFlag = False # Flag to control the data reading loop
song_exitFlag = False 
data = None 
stimulus = None
previous_stimulus = None
endTime = None
songList = [] # Initialize an empty list for songs
songCount = 0

# Get list of song files from folder 
stimA_files = os.listdir(stimA_folderPath)
stimB_files = os.listdir(stimB_folderPath)

# Shuffle the songs to start playing
random.shuffle(stimA_files) 
random.shuffle(stimB_files) 

# Initialize mixer to play songs
mixer.init()

###############################
# Define and activate threads #
###############################

# Function to read serial data from arduino
def read_data(): 
    global data
    while not data_exitFlag:
        data = ser.readline().decode('utf-8').strip()
        time.sleep(0.1)

# Function to play sounds
def play_stimulus():
    
    # Global variables used within the function
    global data_exitFlag, song_exitFlag, stimulus, songCount

    while not data_exitFlag:

                    # logic: make this thing work only with stimA first, then add condition for stimB!!!!!
                    # !!!!!also need to add threshold_time!!
                    # need to figure out how to break song when it is playing!!! another ser/ thread???

        # While bird is on stimulus perch
        while stimulus == stimA:

            # Iterating through each sound in stimA_files
            for song in stimA_files:

                # Stop playing sounds when sound_exit_flag is True
                if song_exitFlag:
                    break

                # Play stimulus
                print(song) # Print song played on screen
                mixer.music.load(os.path.join(stimA_folderPath, song)) # Set song path
                mixer.music.play() # Play song
                songList.append(song.strip()) # Append song to songs_list
                songCount += 1 # Update how many sounds have been played

                # Shuffling sounds if all sounds have been played and sound_exit_flag is False
                if songCount == stim_no:
                    random.shuffle(stimA_files)
                    songCount = 0  # Reset counter

# Read data from arduino thread
data_thread = threading.Thread(target = read_data)
data_thread.daemon = True
data_thread.start()

# Play sound thread
song_thread = threading.Thread(target = play_stimulus)  
song_thread.daemon = True 
song_thread.start()

#############
# Main loop #
#############

# Open a log file for writing
with open(logFile, 'a', encoding='UTF8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([get_date(), get_time()])
    writer.writerow(["Stimulus", "Start_time", "End_time", "Songs"])

    # Read input from arduino
    try:
            ser.timeout = 0.25

            while not data_exitFlag:

                    # Print input from arduino: silent, stimulus A or stimulus B
                    if data:
                            stimulus = convert_to_stimulus(data)

                            # If input stimulus is different from the previous one
                            if stimulus != previous_stimulus:
                                print(stimulus)

                                # Update sound_exitFlag according to arduino input
                                if stimulus == stimA or stimulus == stimB:
                                    song_exitFlag = False # Play sound when bird is on stimulus perch
                                else:
                                    song_exitFlag = True # Stop sound play elsewise 

                                # If this is not the first stimulus, update the endTime
                                if previous_stimulus is not None:
                                    endTime = get_time()  # Get stimulus end time
                                    writer.writerow([previous_stimulus, startTime, endTime, songList])
                                    songList = [] # Empty the songList after logging   

                                # Update startTime for the new stimulus
                                startTime = get_time()

                            # Update the previous_stimulus
                            previous_stimulus = stimulus

    except KeyboardInterrupt:
        data_exitFlag = True
        song_exitFlag = True
        interruption_time = get_date() + ' - ' + get_time() + '\n'
        print("\nData collection interrupted by user at:", interruption_time)

    # Close threads and serial connection
    data_thread.join()
    song_thread.join()
    ser.close()  
    mixer.quit()
    sys.exit()