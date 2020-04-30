import socket, pyaudio, wave, time
from queue import Queue
import argparse
import threading

# Based on an example from http://sharewebegin.blogspot.com/2013/06/real-time-voice-chat-example-in-python.html
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

WAVE_OUTPUT_FILENAME = "server_output.wav"
WIDTH = 2


class MusicStream:

	def __init__(self, args):
	
		self.host = args.clients[0]
#		self.port = [int(c) for c in args.port]
#		self.devices = [int(c) for c in args.devices if c is not None]

		self.port = args.port
		self.device = args.devices

		self.channels = args.channels
		self.sample_rate = args.sample_rate
		self.chunk = args.chunk

		self.audio = pyaudio.PyAudio()
		self.done = True

		if args.list:
			self.list_devices()
			return


		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self.conn = None
		self.addr = None

		#TODO also start a listen port for multiple clients

		self.done = False

		self.audq = Queue()
		self.playq = Queue()


		self.rec_stream = None
		self.play_stream = None


		
		#Wait till all the clients are connected
		self.connect_clients()


		#Define and start all threads
		self.rec_thread = threading.Thread(name = 'rec_thread',target=self.read_audio, args=(self.audq,))
		self.rec_thread.start()

		self.send_thread = threading.Thread(target=self.send_audio, args=(self.audq,))
		self.send_thread.start()

		self.recv_thread = threading.Thread(target=self.recv_audio, args=(self.playq,))
		self.recv_thread.start()

		self.play_thread = threading.Thread(name="play_thread", target=self.play_audio, args=(self.playq,))
		self.play_thread.start()

	def list_devices(self):

		p=self.audio
		info = p.get_host_api_info_by_index(0)
		numdevices = info.get('deviceCount')

		for i in range(0, numdevices):
		    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
			        print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
		for i in range(0, numdevices):
		    if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
			        print("Output Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

	#This waits for a new connection
	def connect_clients(self):

		#Prepare UDP server to listen first
		HOST = socket.gethostname()
		PORT = self.port[0]
		self.serversocket.bind((HOST, PORT))
		self.serversocket.listen(1)

		time.sleep(10)
		print("Listening on port", PORT)

		HOST = self.host
		PORT = self.port[1]
		while True:
			try:
				print(HOST, PORT)
				self.socket.connect((HOST, PORT))
				print("Writing to port", PORT)
				break
			except Exception as e:
				print(e)
				print("Waiting for a server:", HOST, PORT)
				time.sleep(5)
				continue


		print("Waiting for a client to connect")
		self.conn, self.addr = self.serversocket.accept()
		print("Client conncted:", self.addr)

	def read_audio(self, audq):

		print("Start recording...")
		self.rec_stream = self.audio.open(format=FORMAT,
						channels=len(self.channels),
						rate=self.sample_rate,
						input=True,
						input_device_index = self.devices[0],
						frames_per_buffer=self.chunk)
		packet = 1
		print("*recording")
		while not self.done:
			data  = self.rec_stream.read(CHUNK)

			if packet ==1000:
				print("*",end="")
			packet=packet+1
			if packet>1000:
				packet=1

			audq.put(data)

	def send_audio(self, audq):
		while True:
			data = audq.get()
			self.socket.sendall(data)


	def recv_audio(self, playq):
		while True:
			data = self.conn.recv(1024)
			playq.put(data)
		

	def play_audio(self, playq):

		self.play_stream = self.audio.open(format=self.audio.get_format_from_width(WIDTH),
						channels=len(self.channels),
						rate=self.sample_rate,
						output=True,
						output_device_index = self.devices[1],
						frames_per_buffer=self.chunk)

		#Play samples as they are received
		while not self.done:
			data = playq.get()
			self.play_stream.write(data)



	def __del__(self):
		if not self.done:
			self.rec_stream.stop_stream()
			self.rec_stream.close()
			self.play_stream.stop_stream()
			self.play_stream.close()
			self.socket.close()
			self.serversocket.close()

		self.audio.terminate()
		print("closed")


if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Program for streaming audio back and forth between two UDP sockets')
	parser.add_argument(
			'--chunk',
			default = 1024,
			help='CHUNK size to use for ')

	parser.add_argument(
			'--channels', nargs='+',
			default = [0],
			help='Which input channel to use')

	parser.add_argument(
			'--sample_rate', type= int,
			default = 44100,
			help='Which input channel to use')

	parser.add_argument(
			'--clients', nargs='+',
			default = ["localhost"],
			help='clients to connect to')

	parser.add_argument(
			'--devices', nargs=2, type =int,
			default = [None, None],
			help='Input and output device ids. Check --list to see all I/O devices')

	parser.add_argument(
			'--port', nargs=2, type =int,
			default =[50007, 50008],
			help='port to use for connections')

	parser.add_argument(
			'--list', action = "store_true",
			help="List audio devices")

	args = parser.parse_args()
	#This object creates bidirectional UDP connections and can stream and play
	stream  = MusicStream(args)
