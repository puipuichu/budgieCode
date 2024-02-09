######################
# Prepare workspace #
######################

# Import libraries
import time          # Time for time-related functions
import sys           # Sys for system-specific parameters and functions
import serial        # Serial for serial communication
import threading     # Threading for multi-threading support
import csv           # CSV for reading and writing CSV files
import random        # Random for generating random numbers
import os            # OS for operating system-related functions
from pygame import mixer  # Mixer from pygame for audio playback

# Import custom configuration module
import config_budgieCode as c

##########
# Config #
##########

# Set program folder path
folderPath = c.folderPath

# Set folder path to save data
logFolder = c.logFolder

# Set arduino port
arduinoPort = c.arduinoPort

# Set folder path to stimulus
song_folderPath = c.song_folderPath

# Set folder path to stimulus A and stimulus B
stimA_folderPath = c.stimA_folderPath
stimB_folderPath = c.stimB_folderPath

# Set name of stimulus A and stimulus B
stimA = c.stimA
stimB = c.stimB

# Set number of stimulus in each folder
stim_no = c.stim_no

# Set stimulus trigger threshold: after bird on perch for ... seconds
threshold_time = c.threshold_time

#############
# Functions #
#############

# Create conversion key based on user input: from arudino input (0, 1, 2 or 3) to actual state (free, silent, stimA, stimB)
def create_conversion_key(setting):
    silent_position = setting.find('S')
    stimA_position = setting.find('A')

    conversion_key = {
        "0": "free",
        "1": 'silent' if silent_position == 0 else (stimA if stimA_position == 0 else stimB),
        "2": 'silent' if silent_position == 1 else (stimA if stimA_position == 1 else stimB),
        "3": 'silent' if silent_position == 2 else (stimA if stimA_position == 2 else stimB),
    }

    return conversion_key

# Function to play sounds for a given stimulus
def play_stimulus_loop(stim_files, stim_folder_path, played_songs, stim_song_count):
    global song_exitFlag, songList

    for song in stim_files:
        if song_exitFlag:
            if mixer.music.get_busy():
                mixer.music.fadeout(50)
            break

        if song not in played_songs:
            print(song)
            mixer.music.load(os.path.join(stim_folder_path, song))
            mixer.music.play()
            songList.append(song.strip())
            stim_song_count += 1
            played_songs.add(song)

            while mixer.music.get_busy():
                time.sleep(0.1)

    if stim_song_count == stim_no:
        random.shuffle(stim_files)
        stim_song_count = 0
        played_songs.clear()

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

####################
# Create log file #
####################

# Prompt user for input and check if input is in correct format
while True:
    
    # Prompt user for input to create a log file name
    print("Please enter Log Command (e.g. Woody_02_SAB): ")

    # Read user input from standard input and remove newline character
    user_input = (sys.stdin.readline()).rstrip()

    # Split input command using underscore as delimiter
    parsed_input = user_input.split('_')

    # Check if input has expected format (at least three parts separated by underscores)
    if len(parsed_input) < 3:
        print("Wrong Input Format! Input format: Bird_trialNo_stimulus")
    else:
        # Extract experimental setting (e.g., SAB) and create conversion key from Arduino input (0, 1, 2, or 3) to actual state (free, silent, stimA, stimB)
        setting = parsed_input[2]
        try:
            conversion_key = create_conversion_key(setting)

            # Check if the setting string is valid (contains 'S', 'A', and 'B')
            if set('SAB') != set(setting):
                print("Invalid setting. Please include 'S', 'A', and 'B'.")
            else:
                # Input successfully processed, break out of the loop
                print("Input successfully processed.")
                break
        except Exception as e:
            print(f"Error processing input: {e}")

# Create log file name 
logFile = logFolder + user_input + ".txt"

##################
# Program set up #
##################

# Set up serial read from arduino
baud = 9600  # Arduino Uno runs at 9600 baud
ser = serial.Serial(arduinoPort, baud)  
ser.reset_input_buffer() # Clear buffer before starting
print("Connected to Arduino port: " + arduinoPort) # Print message to screen

# Set up initial values 
data_exitFlag = False # Exit flags
song_exitFlag = True   
data = None # Variables for read_data loop       
stimulus = None        
previous_stimulus = None  
landTime = None        
endTime = None         
songList = []          
stimA_playedSongs = set() # Variables for play_stimulus loop
stimB_playedSongs = set()  
stimA_songCount = 0   
stimB_songCount = 0    

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

# Function to play stimuli A and B
def play_stimulus():
    global data_exitFlag, stimulus

    while not data_exitFlag:

        if stimulus == stimA:
            play_stimulus_loop(stimA_files, stimA_folderPath, stimA_playedSongs, stimA_songCount)

        elif stimulus == stimB:
            play_stimulus_loop(stimB_files, stimB_folderPath, stimB_playedSongs, stimB_songCount)

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
with open(logFile, "a", encoding = "UTF8", newline = "") as f:
    writer = csv.writer(f)
    writer.writerow([get_date(), get_time()])
    writer.writerow(["Stimulus", "Start_time", "End_time", "Songs"])

    # Read input from arduino
    try:
        ser.timeout = 0.25

        while not data_exitFlag:

                # Print input from arduino: silent, stimulus A or stimulus B
                if data:
                        stimulus = conversion_key.get(data, "unknown")

                        # If input stimulus is same as previous one: bird still at same place
                        if stimulus == previous_stimulus:
                                currentTime = time.time() # Get current time
                                
                                # If bird on stimulus perch longer than threhold: play song
                                if stimulus in [stimA, stimB] and (currentTime - landTime) > threshold_time:
                                    song_exitFlag = False # Update flag to allow song play

                        # If input stimulus is different from previous one: bird moved
                        else:
                            print(stimulus) # Print current state
                            song_exitFlag = True # Stop song play: if previous stimulus is playing
                            if mixer.music.get_busy():
                                mixer.music.fadeout(50)

                            # If bird just landed on stimuls perch: get landing time
                            if stimulus in [stimA, stimB]:
                                landTime = time.time() # Get current time

                            # If this is not the first stimulus, update the endTime
                            if previous_stimulus is not None:
                                endTime = get_time()  # Get stimulus end time as a string
                                writer.writerow([previous_stimulus, startTime, endTime, songList])
                                songList = [] # Empty the songList after logging   

                            # Update startTime for the new stimulus
                            startTime = get_time()

                        # Update the previous_stimulus
                        previous_stimulus = stimulus

    except KeyboardInterrupt:

        # Update data and song exit flag
        data_exitFlag = True
        song_exitFlag = True

        # Write last row of data
        if previous_stimulus is not None:
            endTime = get_time()  # Get stimulus end time as a string
            writer.writerow([previous_stimulus, startTime, endTime, songList])
            time.sleep(0.1)
        
        # If song is playing: stop
        if mixer.music.get_busy():
            mixer.music.fadeout(50)
            time.sleep(0.1)
        
        # Print interruption message on screen
        interruption_time = get_date() + ' - ' + get_time() + '\n'
        print("\nData collection interrupted by user at:", interruption_time)

        # Close threads and serial connection
        data_thread.join()
        song_thread.join()
        ser.close()  
        time.sleep(0.1)

mixer.quit()
sys.exit()
