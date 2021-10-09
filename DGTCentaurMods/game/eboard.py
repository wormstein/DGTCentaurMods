# Emulate the DGT e-board protocol
#
# Ed Nekebno
#
# Pair first
# Connect after the chessboard displays
#
# TODO
# Currently autopromotes pawn to queens - allow choice (as we cannot actually detect what piece is put down!)
# Check all possible commands are catered for
# Make it so bus address is unique and is checked before responding to messages ?
# Regular serial (in addition to bluetooth) ?
# Handle DGT_BUS_REPEAT_CHANGES bus message 0x04
# RabbitPlugin disconnects when new start state detected

import serial
import time
import sys
from os.path import exists
from DGTCentaurMods.board import boardfunctions
import threading

# https://github.com/well69/picochess-1/blob/master/test/dgtbrd-ruud.h
DGT_SEND_RESET = 0x40 # Puts the board into IDLE mode, cancelling any UPDATE mode
DGT_TO_BUSMODE = 0x4a
DGT_STARTBOOTLOADER = 0x4e
DGT_TRADEMARK = 0x12
DGT_RETURN_SERIALNR = 0x45
DGT_SERIALNR = 0x11
DGT_RETURN_LONG_SERIALNR = 0x55
DGT_LONG_SERIALNR = 0x22
DGT_SEND_CLK = 0x41
DGT_BWTIME = 0x0d

MESSAGE_BIT = 0x80

DGT_BUSADRES = 0x10
DGT_TO_BUSMODE = 0x4a
DGT_SEND_VERSION = 0x4d
DGT_VERSION = 0x13
DGT_SEND_BRD = 0x42
DGT_BOARD_DUMP = 0x06
DGT_SEND_UPDATE = 0x43
DGT_SEND_UPDATE_BRD = 0x44
DGT_FIELD_UPDATE = 0x0e
DGT_SEND_UPDATE_NICE = 0x4b
DGT_SET_LEDS = 0x60
DGT_CLOCK_MESSAGE = 0x2b

DGT_SEND_BATTERY_STATUS = 0x4c
DGT_BATTERY_STATUS = 0x20

DGT_BUS_PING = 0x87
DGT_MSG_BUS_PING = 0x07
DGT_BUS_IGNORE_NEXT_BUS_PING = 0x8a
ignore_next_bus_ping = 0
DGT_BUS_SEND_VERSION = 0x8b
DGT_MSG_BUS_VERSION = 0x09
DGT_BUS_SEND_FROM_START = 0x86
DGT_MSG_BUS_FROM_START = 0x06
DGT_BUS_SEND_CHANGES = 0x83
DGT_MSG_BUS_UPDATE = 0x05
DGT_BUS_SEND_CLK = 0x81
DGT_BUS_SET_START_GAME = 0x85
DGT_MSG_BUS_START_GAME_WRITTEN = 0x08

DGT_RETURN_BUSADRES = 0x46
DGT_SEND_TRADEMARK = 0x47

DGT_UNKNOWN_1 = 0xDF
DGT_UNKNOWN_2 = 0x92

EE_POWERUP = 0x6a
EE_EOF = 0x6b
EE_FOURROWS = 0x6c
EE_EMPTYBOARD = 0x6d
EE_DOWNLOADED = 0x6e
EE_BEGINPOS = 0x6f
EE_BEGINPOS_ROT = 0x7a
EE_START_TAG = 0x7b
EE_WATCHDOG_ACTION = 0x7c
EE_FUTURE_1 = 0x7d
EE_FUTURE_2 = 0x7e
EE_NOP = 0x7f
EE_NOP2 = 0x00
EEPROM = []

EMPTY = 0x00
WPAWN = 0x01
WROOK = 0x02
WKNIGHT = 0x03
WBISHOP = 0x04
WKING = 0x05
WQUEEN = 0x06
BPAWN = 0x07
BROOK = 0x08
BKNIGHT = 0x09
BBISHOP = 0x0a
BKING = 0x0b
BQUEEN = 0x0c
PIECE1 = 0x0d  # Magic piece: Draw
PIECE2 = 0x0e  # Magic piece: White win
PIECE3 = 0x0f  # Magic piece: Black win
board = bytearray([EMPTY] * 64)
litsquares = []
startstate = bytearray(b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01')

boardfunctions.initScreen()

if bytearray(boardfunctions.getBoardState()) != startstate:
	boardfunctions.writeText(0,'Place pieces')
	boardfunctions.writeText(1,'in startpos')
	# As the centaur can light up squares - let's use the
	# squares to help people out
	while bytearray(boardfunctions.getBoardState()) != startstate:
		rstate = boardfunctions.getBoardState()
		tosend = bytearray(b'\xb0\x00\x0c\x06\x50\x05\x12\x00\x05')
		# '\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x37\x36\x35\x34\x33\x32\x31\x30\x0d')
		for x in range(0, 64):
			if x < 16 or x > 47:
				if rstate[x] != 1:
					tosend.append(x)
			if x > 15 and x < 48:
				if rstate[x] == 1:
					tosend.append(x)
		tosend[2] = len(tosend) + 1
		tosend.append(boardfunctions.checksum(tosend))
		boardfunctions.ser.write(tosend)
		time.sleep(0.5)
	boardfunctions.ledsOff()

# As we can only detect piece presence on the centaur and not pieces, we must have a known start state
print("Setup board")
while bytearray(boardfunctions.getBoardState()) != startstate:
	time.sleep(0.5)
board[7] = WROOK
board[6] = WKNIGHT
board[5] = WBISHOP
board[4] = WQUEEN
board[3] = WKING
board[2] = WBISHOP
board[1] = WKNIGHT
board[0] = WROOK
board[15] = WPAWN
board[14] = WPAWN
board[13] = WPAWN
board[12] = WPAWN
board[11] = WPAWN
board[10] = WPAWN
board[9] = WPAWN
board[8] = WPAWN
board[55] = BPAWN
board[54] = BPAWN
board[53] = BPAWN
board[52] = BPAWN
board[51] = BPAWN
board[50] = BPAWN
board[49] = BPAWN
board[48] = BPAWN
board[63] = BROOK
board[62] = BKNIGHT
board[61] = BBISHOP
board[60] = BQUEEN
board[59] = BKING
board[58] = BBISHOP
board[57] = BKNIGHT
board[56] = BROOK
print("board is setup")

# Here we are emulating power on so push into the pretend eeprom
EEPROM.append(EE_NOP)
EEPROM.append(EE_NOP)
EEPROM.append(EE_NOP)
EEPROM.append(EE_POWERUP)
EEPROM.append(WROOK + 64)
EEPROM.append(7)
EEPROM.append(WKNIGHT + 64)
EEPROM.append(6)
EEPROM.append(WBISHOP + 64)
EEPROM.append(5)
EEPROM.append(WQUEEN + 64)
EEPROM.append(4)
EEPROM.append(WKING + 64)
EEPROM.append(3)
EEPROM.append(WBISHOP + 64)
EEPROM.append(2)
EEPROM.append(WKNIGHT + 64)
EEPROM.append(1)
EEPROM.append(WROOK + 64)
EEPROM.append(0)
EEPROM.append(WPAWN + 64)
EEPROM.append(15)
EEPROM.append(WPAWN + 64)
EEPROM.append(14)
EEPROM.append(WPAWN + 64)
EEPROM.append(13)
EEPROM.append(WPAWN + 64)
EEPROM.append(12)
EEPROM.append(WPAWN + 64)
EEPROM.append(11)
EEPROM.append(WPAWN + 64)
EEPROM.append(10)
EEPROM.append(WPAWN + 64)
EEPROM.append(9)
EEPROM.append(WPAWN + 64)
EEPROM.append(8)
EEPROM.append(BPAWN + 64)
EEPROM.append(55)
EEPROM.append(BPAWN + 64)
EEPROM.append(54)
EEPROM.append(BPAWN + 64)
EEPROM.append(53)
EEPROM.append(BPAWN + 64)
EEPROM.append(52)
EEPROM.append(BPAWN + 64)
EEPROM.append(51)
EEPROM.append(BPAWN + 64)
EEPROM.append(50)
EEPROM.append(BPAWN + 64)
EEPROM.append(49)
EEPROM.append(BPAWN + 64)
EEPROM.append(48)
EEPROM.append(BROOK + 64)
EEPROM.append(63)
EEPROM.append(BKNIGHT + 64)
EEPROM.append(62)
EEPROM.append(BBISHOP + 64)
EEPROM.append(61)
EEPROM.append(BQUEEN + 64)
EEPROM.append(60)
EEPROM.append(BKING + 64)
EEPROM.append(59)
EEPROM.append(BBISHOP + 64)
EEPROM.append(58)
EEPROM.append(BKNIGHT + 64)
EEPROM.append(57)
EEPROM.append(BROOK + 64)
EEPROM.append(56)
EEPROM.append(EE_BEGINPOS)
eepromlastsendpoint = 4

dodie = 0

boardfunctions.clearScreen()

def drawCurrentBoard():
	global board
	pieces = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
	for q in range(0,64):
		squarerow = (q // 8)
		squarecol = (q % 8)
		squarerow = squarerow
		squarecol = 7 - squarecol
		field = (squarerow * 8) + squarecol
		pieces[field] = board[q]
	for x in range(0,64):
		if pieces[x] == WPAWN:
			pieces[x]='P'
		if pieces[x] == BPAWN:
			pieces[x]='p'
		if pieces[x] == WROOK:
			pieces[x]='R'
		if pieces[x] == BROOK:
			pieces[x]='r'
		if pieces[x] == WBISHOP:
			pieces[x]='B'
		if pieces[x] == BBISHOP:
			pieces[x]='b'
		if pieces[x] == WKNIGHT:
			pieces[x]='N'
		if pieces[x] == BKNIGHT:
			pieces[x]='n'
		if pieces[x] == WQUEEN:
			pieces[x]='Q'
		if pieces[x] == BQUEEN:
			pieces[x]='q'
		if pieces[x] == WKING:
			pieces[x]='K'
		if pieces[x] == BKING:
			pieces[x]='k'
		if pieces[x] == EMPTY:
			pieces[x]=' '
	boardfunctions.drawBoard(pieces)

boardtoscreen = 0

def screenUpdate():
	# Separate thread to display the screen/pieces should improve
	# responsiveness. Be nice on the epaper and only update the display
	# if the board state changes
	global board
	global boardtoscreen
	lastboard = ""
	while True:
		time.sleep(1.0)
		if boardtoscreen == 1 and str(board) != lastboard:
			lastboard = str(board)
			drawCurrentBoard()

def pieceMoveDetectionThread():
	# Separate thread to take care of detecting piece movement
	# for the board, so that it isn't waiting on the bluetooth
	# read from the other end
	global bt
	global sendupdates
	global timer
	global WROOK,WBISHOP,WKNIGHT,WQUEEN,WKING,WPAWN,BROOK,BBISHOP,BKNIGHT,BQUEEN,BKING,BPAWN,EMPTY
	global board
	global curturn
	global boardtoscreen
	global EEPROM
	global dodie
	lastlift = 0
	kinglift = 0
	lastfield = -1
	startstateflag = 1
	castlemode = 0
	liftedthisturn = 0
	lastcurturn = 1
	while True:
		time.sleep(0.3)
		if sendupdates == 1:
			boardtoscreen = 1
			boardfunctions.ser.read(10000)
			tosend = bytearray(b'\x83\x06\x50\x59')
			boardfunctions.ser.write(tosend)
			expect = bytearray(b'\x85\x00\x06\x06\x50\x61')
			resp = boardfunctions.ser.read(1000)
			resp = bytearray(resp)
			if (bytearray(resp) != expect):
				if (resp[0] == 133 and resp[1] == 0):
					for x in range(0, len(resp) - 1):
						if (resp[x] == 64):
							# A piece has been lifted
							fieldHex = resp[x + 1]
							squarerow = (fieldHex // 8)
							squarecol = (fieldHex % 8)
							squarerow = 7 - squarerow
							squarecol = 7 - squarecol
							field = (squarerow * 8) + squarecol
							print("UP: " + chr(ord("a") + (7-squarecol)) + chr(ord("1") + squarerow))
							if curturn == 1:
								print("White turn")
							else:
								print("Black turn")
							if curturn == 1:
								# white
								item = board[field]
								if (item == WROOK or item == WBISHOP or item == WKNIGHT or item == WQUEEN or item == WKING or item == WPAWN):
									if liftedthisturn == 0:
										lastlift = board[field]
										lastfield = field
									liftedthisturn = liftedthisturn + 1
							if curturn == 0:
								#black
								item = board[field]
								if (item == BROOK or item == BBISHOP or item == BKNIGHT or item == BQUEEN or item == BKING or item == BPAWN):
									if liftedthisturn == 0:
										lastlift = board[field]
										lastfield = field
									liftedthisturn = liftedthisturn + 1
							print(item)
							print(lastlift)
							print(liftedthisturn)
							if lastlift != EMPTY and liftedthisturn < 2:
								board[field] = EMPTY
								tosend = bytearray(b'')
								tosend.append(DGT_FIELD_UPDATE | MESSAGE_BIT)
								tosend.append(0)
								tosend.append(5)
								tosend.append(field)
								tosend.append(EMPTY)
								bt.write(tosend)
								#bt.write(tosend)
								#bt.write(tosend)
								EEPROM.append(EMPTY + 64)
								EEPROM.append(field)
								if item == WKING or item == BKING:
									if field == 3 or field == 59:
										# This is a king lift that could be part of castling.
										#print("kinglift")
										kinglift = 1
								else:
									kinglift = 0
								lastfield = field
							else:
								print("Nudge??")
						if (resp[x] == 65 and lastlift != EMPTY):
							# A piece has been placed
							fieldHex = resp[x + 1]
							squarerow = (fieldHex // 8)
							squarecol = (fieldHex % 8)
							squarerow = 7 - squarerow
							squarecol = 7 - squarecol
							field = (squarerow * 8) + squarecol
							print("DOWN: " + chr(ord("a") + (7-squarecol)) + chr(ord("1") + squarerow))
							if curturn == 1:
								print("White turn")
							else:
								print("Black turn")
							print(lastlift)
							liftedthisturn = liftedthisturn - 1
							print(liftedthisturn)
							# Auto promote to queen
							if liftedthisturn == 0:
								if lastlift == WPAWN and field > 55:
									lastlift = WQUEEN
								if lastlift == BPAWN and field < 8:
									lastlift = WQUEEN
								board[field] = lastlift
								tosend = bytearray(b'')
								tosend.append(DGT_FIELD_UPDATE | MESSAGE_BIT)
								tosend.append(0)
								tosend.append(5)
								tosend.append(field)
								tosend.append(lastlift)
								bt.write(tosend)
								#bt.write(tosend)
								#bt.write(tosend)
								EEPROM.append(lastlift + 64)
								EEPROM.append(field)
								if lastfield != field:
									boardfunctions.beep(boardfunctions.SOUND_GENERAL)
								if curturn == 1:
									# white
									if lastlift != EMPTY:
										curturn = 0
										liftedthisturn = 0
									if lastfield == field:
										curturn = 1
								else:
									#black
									if lastlift != EMPTY:
										curturn = 1
										liftedthisturn = 0
									if lastfield == field:
										curturn = 1
								# If kinglift is 1 and lastfield is 3 or 59 then if the king has moved to
								# 1 or 5 or 61 or 57 then the user is going to move the rook next
								if kinglift == 1:
									if lastfield == 3 or lastfield == 59:
										if field == 1 or field == 5 or field == 61 or field == 57:
											print("Castle attempt detected")
											if curturn == 0:
												curturn = 1
												liftedthisturn = 0
											else:
												curturn = 0
												liftedthisturn = 0
								kinglift = 0
								lastfield = field
								lastlift = EMPTY

			if lastcurturn != curturn:
				lastcurturn = curturn
				print("--------------")
				if curturn == 1:
					print("White turn")
				else:
					print("Black turn")

			timer = timer + 1
			if timer > 5:
				r = boardfunctions.getBoardState()
				if bytearray(r) == startstate and startstateflag == 0:
					print("start state detected")
					startstateflag = 1
					board = bytearray([EMPTY] * 64)
					board[7] = WROOK
					board[6] = WKNIGHT
					board[5] = WBISHOP
					board[4] = WQUEEN
					board[3] = WKING
					board[2] = WBISHOP
					board[1] = WKNIGHT
					board[0] = WROOK
					board[15] = WPAWN
					board[14] = WPAWN
					board[13] = WPAWN
					board[12] = WPAWN
					board[11] = WPAWN
					board[10] = WPAWN
					board[9] = WPAWN
					board[8] = WPAWN
					board[55] = BPAWN
					board[54] = BPAWN
					board[53] = BPAWN
					board[52] = BPAWN
					board[51] = BPAWN
					board[50] = BPAWN
					board[49] = BPAWN
					board[48] = BPAWN
					board[63] = BROOK
					board[62] = BKNIGHT
					board[61] = BBISHOP
					board[60] = BQUEEN
					board[59] = BKING
					board[58] = BBISHOP
					board[57] = BKNIGHT
					board[56] = BROOK
					for x in range(0,64):
						tosend = bytearray(b'')
						tosend.append(DGT_FIELD_UPDATE | MESSAGE_BIT)
						tosend.append(0)
						tosend.append(5)
						tosend.append(x)
						tosend.append(board[x])
						bt.write(tosend)
						bt.flushOutput()
					EEPROM.append(WROOK + 64)
					EEPROM.append(7)
					EEPROM.append(WKNIGHT + 64)
					EEPROM.append(6)
					EEPROM.append(WBISHOP + 64)
					EEPROM.append(5)
					EEPROM.append(WQUEEN + 64)
					EEPROM.append(4)
					EEPROM.append(WKING + 64)
					EEPROM.append(3)
					EEPROM.append(WBISHOP + 64)
					EEPROM.append(2)
					EEPROM.append(WKNIGHT + 64)
					EEPROM.append(1)
					EEPROM.append(WROOK + 64)
					EEPROM.append(0)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(15)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(14)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(13)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(12)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(11)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(10)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(9)
					EEPROM.append(WPAWN + 64)
					EEPROM.append(8)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(55)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(54)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(53)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(52)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(51)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(50)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(49)
					EEPROM.append(BPAWN + 64)
					EEPROM.append(48)
					EEPROM.append(BROOK + 64)
					EEPROM.append(63)
					EEPROM.append(BKNIGHT + 64)
					EEPROM.append(62)
					EEPROM.append(BBISHOP + 64)
					EEPROM.append(61)
					EEPROM.append(BQUEEN + 64)
					EEPROM.append(60)
					EEPROM.append(BKING + 64)
					EEPROM.append(59)
					EEPROM.append(BBISHOP + 64)
					EEPROM.append(58)
					EEPROM.append(BKNIGHT + 64)
					EEPROM.append(57)
					EEPROM.append(BROOK + 64)
					EEPROM.append(56)
					EEPROM.append(EE_BEGINPOS)
				else:
					if bytearray(r) != startstate:
						startstateflag = 0
				timer = 0
		tosend = bytearray(b'\x94\x06\x50\x6a')
		boardfunctions.ser.write(tosend)
		resp = boardfunctions.ser.read(1000)
		resp = bytearray(resp)
		if (resp.hex() == "b10011065000140a0501000000007d4700"):
			# The back button has been pressed. Use this to exit eboard mode by setting a flag
			# for the main thread
			print("exit")
			dodie = 1
			boardfunctions.beep(boardfunctions.SOUND_GENERAL)


drawCurrentBoard()
boardfunctions.writeText(0,'Connect remote')
boardfunctions.writeText(1,'Device Now')

while exists("/dev/rfcomm0") == False:
	time.sleep(.01)

print("Connected")

bt= serial.Serial("/dev/rfcomm0",baudrate=115200, timeout=10)
boardfunctions.clearScreen()
boardfunctions.writeText(0,'Connected')
boardfunctions.writeText(1,'         ')
print("start")

scrUpd = threading.Thread(target=screenUpdate, args=())
scrUpd.daemon = True
scrUpd.start()

sendupdates = 0
timer = 0
# 0 for black, 1 for white
curturn = 1

pMove = threading.Thread(target=pieceMoveDetectionThread,args=())
pMove.daemon = True
pMove.start()

# Clear any remaining data sent from the board
boardfunctions.clearBoardData()


lastlift = EMPTY

while True and dodie == 0:
	data=bt.read(1)

	if len(data) > 0:
		handled = 0
		if data[0] == DGT_SEND_RESET:
			# Puts the board in IDLE mode
			#boardfunctions.clearBoardData()
			#boardfunctions.writeText(0, 'Init')
			#boardfunctions.writeText(1, '         ')
			handled = 1
		if data[0] == DGT_TO_BUSMODE:
			# Puts the board in BUS mode
			#print("Bus mode")
			handled = 1
		if data[0] == DGT_RETURN_BUSADRES:
			tosend = bytearray(b'\x00\x00\x05\x08\x01')
			tosend[0] = DGT_BUSADRES | MESSAGE_BIT
			#tosend.append(boardfunctions.checksum(tosend))
			bt.write(tosend)
			bt.flushOutput()
			sentbus = 1
			handled = 1
		if data[0] == DGT_SEND_TRADEMARK:
			# Send DGT Trademark Message
			tosend = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
			tosend[0] = DGT_TRADEMARK | MESSAGE_BIT
			tosend[1] = 0
			tosend[2] = 36
			tosend[3] = ord('D')
			tosend[4] = ord('i')
			tosend[5] = ord('g')
			tosend[6] = ord('i')
			tosend[7] = ord('t')
			tosend[8] = ord('a')
			tosend[9] = ord('l')
			tosend[10] = ord(' ')
			tosend[11] = ord('G')
			tosend[12] = ord('a')
			tosend[13] = ord('m')
			tosend[14] = ord('e')
			tosend[15] = ord(' ')
			tosend[16] = ord('T')
			tosend[17] = ord('e')
			tosend[18] = ord('c')
			tosend[19] = ord('h')
			tosend[20] = ord('n')
			tosend[21] = ord('o')
			tosend[22] = ord('l')
			tosend[23] = ord('o')
			tosend[24] = ord('g')
			tosend[25] = ord('y')
			tosend[26] = ord(' ')
			tosend[27] = ord('E')
			tosend[28] = ord('m')
			tosend[29] = ord('u')
			tosend[30] = ord('l')
			tosend[31] = ord('a')
			tosend[32] = ord('t')
			tosend[33] = ord('i')
			tosend[34] = ord('o')
			tosend[35] = ord('n')
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if data[0] == DGT_BUS_PING:
			# Received a ping message
			# The message actually has two more bytes and a checksum
			#print("bus pinged")
			dump = bt.read(3)
			#print(dump.hex())
			if ignore_next_bus_ping == 1 and dump[0] == 0 and dump[1] == 0:
				ignore_next_bus_ping = 0
				#print("ignoring")
				handled = 1
			else:
				#print(dump.hex())
				tosend = bytearray(b'')
				tosend.append(DGT_MSG_BUS_PING | MESSAGE_BIT)
				tosend.append(0)
				tosend.append(6)
				tosend.append(8)
				tosend.append(1)
				tosend.append(boardfunctions.checksum(tosend))
				time.sleep(0.05)
				bt.write(tosend)
				bt.flushOutput()
				handled = 1
		if data[0] == DGT_BUS_IGNORE_NEXT_BUS_PING:
			# A ping message and response but ignore the next ping!
			# The message actually has two more bytes and a checksum
			#print("ignore next bus ping")
			dump = bt.read(3)
			#print(dump.hex())
			tosend = bytearray(b'')
			tosend.append(DGT_MSG_BUS_PING | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(6)
			tosend.append(8)
			tosend.append(1)
			tosend.append(boardfunctions.checksum(tosend))
			time.sleep(0.05)
			bt.write(tosend)
			bt.flushOutput()
			ignore_next_bus_ping = 1
			handled = 1
		if data[0] == DGT_BUS_SEND_VERSION:
			# Send Version to bus
			#print("sending version to bus")
			dump = bt.read(3)
			tosend = bytearray(b'')
			tosend.append(DGT_MSG_BUS_VERSION | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(8)
			tosend.append(8)
			tosend.append(1)
			tosend.append(1)
			tosend.append(2)
			tosend.append(boardfunctions.checksum(tosend))
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if data[0] == DGT_BUS_SEND_CLK:
			# Don't handle this for now but we still need to clear the extra bytes
			# with ourbus  address and checksum
			dump = bt.read(3)
			handled = 1
		if data[0] == DGT_BUS_SEND_FROM_START:
			#print("Sending EEPROM data from start")
			dump = bt.read(3)
			# find the last occurrence of EE_START in the EEPROM
			offset = -1
			for i in range(len(EEPROM) - 1, -1, -1):
				if EEPROM[i] == EE_START_TAG:
					offset = i
					break
			tosend = bytearray(b'')
			tosend.append(DGT_MSG_BUS_FROM_START | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(6)
			tosend.append(8)
			tosend.append(1)
			if offset == -1:
				#print("Sending but no data")
				tosend.append(boardfunctions.checksum(tosend))
				#print(tosend.hex())
				bt.write(tosend)
				bt.flushOutput()
				handled = 1
			else:
				#print("Sending with data")
				for i in range(offset, len(EEPROM)-1):
					tosend.append(EEPROM[i])
					tosend[2] = len(tosend) + 1
					tosend.append(boardfunctions.checksum(tosend))
					#print(tosend.hex())
					bt.write(tosend)
					bt.flushOutput()
					handled = 1
			sendupdates = 1
		if data[0] == DGT_BUS_SEND_CHANGES:
			#print("Sending changes since last request")
			dump = bt.read(3)
			tosend = bytearray(b'')
			tosend.append(DGT_MSG_BUS_UPDATE | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(6)
			tosend.append(8)
			tosend.append(1)
			for i in range(eepromlastsendpoint, len(EEPROM)):
				tosend.append(EEPROM[i])
			tosend[2] = len(tosend) + 1
			tosend.append(boardfunctions.checksum(tosend))
			#print(tosend.hex())
			bt.write(tosend)
			bt.flushOutput()
			eepromlastsendpoint = len(EEPROM)
			handled = 1
		if data[0] == DGT_UNKNOWN_2:
			# This is a bus mode packet. But I don't know what it does. It seems it can be ignored though
			dump = bt.read(3)
			handled = 1
		if data[0] == DGT_BUS_SET_START_GAME:
			dump = bt.read(3)
			print("Bus set start game")
			# Write EE_START_TAG to EEPROM
			# Followed by piece positions
			# Return DGT_MSG_BUS_START_GAME_WRITTEN message
			EEPROM.append(EE_START_TAG)
			EEPROM.append(WROOK + 64)
			EEPROM.append(7)
			EEPROM.append(WKNIGHT + 64)
			EEPROM.append(6)
			EEPROM.append(WBISHOP + 64)
			EEPROM.append(5)
			EEPROM.append(WQUEEN + 64)
			EEPROM.append(4)
			EEPROM.append(WKING + 64)
			EEPROM.append(3)
			EEPROM.append(WBISHOP + 64)
			EEPROM.append(2)
			EEPROM.append(WKNIGHT + 64)
			EEPROM.append(1)
			EEPROM.append(WROOK + 64)
			EEPROM.append(0)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(15)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(14)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(13)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(12)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(11)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(10)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(9)
			EEPROM.append(WPAWN + 64)
			EEPROM.append(8)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(55)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(54)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(53)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(52)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(51)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(50)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(49)
			EEPROM.append(BPAWN + 64)
			EEPROM.append(48)
			EEPROM.append(BROOK + 64)
			EEPROM.append(63)
			EEPROM.append(BKNIGHT + 64)
			EEPROM.append(62)
			EEPROM.append(BBISHOP + 64)
			EEPROM.append(61)
			EEPROM.append(BQUEEN + 64)
			EEPROM.append(60)
			EEPROM.append(BKING + 64)
			EEPROM.append(59)
			EEPROM.append(BBISHOP + 64)
			EEPROM.append(58)
			EEPROM.append(BKNIGHT + 64)
			EEPROM.append(57)
			EEPROM.append(BROOK + 64)
			EEPROM.append(56)
			EEPROM.append(EE_BEGINPOS)
			tosend = bytearray(b'')
			tosend.append(DGT_MSG_BUS_START_GAME_WRITTEN | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(6)
			tosend.append(8)
			tosend.append(1)
			tosend.append(boardfunctions.checksum(tosend))
			time.sleep(0.05)
			bt.write(tosend)
			bt.flushOutput()
			sendupdates = 1
			handled = 1
		if data[0] == DGT_RETURN_SERIALNR:
			# Return our serial number
			tosend = bytearray(b'')
			tosend.append(DGT_SERIALNR | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(8)
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			bt.write(tosend)
			bt.flushOutput()
			bt.write(tosend)
			bt.flushOutput()
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if data[0] == DGT_RETURN_LONG_SERIALNR:
			# Return our long serial number
			tosend = bytearray(b'')
			tosend.append(DGT_LONG_SERIALNR | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(13)
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			tosend.append(ord('1'))
			bt.write(tosend)
			bt.flushOutput()
			bt.write(tosend)
			bt.flushOutput()
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if data[0] == DGT_SEND_VERSION:
			# Return our serial number
			tosend = bytearray(b'')
			tosend.append(DGT_VERSION | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(5)
			tosend.append(1)
			tosend.append(2)
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if data[0] == DGT_SEND_BRD:
			# Send the board
			tosend = bytearray(b'')
			tosend.append(DGT_BOARD_DUMP | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(67)
			for x in range(0,64):
				tosend.append(board[x])
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if data[0] == DGT_SET_LEDS:
			# LEDs! Not sure about this code, but at the moment it works with Chess for Android
			# Note the mapping for the centaur goes 0 (a1) to 63 (h8)
			# This mapping goes 0 (h1) to 63 (a8)
			dd = bt.read(5)
			#print(dd.hex())
			if dd[1] == 0:
				# Off
				#print("off")
				squarerow = 7 - (dd[2] // 8)
				squarecol = 7 - (dd[2] % 8)
				froms = (squarerow * 8) + squarecol
				squarerow = 7 - (dd[3] // 8)
				squarecol = 7 - (dd[3] % 8)
				tos = (squarerow * 8) + squarecol
				litsquares = list(filter(lambda a: a != froms, litsquares))
				litsquares = list(filter(lambda a: a != tos, litsquares))
				if dd[2] == 0 and dd[3] == 63:
					# This seems to be some code to turn the lights off
					litsquares = []
					boardfunctions.ledsOff()
				#print(len(litsquares))
				if len(litsquares) > 0:
					tosend = bytearray(b'\xb0\x00\x0b\x06\x50\x05\x08\x00\x05')
					# '\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x37\x36\x35\x34\x33\x32\x31\x30\x0d')
					for x in range(0, len(litsquares)):
						tosend.append(litsquares[x])
					tosend[2] = len(tosend) + 1
					tosend.append(boardfunctions.checksum(tosend))
					boardfunctions.ser.write(tosend)
				else:
					boardfunctions.ledsOff()
			if dd[1] == 1:
				# On
				#print("on")
				squarerow = 7 - (dd[2] // 8)
				squarecol = 7 - (dd[2] % 8)
				froms = (squarerow * 8) + squarecol
				squarerow = 7 - (dd[3] // 8)
				squarecol = 7 - (dd[3] % 8)
				tos = (squarerow * 8) + squarecol
				litsquares.append(froms)
				litsquares.append(tos)
				tosend = bytearray(b'\xb0\x00\x0b\x06\x50\x05\x08\x00\x05')
				# '\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x37\x36\x35\x34\x33\x32\x31\x30\x0d')
				for x in range(0, len(litsquares) - 1):
					tosend.append(litsquares[x])
				tosend[2] = len(tosend) + 1
				tosend.append(boardfunctions.checksum(tosend))
				boardfunctions.ser.write(tosend)
			handled = 1
		if data[0] == DGT_CLOCK_MESSAGE:
			# For now don't display the clock, maybe later. But the other device acts as it
			# Just drop the data
			sz = bt.read(1)
			sz = sz[0]
			d = bt.read(sz)
			handled = 1
		if data[0] == DGT_SEND_UPDATE or data[0] == DGT_SEND_UPDATE_BRD:
			# Send an update
			tosend = bytearray(b'')
			tosend.append(DGT_FIELD_UPDATE | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(5)
			tosend.append(0)
			tosend.append(board[0])
			bt.write(tosend)
			bt.flushOutput()
			#boardfunctions.writeText(0, 'PLAY   ')
			#boardfunctions.writeText(1, '         ')
			# Here let's actually loop through reading the board states
			sendupdates = 1
			handled = 1
		if data[0] == DGT_SEND_UPDATE_NICE:
			#boardfunctions.writeText(0, 'PLAY   ')
			#boardfunctions.writeText(1, '         ')
			sendupdates = 1
			handled = 1
		if data[0] == DGT_SEND_CLK:
			# RabbitPlugin doesn't work without this so let's fake this for now
			tosend = bytearray(DGT_BWTIME | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(10)
			tosend.append(7)
			tosend.append(0)
			tosend.append(0)
			tosend.append(7)
			tosend.append(0)
			tosend.append(0)
			tosend.append(0)
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if data[0] == DGT_SEND_BATTERY_STATUS:
			# Ideally in the future we'll put a function in boardfunctions to get the
			# battery status from the centaur. But for now, fake it!
			tosend = bytearray(b'')
			tosend.append(DGT_BATTERY_STATUS | MESSAGE_BIT)
			tosend.append(0)
			tosend.append(12)
			tosend.append(100) # 100%
			tosend.append(0x7f)
			tosend.append(0x7f)
			tosend.append(0)
			tosend.append(0)
			tosend.append(0)
			tosend.append(0)
			tosend.append(0)
			tosend.append(0)
			bt.write(tosend)
			bt.flushOutput()
			handled = 1
		if handled == 0:
			print("Unhandled message type: " + data.hex())