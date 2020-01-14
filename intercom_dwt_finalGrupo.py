# Using the Discrete Wavelet Transform, convert the chunks of samples
# intro chunks of Wavelet coefficients (coeffs).
#
# The coefficients require more bitplanes than the original samples,
# but most of the energy of the samples of the original chunk tends to
# be into a small number of coefficients that are localized, usually
# in the low-frequency subbands:
#
# (supposing a chunk with 1024 samples)
#
# Amplitude
#     |       +                      *
#     |   *     *                  *
#     | *        *                *
#     |*          *             *
#     |             *       *
#     |                 *
#     +------------------------------- Time
#     0                  ^        1023 
#                |       |       
#               DWT  Inverse DWT 
#                |       |
#                v
# Amplitude
#     |*
#     |
#     | *
#     |  **
#     |    ****
#     |        *******
#     |               *****************
#     +++-+---+------+----------------+ Frequency
#     0                            1023
#     ^^ ^  ^     ^           ^
#     || |  |     |           |
#     || |  |     |           +--- Subband H1 (16N coeffs)
#     || |  |     +--------------- Subband H2 (8N coeffs)
#     || |  +--------------------- Subband H3 (4N coeffs)
#     || +------------------------ Subband H4 (2N coeffs)
#     |+-------------------------- Subband H5 (N coeffs)
#     +--------------------------- Subband L5 (N coeffs)
#
# (each channel must be transformed independently)
#
# This means that the most-significant bitplanes, for most chunks
# (this depends on the content of the chunk), should have only bits
# different of 0 in the coeffs that belongs to the low-frequency
# subbands. This will be exploited in a future issue.
#
# The straighforward implementation of this issue is to transform each
# chun without considering the samples of adjacent
# chunks. Unfortunately this produces an error in the computation of
# the coeffs that are at the beginning and the end of each subband. To
# compute these coeffs correctly, the samples of the adjacent chunks
# i-1 and i+1 should be used when the chunk i is transformed:
#
#   chunk i-1     chunk i     chunk i+1
# +------------+------------+------------+
# |          OO|OOOOOOOOOOOO|OO          |
# +------------+------------+------------+
#
# O = sample
#
# (In this example, only 2 samples are required from adajact chunks)
#
# The number of ajacent samples depends on the Wavelet
# transform. However, considering that usually a chunk has a number of
# samples larger than the number of coefficients of the Wavelet
# filters, we don't need to be aware of this detail if we work with
# chunks.

import struct
import numpy as np
import pywt
import pywt.data
from intercom import Intercom
from intercom_empty import Intercom_empty

if __debug__:
    import sys

class Intercom_DWT(Intercom_empty):

    def init(self, args):
        Intercom_empty.init(self, args)
        self.packet_format = f"!HB{self.frames_per_chunk//8}BHH"
        self.zeros = 0

    def send(self, indata):
        signs = indata & 0x8000
        magnitudes = abs(indata)
        indata = signs | magnitudes
        
        self.NOBPTS = int(0.75*self.NOBPTS + 0.25*self.NORB)
        self.NOBPTS += self.zeros
        self.zeros = 0
        self.NOBPTS += 1
        
        if self.NOBPTS > self.max_NOBPTS:
            self.NOBPTS = self.max_NOBPTS

        self.flat = indata[:,0].flatten()
        self.coeffs_c0 = pywt.wavedec(self.flat, "db5", mode='per')
        self.flat = indata[:,1].flatten()
        self.coeffs_c1 = pywt.wavedec(self.flat, "db5", mode='per')
        #self.coeffs = np.array(self.coeffs)
        self.coeffs_c0,_ = pywt.coeffs_to_array(self.coeffs_c0)
        self.coeffs_c1,_ = pywt.coeffs_to_array(self.coeffs_c1)
        print("array: ", self.coeffs_c0)
        print("array: ", self.coeffs_c1)
        print("shape: ", self.coeffs_c1.shape)
        print("shape: ", self.coeffs_c1.shape)
        print("shape indata: ", indata.shape)

        self.coeffs_c0 = np.array(self.coeffs_c0,dtype=np.uint32)
        self.coeffs_c1 = np.array(self.coeffs_c1,dtype=np.uint32)

        #self.send_bitplane(self.coeffs)
        #self.send_bitplane(self.coeffs, self.max_NOBPTS-2)

        last_BPTS = self.max_NOBPTS - self.NOBPTS - 1
        self.send_bitplane(self.coeffs_c0, self.max_NOBPTS-1, 0)
        self.send_bitplane(self.coeffs_c0, self.max_NOBPTS-2, 0)

        self.send_bitplane(self.coeffs_c1, self.max_NOBPTS-1, 1)
        self.send_bitplane(self.coeffs_c1, self.max_NOBPTS-2, 1)

        for bitplane_number in range(self.max_NOBPTS-3, last_BPTS, -1):
            self.send_bitplane(self.coeffs_c0, bitplane_number, 0)
            self.send_bitplane(self.coeffs_c1, bitplane_number, 1)

        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER


    def send_bitplane(self, indata, bitplane_number, channel):
        bitplane = (indata[:,] >> bitplane_number//self.number_of_channels) & 1
        if np.any(bitplane): 
            bitplane = bitplane.astype(np.uint8)
            bitplane = np.packbits(bitplane)
            message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, self.received_bitplanes_per_chunk[(self.played_chunk_number+1) % self.cells_in_buffer]+1, *bitplane, channel)
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
        else:
            self.skipped_bitplanes[self.recorded_chunk_number % self.cells_in_buffer] += 1

    
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        received_chunk_number, received_bitplane_number, *bitplane, channel = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        #Desempaqueta los bits en el formato inicial de indata
        bitplane = np.unpackbits(bitplane)
        #Transforma el array a in16 para hacer legible el nuevo array
        bitplane = bitplane.astype(np.int16)

        self._buffer[received_chunk_number % self.cells_in_buffer][:, channel] |= (bitplane << received_bitplane_number//self.number_of_channels)
        return received_chunk_number

if __name__ == "__main__":
    intercom = Intercom_DWT()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
