import socket
import io
import os.path
import sys

from constants import *

class Sender:
    def __init__(self, file_ :io.BufferedReader, s_ip :str='127.0.0.1', s_port :int=1026, initiative=True):
        self.__ip = s_ip
        self.__port = s_port
        self.__socket :socket.socket = None   \
                if initiative else self.__init_socket()
        self.__file = file_
        self.__file_size = os.path.getsize(file_.name)
        self.__file_name :str= os.path.split(file_.name)[-1]

        self.__isinitiative = initiative

    def __init_socket(self) -> socket.socket:
        soc = socket.socket()
        soc.bind((self.__ip, self.__port))

        return soc

    def __get_block_desc(self) -> tuple:
        '''
        return (block_count, block_size, tail_size)
        '''

        return (self.__file_size // EACH_BLOCK_SIZE, 
                EACH_BLOCK_SIZE,
                self.__file_size % EACH_BLOCK_SIZE)

    def __convert_length_to_bytes(self, length :int) -> bytes:
        #print('file size = %s' % length)
        if length >= 2 ** (FILE_SIZE_DESC * 8):
            raise OverflowError('file to large!')

        return int(length).to_bytes(FILE_SIZE_DESC, 'big')  # byteorder = big

    def __convert_filename_length_to_bytes(self, length:int) -> bytes:
        if length >= 2 ** (FILE_NAME_DESC * 8):
            raise OverflowError('file name to long!')

        return int(length).to_bytes(FILE_NAME_DESC, 'big')

    def __convert_number_to_bytes(self, size :int, value :int, describe :str) -> bytes:
        if 2 ** (size * 8) < value:
            raise OverflowError('%s to large!')
        return int(value).to_bytes(size, 'big')

    def __get_file_bytes(self) -> bytes:
        '''
        struct file_b {
            head_b head,
            bytes  file_content
        }
        '''

        head = self.__get_head_bytes()

        return head + self.__fileb

    def __get_head_bytes(self) -> bytes:
        '''
        struct head_b {
            6bytes sign_b,
            4bytes block_count_b,
            4bytes block_size_b,
            8bytes tail_size_b
            2bytes file_name_length_b,
            bytes  file_name_b
        }
        '''

        block_c, block_s, tail_s = self.__get_block_desc()

        blockc_b = self.__convert_number_to_bytes(BLOCK_COUNT_SIZE, block_c, 'block count')
        blocks_b = self.__convert_number_to_bytes(BLOCK_SIZE_SIZE, block_s, 'block size')
        tails_b  = self.__convert_number_to_bytes(TAIL_SIZE_SIZE, tail_s, 'tail size')

        fnb = self.__file_name.encode('UTF-8')
        fnlenb = self.__convert_filename_length_to_bytes(len(fnb))

        result = SIGN + blockc_b + blocks_b + tails_b + fnlenb + fnb

        return result


    def __listen_and_send(self):
        if self.__isinitiative:
            raise Exception('This sender is in initiative mode!')

        try:
            self.__socket.listen(1)

            print('listening at %s : %s ...' % (self.__ip, self.__port))
            conn :socket.socket = None
            conn, addr = self.__socket.accept()

            print('%s : %s connected !' % addr)
            print('sending file...')

            #conn.send(self.__get_file_bytes())

            conn.close()

            print('finish!')
        except KeyboardInterrupt:
            pass
        finally:
            if conn : conn.close()
            self.__socket.close()

    def connect_and_send(self, wait=False):
        if not self.__isinitiative:
            raise Exception('This sender is in passive mode!')

        try:
            soc = socket.socket()
            print('connecting to %s : %s ...' % (self.__ip, self.__port))
            soc.connect((self.__ip, self.__port))
            
            print('Connected!')
            print('shaking hands with receiver...')

            # head shaking...
            # receiver must send a sign text that means successfully shaking
            # hands.
            if soc.recv(len(SHAKING_SIGN)) != SHAKING_SIGN:
                print('Failure to shake hands :(')
                soc.close()
                return

            soc.send(ANSWER_SIGN)

            print('Successfully shaking hands')

            # send a file
            soc.send(self.__get_head_bytes())  # head first

            # spilt file into a block size
            block_c, block_s, tail_s = self.__get_block_desc()
            
            print('sending file...')
            print('file size = %s' % (self.__file_size))

            for count in range(block_c):
                soc.send(self.__file.read(block_s))
                print('[sending] Block %s / %s     \r' % (count + 1, block_c), end='')
            else:
                soc.send(self.__file.read(tail_s))
                print('[sending] almost finish...      ')

            if wait:
                print('Waiting for receiver finish...')
                if soc.recv(len(RECEIVER_FINISH_SIGN)) != RECEIVER_FINISH_SIGN:
                    print('E: receiver may haven\'t finish...')
                else:
                    print('finish!')
            
            else:
                print('finish!')

            soc.close()
        except ConnectionRefusedError:
            print('E: maybe receiver is not online')
        finally:
            soc.close()



def main():
    import argparse
    
    argp = argparse.ArgumentParser()
    argp.add_argument('-p', type=int, default=4949,
            help='set port')
    argp.add_argument('-ip', default='127.0.0.1',
            help='set ip (IPv4) address')
    argp.add_argument('-w', action='store_true',
            help='wait for receiver finish')
    argp.add_argument('file', help='the file to send')

    nsp = argp.parse_args()

    s_port = nsp.p
    s_ip = nsp.ip
    f_name = nsp.file

    sender = Sender(open(f_name, 'rb'), s_ip=s_ip, s_port=s_port)
    sender.connect_and_send(nsp.w)


if __name__ == '__main__':
    main()
