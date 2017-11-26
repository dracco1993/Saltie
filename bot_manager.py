import bot_input_struct as bi
import binary_converter as compressor
import ctypes
from ctypes import *
from datetime import datetime
import game_data_struct as gd
import importlib
import input_formatter
import mmap
import numpy as np
import rate_limiter
import sys
import os


OUTPUT_SHARED_MEMORY_TAG = 'Local\\RLBotOutput'
INPUT_SHARED_MEMORY_TAG = 'Local\\RLBotInput'
RATE_LIMITED_ACTIONS_PER_SECOND = 60
REFRESH_IN_PROGRESS = 1
REFRESH_NOT_IN_PROGRESS = 0
MAX_CARS = 10


class BotManager:

    def __init__(self, terminateEvent, callbackEvent, name, team, index, modulename, gamename, savedata):
        self.terminateEvent = terminateEvent
        self.callbackEvent = callbackEvent
        self.name = name
        self.team = team
        self.index = index
        self.save_data = savedata
        self.module_name = modulename
        self.game_name = gamename
        self.input_converter = input_formatter.InputFormatter(team, index)


    def run(self):
        # Set up shared memory map (offset makes it so bot only writes to its own input!) and map to buffer
        buff = mmap.mmap(-1, ctypes.sizeof(bi.GameInputPacket), INPUT_SHARED_MEMORY_TAG)
        bot_input = bi.GameInputPacket.from_buffer(buff)
        player_input = bot_input.sPlayerInput[self.index]
        player_input_lock = (ctypes.c_long).from_address(ctypes.addressof(player_input))

        # Set up shared memory for game data
        game_data_shared_memory = mmap.mmap(-1, ctypes.sizeof(gd.GameTickPacketWithLock), OUTPUT_SHARED_MEMORY_TAG)
        bot_output = gd.GameTickPacketWithLock.from_buffer(game_data_shared_memory)
        lock = ctypes.c_long(0)
        game_tick_packet = gd.GameTickPacket() # We want to do a deep copy for game inputs so people don't mess with em

        # Get bot module
        agent_module = importlib.import_module(self.module_name)

        # Create Ratelimiter
        r = rate_limiter.RateLimiter(RATE_LIMITED_ACTIONS_PER_SECOND)

        # Find car with same name and assign index
        for i in range(MAX_CARS):
            if str(bot_output.gamecars[i].wName) == self.name:
                self.index = i
                continue

        # Create bot from module
        agent = agent_module.Agent(self.name, self.team, self.index)

        if self.save_data:
            filename = self.game_name + '\\' + self.name + '.txt'
            print('creating file ' + filename)
            self.game_file = open(filename.replace(" ", ""), 'wb')
        old_time = 0
        current_time = -10

        # Run until main process tells to stop
        while not self.terminateEvent.is_set():
            before = datetime.now()

            # Read from game data shared memory
            game_data_shared_memory.seek(0)  # Move to beginning of shared memory
            ctypes.memmove(ctypes.addressof(lock), game_data_shared_memory.read(ctypes.sizeof(lock)), ctypes.sizeof(lock)) # dll uses InterlockedExchange so this read will return the correct value!

            if lock.value != REFRESH_IN_PROGRESS:
                game_data_shared_memory.seek(4, os.SEEK_CUR) # Move 4 bytes past error code
                ctypes.memmove(ctypes.addressof(game_tick_packet), game_data_shared_memory.read(ctypes.sizeof(gd.GameTickPacket)),ctypes.sizeof(gd.GameTickPacket))  # copy shared memory into struct

            # Call agent
            controller_input = agent.get_output_vector(game_tick_packet)

            # Write all player inputs
            player_input.fThrottle = controller_input[0]
            player_input.fSteer = controller_input[1]
            player_input.fPitch = controller_input[2]
            player_input.fYaw = controller_input[3]
            player_input.fRoll = controller_input[4]
            player_input.bJump = controller_input[5]
            player_input.bBoost = controller_input[6]
            player_input.bHandbrake = controller_input[7]

            current_time = game_tick_packet.gameInfo.TimeSeconds

            if self.save_data and game_tick_packet.gameInfo.bRoundActive and not old_time == current_time and not current_time == -10:
                np_input = self.input_converter.create_input_array(game_tick_packet)
                np_output = np.array(controller_input)
                self.write_array_to_file(np_input)
                self.write_array_to_file(np_output)

            old_time = current_time

            # Ratelimit here
            after = datetime.now()
            #print('Latency of ' + self.name + ': ' + str(after - before))
            #print('Latency of ' + self.name + ': ' + str(after - before))

            r.acquire(after-before)

        # If terminated, send callback
        print("something ended closing file")
        self.callbackEvent.set()


    def write_array_to_file(self, array):
        bytes = compressor.convert_numpy_array(array)
        size_of_bytes = len(bytes.getvalue())
        print(size_of_bytes)
        self.game_file.write(bytes.getvalue())
