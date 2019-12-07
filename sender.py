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
        self.__fileb = file_.read()
        self.__file_name :str= os.path.split(file_.name)[-1]

        self.__isinitiative = initiative

    def __init_socket(self) -> socket.socket:
        soc = socket.socket()
        soc.bind((self.__ip, self.__port))

        return soc

    def __convert_length_to_bytes(self, length :int) -> bytes:
        print('file size = %s' % length)
        if length >= 2 ** (FILE_SIZE_DESC * 8):
            raise OverflowError('file to large!')

        return int(length).to_bytes(FILE_SIZE_DESC, 'big')  # byteorder = big

    def __convert_filename_length_to_bytes(self, length:int) -> bytes:
        if length >= 2 ** (FILE_NAME_DESC * 8):
            raise OverflowError('file name to long!')

        return int(length).to_bytes(FILE_NAME_DESC, 'big')

    def __get_file_bytes(self) -> bytes:
        '''
        struct file_b {
            6bytes sign_b,
            4bytes file_size_b,
            2bytes file_name_length_b,
            bytes  file_name_b
            bytes  file_content
        }
        '''

        fnlenb = self.__convert_filename_length_to_bytes(len(self.__file_name))
        szlenb = self.__convert_length_to_bytes(len(self.__fileb))
        fnb = self.__file_name.encode('UTF-8')

        result = SIGN + szlenb + fnlenb + fnb + self.__fileb

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

            conn.send(self.__get_file_bytes())

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
            
            print('sending file...')
            soc.send(self.__get_file_bytes())

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
    argp.add_argument('-p',type=int, default=4949)
    argp.add_argument('-ip', default='127.0.0.1')
    argp.add_argument('-w', action='store_true')
    argp.add_argument('file')

    nsp = argp.parse_args()

    s_port = nsp.p
    s_ip = nsp.ip
    f_name = nsp.file

    sender = Sender(open(f_name, 'rb'), s_ip=s_ip, s_port=s_port)
    sender.connect_and_send(nsp.w)


if __name__ == '__main__':
    main()
