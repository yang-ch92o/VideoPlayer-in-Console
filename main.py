import sys
import os

etp = "Enter the path of the video: "
if len(sys.argv) <= 0:
	videopath = input(etp).strip('"')
videopath = sys.argv[-1]
while not (
	os.path.exists(videopath)
	and any(
		[
			videopath.endswith(x)
			for x in [
				".mp4",
				".mkv",
				".avi",
				".flv",
				".webm",
				"hevc",
				".mov",
				".wmv",
				".m4v",
			]
		]
		+ ["force-play" in sys.argv]
	)
):
	videopath = input(etp).strip('"')
sys.stdout.write("\x1b[?25lPlease Wait\x1b[8m")
if sys.platform == "win32":
	import ctypes
	hStdin = ctypes.windll.kernel32.GetStdHandle(-10)
	cmode = ctypes.c_ulong()
	_modev=cmode.value
	ctypes.windll.kernel32.GetConsoleMode(hStdin, ctypes.byref(cmode))
	if not 'kqe' in sys.argv:
		cmode.value &= ~0x40
		ctypes.windll.kernel32.SetConsoleMode(hStdin, cmode)
	elif 'qe' in sys.argv:
		ctypes.windll.kernel32.GetConsoleMode(hStdin, ctypes.byref(cmode))
		cmode.value |= 0x40
		ctypes.windll.kernel32.SetConsoleMode(hStdin, cmode)
try:
	import moviepy.editor as mp
except:
	import moviepy as mp
import pygame
import time
import traceback
import _thread
import numpy as np
import sounddevice as sd

scalem = [pygame.transform.smoothscale, pygame.transform.scale]["fast" in sys.argv]
less = "less" in sys.argv
af = os.path.expandvars("%temp%\\" + str(hash("SAFEFFSDS")) + ".wav")

def stop(code=0):
	sys.stdout.write("\x1b[?25h\x1b[0m")
	if hasaudio:_thread.exit()
	mv.close()
	if sys.platform == "win32":
		cmode.value = _modev
		ctypes.windll.kernel32.SetConsoleMode(hStdin, cmode)
	sys.exit(code)

class VAPlayer:
	def __init__(self, clip: mp.VideoFileClip):
		self.clip = clip
		if clip.audio is None:
			return
		fps = clip.audio.fps
		n_channels = clip.audio.nchannels

		def callback(outdata, frames, time, status):
			try:
				current_time = callback.current_time
				end_time = current_time + frames / fps
				try:
					subclip = clip.audio.subclipped(current_time, end_time)
				except:
					subclip = clip.audio.subclip(current_time, end_time)
				audio_chunk = subclip.to_soundarray(fps=fps)
				if audio_chunk.shape[0] < frames:
					padding = np.zeros((frames - audio_chunk.shape[0], n_channels))
					audio_chunk = np.vstack([audio_chunk, padding])
				callback.current_time = end_time
				outdata[:] = audio_chunk[:frames]
				if end_time >= clip.duration:
					raise sd.CallbackStop()
			except Exception as e:
				print(f"Error: {e}")
				raise sd.CallbackStop()
		callback.current_time = 0.0
		self.stream = sd.OutputStream(samplerate=fps, channels=n_channels, callback=callback, dtype="float32")
	def play(self):
		with self.stream:
			sd.sleep(int(self.clip.duration * 1000))
	def play_iter(self):
		with self.stream:
			sd.sleep(int(self.clip.duration * 1000))
			yield None
try:
	mv: mp.VideoFileClip = mp.VideoFileClip(videopath)
	hasaudio = 0

	if mv.audio is not None:
		ap = VAPlayer(mv)
		def playa():
			try:
				ap.play()
			except Exception:
				sys.stdout.write('\a')
				traceback.print_exc()
		_thread.start_new_thread(playa, ())
		hasaudio = 1
	starttime = time.time()
	frames = int(mv.duration * mv.fps)
	it = mv.iter_frames()
	clock = pygame.time.Clock()
	t = 0
	sys.stdout.write("\n" * os.get_terminal_size().lines + "\x1b[?25l")
	title = os.path.basename(videopath)
	if len(title) > 80:
		title = title[:77] + "..."
	for i in it:
		if not (time.time() - starttime) - t * (1 / mv.fps) > 1 / mv.fps:
			frame = pygame.transform.flip(pygame.transform.rotate(pygame.surfarray.make_surface(i), -90), 1, 0)
			f = scalem(frame, (os.get_terminal_size().columns + 1, os.get_terminal_size().lines * 2 - 2))
			p = "\x1b[0;1m\x1b[1;1H\x1b[2K %s | %.2f/%.2f FPS | %i/%i Frames\n" % (
				title,
				clock.get_fps(),
				mv.fps,
				t,
				frames,
			)
			for y in range(0, f.get_height(), 2):
				for x in range(f.get_width()):
					if not less:p += "\x1b[%i;%iH" % (y // 2 + 2, x)
					p += "\x1b[48;2;{};{};{}m".format(*f.get_at((x, y))[:3])
					p += "\x1b[38;2;{};{};{}m▄".format(*f.get_at((x, y + 1))[:3])
				if less:p += "\x1b[0m \x1b[%i;1H" % (y // 2 + 2)
			sys.stdout.write(p + "\x1b[s")
			clock.tick(mv.fps)
		t += 1
	stop()
except Exception:
	sys.stdout.write("\x1b[u\n\x1b[0;31;1m\x1b[0J" + traceback.format_exc() + "\x1b[0m")
	stop(1)
except KeyboardInterrupt:
	print("\n\x1b[0;33;1m\x1b[0JKeyboardInterrupt\x1b[0m")
	stop()