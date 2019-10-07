from intercom import Intercom

import sounddevice as sd                                                        # https://python-sounddevice.readthedocs.io
import numpy                                                                    # https://numpy.org/
import argparse                                                                 # https://docs.python.org/3/library/argparse.html
import socket                                                                   # https://docs.python.org/3/library/socket.html
import queue

if __debug__:
    import sys

class Herencia(Intercom):

    def init(self, args):
        Intercom.init(self, args)

    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)

        q = queue.Queue(maxsize=100000)

        def receive_and_buffer():
            message, source_address = receiving_sock.recvfrom(Intercom.max_packet_size)
            #print(message)
            q.put(message)
        
        def record_send_and_play(indata, outdata, frames, time, status):
            sending_sock.sendto(indata, (self.destination_IP_addr, self.destination_port))
            try:
                message = q.get_nowait()
            except queue.Empty:
                message = numpy.zeros((self.samples_per_chunk, self.number_of_channels), self.dtype)
            outdata[:] = numpy.frombuffer(message, numpy.int16).reshape(self.samples_per_chunk, self.number_of_channels)
            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()

        with sd.Stream(samplerate=self.samples_per_second, blocksize=self.samples_per_chunk, dtype=self.dtype, channels=self.number_of_channels, callback=record_send_and_play):
            print('-=- Press <CTRL> + <C> to quit -=-')
            while True:
                receive_and_buffer()


if __name__ == "__main__":
    intercom = Herencia()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
