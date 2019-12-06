import socket
import io

FILE_SIZE_DESC = 4
EACH_BLOCK_SIZE = 1024  # (bytes)
FILE_NAME_DESC = 2
SIGN = b'LANCOM'

def _print_progress_bar(total, now, length=10):
    layout = '[%s%s]'
    b1 = '='
    b2 = '>'
    prog = int(now / total * length)
    
    res = layout % (b1 * (prog - 1), b2)

    print('\r%s' % res)

class Receiver:
    def __init__(self, s_ip :str='127.0.0.1', s_port :int=1026):
        self.__ip = s_ip
        self.__port = s_port
        self.__socket = self.__init_socket()

    def __init_socket(self) -> socket.socket:
        soc = socket.socket()
        
        print('connecting... %s : %s' % (self.__ip, self.__port))
        soc.connect((self.__ip, self.__port))
        print('Successfully connected to %s : %s' % (self.__ip, self.__port))

        return soc

    def __get_head(self) -> tuple:
        '''
        return (length, file_name)
        '''
        sign = self.__socket.recv(len(SIGN))
        
        # check sign
        if sign != SIGN : raise Exception('Unknown sign!')

        fslength = int.from_bytes(self.__socket.recv(FILE_SIZE_DESC), 'big')
        fnlength = int.from_bytes(self.__socket.recv(FILE_NAME_DESC), 'big')
        
        fn = self.__socket.recv(fnlength).decode('UTF-8')
        
        return (fslength, fn)


    def receive_and_save(self, file_ :io.BufferedReader=None):
        try:
            print('receiving from socket...')

            length, file_name = self.__get_head()
            
            print('file size = %s bytes' % length)
            print('file name : %s' % file_name)
            
            fb = b''
            real_block_count = length // EACH_BLOCK_SIZE  # 完整BLOCK的数量
            last_b = length - real_block_count  # 剩下最后的BLOCK的bytes

            for count in range(real_block_count):
                print('[receiving] Block %s / %s\r' % (count+1, real_block_count), end='')
                fb += self.__socket.recv(EACH_BLOCK_SIZE)
            else:
                print('[receiving] Almost finish...')
                fb += self.__socket.recv(last_b)

            total_bytes = len(fb) + FILE_SIZE_DESC

            print('Successfully receive %s bytes' % (total_bytes))

            if len(fb) != length:
                print('A : The file may not be complete! \a')

            if not file_:
                file_ = open(file_name, 'wb')
            
            print('writing to \'%s\'' % file_.name)
            file_.write(fb)

            print('Successfully write %s bytes into \'%s\'' % (
                total_bytes - FILE_SIZE_DESC, file_.name))
        finally:
            self.__socket.close()

    def just_receive(self) -> bytes:
        bf = b''

        while True:
            tempb = self.__socket.recv(EACH_BLOCK_SIZE)
            if not tempb:
                break
            bf += tempb

        return bf

def main():
    import argparse

    # parse_argument

    f = None

    argp = argparse.ArgumentParser()
    argp.add_argument('-p', type=int, help='port (default 4949)',
                        default=4949)
    argp.add_argument('-ip', help='IP address (default localhost)', default='127.0.0.1')
    argp.add_argument('-f', help='filename', default=None)
    argp.add_argument('-b',
            help='each block size (byte) (default 1024)'
            , type=int,default=1024)

    nsp = argp.parse_args()
    
    s_port = nsp.p
    s_ip = nsp.ip

    if nsp.f:
        f = open(nsp.f, 'wb')
    
    EACH_BLOCK_SIZE = nsp.b

    receiver = Receiver(s_ip=s_ip, s_port=s_port)
    receiver.receive_and_save(f)
    
    if f:
        f.close()


if __name__ == '__main__':
    main()
