# Adding a buffer.

import sounddevice as sd
import numpy as np
import struct
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class Intercom_bitplanes(Intercom_buffer):

    def init(self, args):
        Intercom_buffer.init(self, args)
##########################
    def run(self):

        self.packet_format = f"HH{(1024)}h"
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0

        def receive_and_buffer():
            message, source_address = self.receiving_sock.recvfrom(Intercom_buffer.MAX_MESSAGE_SIZE)
            chunk_number,channel, *chunk = struct.unpack(self.packet_format, message)
            
            self._buffer[chunk_number % self.cells_in_buffer][:,channel]=chunk
         
            return chunk_number
      ##Metodo para extraer el plano de bit
        def transformar(bit, array):
            for i in range(0,len(array)):
                negativo=0
                if array[i]< 0:
                    array[i]=array[i]*-1
                    negativo=1

                if negativo == 1:
                    array[i]=((((array[i] >> bit) & 1)*(2**bit))*-1)
                else:
                    array[i]=((((array[i] >> bit) & 1)*(2**bit)))
            return array
      ########################
        def record_send_and_play(indata, outdata, frames, time, status):
            #Se hace una conversión de indata a array de numpy de 16
            conversion= np.array(indata,np.int16)
            #Se envia el paquete desde el bit 15 hasta el 1
            print("indata\n",indata,"\n fin indata")
            for i in range(-16,0):
                i=i*(-1)-1
              
                print("i= ",i,"    ",(((conversion >> i) & 1)*(2**(i)))[:,0])
                message = struct.pack(self.packet_format,self.recorded_chunk_number,0, *(((conversion >> i) & 1)*(2**(i)))[:,0].flatten())
                self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
                message = struct.pack(self.packet_format,self.recorded_chunk_number,1,*(((conversion >> i) & 1)*(2**(i)))[:,1].flatten())
                self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
            self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
            chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
            self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
            self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
            outdata[:] = chunk
            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()

        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            first_received_chunk_number = receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                receive_and_buffer()
##########################




if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()