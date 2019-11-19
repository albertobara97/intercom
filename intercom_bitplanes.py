# Transmitint bitplanes.

import sounddevice as sd
import numpy as np
import struct
from intercom import Intercom
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class Intercom_bitplanes(Intercom_buffer):

    def init(self, args):
        Intercom_buffer.init(self, args)
        self.packet_format = f"!HB{self.frames_per_chunk//8}B"

    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        #Despieza el paquete recibido en varias variables
        chunk_number, bitplane_number, *bitplane = struct.unpack(self.packet_format, message)
        #Crea una variable y le da formato para hacer legible el array recibido
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        #Desempaqueta los bits en el formato inicial de indata
        bitplane = np.unpackbits(bitplane)
        #Transforma el array a in16 para hacer legible el nuevo array
        bitplane = bitplane.astype(np.int16)
        #Almacena en el chunk correspondiente el plano de bits, |= es un operador logico (OR) con el mismo funcionamiento que +=
        #necesario porque el buffer almacena los datos en un array bidimensional, si asignamos sin el operador el array que nos llega
        # del bitplane, sobreescribiriamos los valores de las columnas que no nos interesan tomar del array
        self._buffer[chunk_number % self.cells_in_buffer][:, bitplane_number%self.number_of_channels] |= (bitplane << bitplane_number//self.number_of_channels)
        return chunk_number

    def record_and_send(self, indata):
        for bitplane_number in range(self.number_of_channels*16-1, -1, -1):
            #: devuelve todo el contenido de ese lado del array. >> desplaza los bits recogidos de ese array tantas casillas como avanza la i 
            # en el bucle local. & 1 hace que cuando un bit es negativo, el desplazamiento no arrastre mas 1 creados por la propiedad de desplazar los bits de un numero negativo
            bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
            #Convertimos el array a unsigned int 8
            bitplane = bitplane.astype(np.uint8)
            #Empaquetamos el array
            bitplane = np.packbits(bitplane)
            #Le damos forma al paquete que vamos a enviar con su formato de paquete, numero de chunk y todo el array del bitplane.
            message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, *bitplane)
            #Enviamos el mensaje con su formato
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
        #Cuando se han enviado todos los planos de bits, esta variable aumenta en 1 para hacer un seguimiento del contador de chunks enviados.
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
