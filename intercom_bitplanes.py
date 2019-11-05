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
        
        #self.packet_format = f"HH{(1024)}H"
        self.packet_format = f"HH{(128)}H"
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0


        def receive_and_buffer():
            message, source_address = self.receiving_sock.recvfrom(Intercom_buffer.MAX_MESSAGE_SIZE)
            #Ahora necesitamos el numero de chunk,el canal y el paquete
            chunk_number, channel, *chunk = struct.unpack(self.packet_format, message)
            #unpacked = np.array(chunk, dtype= np.uint16).view('uint8')
            chunk = np.array(chunk, dtype=np.uint8)
            unpacked = np.unpackbits(chunk)
            #unpacked16 = np.asarray(unpacked, dtype=np.uint16)
            #print(*chunk)
            #Mete dentro del buffer el cuerpo del paquete, pero en un canal determinado
            self._buffer[chunk_number % self.cells_in_buffer][:,channel] = unpacked
            
            return chunk_number
     
        def record_send_and_play(indata, outdata, frames, time, status):
            for i in range(1, 16):
                bitsCanal0 = np.packbits(indata[:,0]>>(16-i) & 1)
                bitsCanal1 = np.packbits(indata[:,1]>>(16-i) & 1)
                #bitsCanal0 = np.array(bitsCanal0, dtype=np.uint8)
                #bitsCanal1 = np.array(bitsCanal0, dtype=np.uint8)
                message = struct.pack(self.packet_format, self.recorded_chunk_number, 0, *bitsCanal0)
                self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
                
                message = struct.pack(self.packet_format, self.recorded_chunk_number, 1, *bitsCanal1)
                self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
                
                print("bit de indata enviado:", 16-i, "\ncanal izquierdo:\n", bitsCanal0, "\ncanal derecho:\n", bitsCanal1)
                print("--------------------------------------------------------")

        #    Se crea bc0(bit canal 0) y bc1(bit canal 1). Van a ser literalmente una matriz de 1024 x 16 rellenado con 0
        #    bc0=[[0]*16]*1024
        #    bc1=[[0]*16]*1024
        #    Se pasa a unsigned int 16 ambas matrices
        #    bc0=np.array(bc0, np.uint16)
        #    bc1=np.array(bc1, np.uint16)
        #    for i in range(-15,1):
        #        i=i*(-1)
        #        #En la columna 15-i(15 - i es para rellenar empezando desde 0 y acabando en 15).Rellenamos si el bit i es 0 o 1.
        #        bc0[:,15-i]=((indata[:,0] >> i) & 1)
        #        #Se envia transformando packbits a 16 bits. En este caso necesitamos 1026 elementos: nº de chunk, canal y los 1024 elementos del paquete.
        #        message = struct.pack(self.packet_format,self.recorded_chunk_number,0,*np.packbits(bc0.reshape(-1, 2, 8)[:, ::-1]).view(np.uint16).flatten())
        #        self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
        #
        #        bc1[:,15-i]=((indata[:,1] >> i) & 1)
        #        message = struct.pack(self.packet_format,self.recorded_chunk_number,1,*np.packbits(bc1.reshape(-1, 2, 8)[:, ::-1]).view(np.uint16).flatten())
        #        self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
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