import socket
import io
import sys
import os.path

from constants import *
from recv_config import *

def _print_progress_bar(total, now, length=10):
    layout = '[%s%s]'
    b1 = '='
    b2 = '>'
    prog = int(now / total * length)
    
    res = layout % (b1 * (prog - 1), b2)

    print('\r%s' % res)

class Receiver:
    def __init__(self, s_ip :str='127.0.0.1', s_port :int=1026, standby_mode :bool=True):
        self.__ip = s_ip
        self.__port = s_port
        self.__socket = self.__init_socket()   \
                        if not standby_mode else None

        self.__standby_mode = standby_mode

        self.__interior_call = False

    def __init_socket(self) -> socket.socket:
        soc = socket.socket()
        
        try:
            print('connecting... %s : %s' % (self.__ip, self.__port))
            soc.connect((self.__ip, self.__port))
            print('Successfully connected to %s : %s' % (self.__ip, self.__port))
            return soc

        except ConnectionRefusedError:
            print('E:  maybe sender is not online')
            sys.exit(1)

    def __get_file_path(self, filename :str) -> str:
        if not os.path.exists(RECV_DIRECTORY):
            os.mkdir(RECV_DIRECTORY)
        return os.path.join(RECV_DIRECTORY, filename)

    def __get_head(self) -> tuple:
        '''
        return (block_count, block_size, tail_size, file_name)
        return -1  : Unknown sign
        
        struct head_b {
            6bytes sign_b,
            4bytes block_count_b,
            4bytes block_size_b,
            8bytes tail_size_b
            2bytes file_name_length_b,
            bytes  file_name_b
            }
        '''
        sign = self.__socket.recv(len(SIGN))
        
        # check sign
        if sign != SIGN : return -1

        block_count = int.from_bytes(self.__socket.recv(BLOCK_COUNT_SIZE), 'big')
        block_size = int.from_bytes(self.__socket.recv(BLOCK_SIZE_SIZE), 'big')
        tail_size = int.from_bytes(self.__socket.recv(TAIL_SIZE_SIZE), 'big')

        fnlength = int.from_bytes(self.__socket.recv(FILE_NAME_DESC), 'big')
        fname = self.__socket.recv(fnlength).decode('UTF-8')
        
        return (block_count, block_size, tail_size, fname)
    
    def __interior_receive_and_save(self):
        self.__interior_call = True
        self.receive_and_save()
        self.__interior_call = False

    def __recv_block_by_recursion(self, length :int) -> bytes:
        b = self.__socket.recv(length)

        if len(b) != length:
            return b + self.__recv_block(length - len(b))  # 递归调用，直至接收完全
        return b

    def __recv_block_by_iteration(self, length :int) -> bytes:
        b = self.__socket.recv(length)
        last_b = length - len(b)

        while last_b > 0:
            bf = self.__socket.recv(last_b)
            last_b -= len(bf)
            b += bf
        return b

    __recv_block = __recv_block_by_iteration

    def receive_and_save(self, file_ :io.BufferedReader=None):
        if self.__standby_mode and not self.__interior_call:
            raise Exception('This receiver is in standby mode!')

        try:
            print('receiving from socket...')

            h = self.__get_head()
            if h == -1:
                print('E: Unknown sign')
                return

            block_count, block_size, tail_size, file_name = h
            file_size = block_count * block_size + tail_size
            
            print('file size = %s bytes' % file_size)
            print('file name : %s' % file_name)

            fp = self.__get_file_path(file_name)

            if not file_:
                file_ = open(fp, 'wb')

            # receive the file

            total_bytes = 0

            for count in range(block_count):
                fb = self.__recv_block(block_size)
                file_.write(fb)
                total_bytes += len(fb)

                print('[receiving] Block %s / %s         \r' % (count + 1, block_count) ,end='')
            
            else:
                fb = self.__recv_block(tail_size)
                file_.write(fb)
                total_bytes += len(fb)

                print('[receiving] Almost finish...      ')

            if total_bytes != file_size:
                print('A: The file may incomplete  actual = %s  received = %s' % (file_size, total_bytes))

            print('Successfully write %s bytes into \'%s\'' % (
                total_bytes, file_.name))
            
            self.__socket.send(RECEIVER_FINISH_SIGN)  # finish
        finally:
            self.__socket.close()

    def just_receive(self) -> bytes:
        bf = b''

        soc = socket.socket()
        soc.bind((self.__ip, self.__port))
        soc.listen(1)
        
        print('listening at %s : %s' % (self.__ip, self.__port))
        conn, addr = soc.accept()

        print('%s : %s connected!' % addr)
        
        print('shaking hands with sender...')

        # handshaking...
        conn.send(SHAKING_SIGN)
        
        ans = conn.recv(len(ANSWER_SIGN))

        if ans != ANSWER_SIGN:
            raise Exception('Failure to shake hands :(')

        print('Successfully shaking hands!')

        print('receiving...')

        while True:
            tempb = conn.recv(EACH_BLOCK_SIZE)
            if not tempb:
                break
            bf += tempb

        return bf

    def listen_and_receive(self):
        if not self.__standby_mode:
            raise Exception('This receiver is in initiative mode!')

        server = socket.socket()
        server.bind((self.__ip, self.__port))
        server.listen(1)

        tsk_c = 1

        try:
            while True:
                print('--> Task %s' % tsk_c)
                print('standby at %s : %s' % (self.__ip, self.__port))
                conn, addr = server.accept()
                self.__socket = conn
                print('%s : %s connected!' % addr)

                print('shaking hands with sender...')

                # handshaking...
                conn.send(SHAKING_SIGN)
                
                ans = conn.recv(len(ANSWER_SIGN))

                if ans != ANSWER_SIGN:
                    raise Exception('Failure to shake hands :(')

                print('Successfully shaking hands!')

                print()

                self.__interior_receive_and_save()

                print('\n')

                tsk_c += 1
        except KeyboardInterrupt:
            pass
        finally:
            if self.__socket : self.__socket.close()



def main():
    import argparse

    # parse_argument

    global RECV_DIRECTORY

    f = None
    fp = RECV_DIRECTORY

    argp = argparse.ArgumentParser()
    argp.add_argument('-p', type=int, help='port (default 4949)',
                        default=4949)
    argp.add_argument('-ip', help='IP address (default localhost)', default='127.0.0.1')
    argp.add_argument('-f', default=None,
            help='save the file to a specific path')
    argp.add_argument('-b', 
            help='each block size (byte) (default 8192)'
            , type=int,default=8192)
    argp.add_argument('-d', help='path to save')

    nsp = argp.parse_args()
    
    s_port = nsp.p
    s_ip = nsp.ip

    if nsp.f:
        f = open(nsp.f, 'wb')
    if nsp.d:
        if not os.path.isdir(nsp.d):
            print('E: \'%s\' is not a directory!')
            return

        RECV_DIRECTORY = nsp.d
    
    global EACH_BLOCK_SIZE
    EACH_BLOCK_SIZE = nsp.b

    receiver = Receiver(s_ip=s_ip, s_port=s_port, standby_mode=True)
    receiver.listen_and_receive()
    
    if f:
        f.close()


if __name__ == '__main__':
    main()
