"""Simple Peer Command Line Program."""


import socket
import threading
import pickle
import hashlib
import time
from os import path


class FileOperation:
    """File Operation class: handling all file related operations.

    This class perform three tasks:
        1. Make file detail in specific format and send it to MyServer class
        2. Send the file to the peer in chunks
        3. Receive the file from the peer

    Attributes:
        fname (str): Name of the file
        conn (socket.socket): Peer connection socket object
    """

    whole_file = []

    def __init__(self, fname, conn=None):
        """Init method of FileOperation class."""
        self.fname = fname
        self.conn = conn

    def send_file_detail(self) -> dict:
        """Send the file detail provided by peer to tracker in the specified format.

        Returns:
            dict : Dictionary of file block in specified format
        """
        file_block = {}
        no_blocks = 0
        size = 512 * 1024   # 512 kb

        file_block['FileName'] = self.fname
        # file_block['FileOwner'] = int(details[0]), details[1]
        file_block['TotalSize'] = path.getsize(f'./files/{self.fname}')
        file_block['SHAofEveryBlock'] = []
        # file_block['PeerPorts'] = [server_port]

        with open(f'./files/{self.fname}', 'rb') as f:
            data = f.read(size)
            file_hsh = hashlib.sha1()

            while data:
                no_blocks += 1

                block_hsh = hashlib.sha1(data).hexdigest()
                file_block['SHAofEveryBlock'].append(block_hsh)
                file_hsh.update(data)

                data = f.read(size)

        file_block['SHAofFullFile'] = file_hsh.hexdigest()
        file_block['NoBlocks'] = no_blocks

        return file_block

    def send_file(self, start: int, end: int):
        """Send the file from start to end in the specified size (chunks) to the conn object.

        Args:
            start (int): Starting part of the file
            end (int): Ending part of the file
        """
        file_parts = []
        size = 512 * 1024   # 512 kb

        with open(f'./files/{self.fname}', 'rb') as f:
            data = f.read(size)

            while data:
                file_parts.append(data)
                data = f.read(size)

        for i in range(start, end + 1):
            print(f'Send part {i}')
            peer_list.insert(tk.END, f'Send part {i}')
            data = [i, file_parts[i - 1]]
            self.conn.send(pickle.dumps(data))
            time.sleep(0.5)

    @classmethod
    def receive_file(cls, fname: str, client, start: int, sha_list: list):
        """Recieve the file in chunks from different peers and append it to the new created file.

        Args:
            fname (str): Name of the file
            client : Peer client object
            start (int): Statring part of the specified file part
            sha_list (list): SHA1 list of the specified file parts
        """
        size = 513 * 1024   # 512 kb -> file_part | 1 kb -> part_number
        cls.whole_file += [0] * len(sha_list)

        for i, i_hsh in enumerate(sha_list):

            data = client.receive_msg(size)
            no, block = pickle.loads(data)

            b_hsh = hashlib.sha1(block).hexdigest()

            if i_hsh == b_hsh:
                print(f'Receiving {i + start} OK')
                peer_list.insert(tk.END, f'Receiving {i + start} OK')
                cls.whole_file[no - 1] = block
                time.sleep(0.5)
            else:
                print('Corrupted', i + start)

        if cls.whole_file.count(0) != 0:
            print(cls.whole_file.index(0)+1, 'Error')
        else:
            print('All OK')

        time.sleep(1)
        with open(f'./files/{fname}', 'wb+') as f:
            for i in cls.whole_file:
                if type(i) is int:
                    print(cls.whole_file.index(i)+1, '====== Corrupted ======')
                    continue
                f.write(i)

        client.send_msg(b'bye')
        client.client.close()


class MyServer:
    """Server class: handling server objects.

    This class perform three tasks:
        1. Accept connections from other peers
        2. Receive messages from peers
        3. Send the file in chunks to the peer

    Attributes:
        server : Server socket object
        port (int): Peer port (Server port)
    """

    def __init__(self, port: int):
        """Init method of MyServer class."""
        self.host = '127.0.0.1'
        self.port = port

        self.server = socket.socket()
        self.server.bind((self.host, self.port))
        self.server.listen(5)

    def accept_connections(self):
        """Accept peer clients connections request."""
        while True:
            conn, addr = self.server.accept()
            peer_server_port = conn.recv(1024).decode()
            print('[+] New Peer', peer_server_port)
            threading.Thread(target=self.receive_msg,
                             args=[conn, peer_server_port]).start()

    @staticmethod
    def receive_msg(conn, addr):
        """Receive messages from the other peers.

        Args:
            conn : Socket connection object
            addr : Peer port no
        """
        while True:
            msg = conn.recv(1024).decode()
            print(addr, '->', msg)

            if msg == 'bye':
                print(addr, 'disconnected')
                conn.close()
                break

            elif msg.startswith('sendfile'):
                fname, f, l = msg.split()[1:]
                f, l = int(f), int(l)

                FileOperation(fname, conn).send_file(f, l)

    def close_connections(self):
        self.server.close()


class MyClient:
    """Client class: handling clients objects.

    This class perform four tasks:
        1. Try to connect to the server
        2. Send messages to and receive messages from tracker
        3. Send messages to the peer
        4. Receive file in chunks from the peer

    Attributes:
        client : Client socket object
        port (int): Server port number
    """

    def __init__(self, port):
        """Init method of MyClient class.

        Args:
            port (TYPE): Description
        """
        self.client = socket.socket()
        self.port = port
        self.host = '127.0.0.1'

    def server_connect(self) -> bool:
        """Connect to the given server port.

        Returns:
            bool : True if server accepts connection, otherwise False
        """
        try:
            self.client.connect((self.host, self.port))
        except ConnectionRefusedError:
            return False
        else:
            return True

    def send_msg(self, bin_msg: bytes) -> None:
        """Send the message (bytes) to the server.

        Args:
            bin_msg (bytes): Message in bytes
        """
        self.client.send(bin_msg)

    def receive_msg(self, size: int=1024) -> bytes:
        """Receive the message (bytes) from the server.

        Optional Args:
            size (int): Buffer size of receiving message

        Returns:
            bytes: Message in bytes
        """
        return self.client.recv(size)


def tracker() -> bool:
    """Handling tracker client object.

    Returns:
        bool: True if connected with the tracker, otherwise False
    """
    global tracker_client

    t_port = int(input('Enter tracker port:\n'))
    tracker_client = MyClient(t_port)

    if tracker_client.server_connect():
        # print('[+]` Connected to', t_port)
        tracker_client.send_msg(str(server_port).encode())
        return True

    else:
        # print('Tracker not found')
        return False


def options():
    """List of options."""
    print('''List of options:-
            connecttracker (t)
            register (r)
            login (l)
            mydetail (m)
            sendfile (s)
            getfiles (g)
            getfiledetail (f)
            downloadfile (d)
            quittracker (k)
            quit (q)
            help (h)
            ''')

# __main__

details = []
file_detail = {}
all_files = {}
is_tracker = False
tracker_client = None
size = 512 * 1024  # 512 kb

def main():
    # Peer server object
    server_port = int(input('Enter your port:\n'))
    my_server = MyServer(server_port)

    threading.Thread(target=my_server.accept_connections, daemon=True).start()

    # User input
    while True:

        msg = input('Enter option or help(h)\n').lower()

        # Tracker chatting
        if msg == 't' and not is_tracker:  # Connect to tracker
            is_tracker = tracker()

        elif msg == 'r' and is_tracker:  # Register in tracker
            tracker_client.send_msg(b'register')

            tracker_msg = input('Enter details: uid name password:\n')
            tracker_client.send_msg(tracker_msg.encode())

            tracker_msg = tracker_client.receive_msg().decode()
            print(tracker_msg)

        elif msg == 'l' and is_tracker:  # Login in tracker
            tracker_client.send_msg(b'login')

            tracker_msg = input('Enter details: uid password:\n')
            tracker_client.send_msg(tracker_msg.encode())

            data = tracker_client.receive_msg()

            tracker_msg, *details = pickle.loads(data).split()
            print(tracker_msg)

        elif msg == 'm' and is_tracker:  # Print my details
            if details:
                print(details)

            else:
                print('Login first')

        elif msg == 's' and details:  # Send file detail to tracker
            tracker_client.send_msg(b'sendfile')

            fname = input('Enter file name:\n')

            if fname:
                fileop = FileOperation(fname)
                file_block = fileop.send_file_detail()

                data = pickle.dumps(file_block)
                data_length = str(len(data))
            else:
                data = pickle.dumps('No-File')
                data_length = '100'

            tracker_client.send_msg(data_length.encode())
            tracker_client.send_msg(data)

            tracker_msg = tracker_client.receive_msg().decode()
            print(tracker_msg)

        elif msg == 'g' and details:  # Get all files name and size
            tracker_client.send_msg(b'getfiles')

            data = tracker_client.receive_msg()
            all_files = pickle.loads(data)

            if not all_files:
                print('No file to display')
                continue

            for i, j in all_files.items():
                print(i, j)

        elif msg == 'f' and details:  # Get all details about a file
            tracker_client.send_msg(b'getfiledetail')

            fname = input('Enter file name:\n')

            if fname in all_files:
                tracker_client.send_msg(fname.encode())

                data_length = tracker_client.receive_msg().decode()
                data = tracker_client.receive_msg(int(data_length))

                file_detail = pickle.loads(data)

                for i, j in file_detail.items():
                    if i in ['SHAofEveryBlock', 'SHAofFullFile']:
                        continue
                    print(i, j)

            else:
                tracker_client.send_msg(b'No-File')
                print('Wrong file name')

        elif msg == 'k' and is_tracker:  # Disconnect from tracker
            tracker_client.send_msg(b'bye')
            tracker_client.client.close()
            details.clear()
            is_tracker = False
            tracker_client = None

            print('[+] Disconnected from tracker')

        # ============ Download The File From Peers ============
        elif msg == 'd':
            fname = input('File name to download:\n')

            if fname not in all_files:
                print('There is no such file')
                continue
            try:
                tracker_client.send_msg(b'getfiledetail')
                tracker_client.send_msg(fname.encode())
            except AttributeError:
                print('No file detail...connect to tracker')
                continue

            data_length = tracker_client.receive_msg().decode()
            data = tracker_client.receive_msg(int(data_length))

            file_detail = pickle.loads(data)

            download_peers = {}  # Peers dict to download file from them

            for peer_client_port in file_detail['PeerPorts']:
                peer_client_obj = MyClient(peer_client_port)

                if peer_client_obj.server_connect():
                    print('[+] Connected to peer', peer_client_port)

                    download_peers[peer_client_port] = peer_client_obj
                    peer_client_obj.send_msg(str(server_port).encode())
                else:
                    print(peer_client_port, 'is sleeping')

            peers_no = len(download_peers)

            if peers_no == 0:
                print('No peer available')
                continue

            if file_detail['NoBlocks'] % peers_no == 0:
                each_parts = file_detail['NoBlocks'] // peers_no
            else:
                each_parts = (file_detail['NoBlocks'] // peers_no) + 1

            time.sleep(0.5)
            fname = file_detail['FileName']
            f, l = 1, each_parts
            last = left = file_detail['NoBlocks']
            thrds = []

            for k, client in peers.items():
                left -= each_parts

                client.send_msg(f'sendfile {fname} {f} {l}'.encode())

                fileop = FileOperation(fname, client)

                t = threading.Thread(target=fileop.receive_file,
                                     args=[fname, client, f,
                                           file_detail['SHAofEveryBlock'][f-1:l]])
                thrds.append(t)
                t.start()

                f += each_parts
                if left >= each_parts:
                    l += each_parts
                else:
                    l = last

            for i in thrds:
                i.join()

            print(fname, 'fully received')
            tracker_client.send_msg(b'more')
            tracker_client.send_msg(fname.encode())

        elif msg == 'h':  # Print options
            options()

        elif msg == 'q':  # Quit from program
            if not is_tracker:
                print('[+] Bye')
                break

            else:
                print('Not allowed to quit')

        else:
            print('Something went wrong')


if __name__ == '__main__':
    main()

# == END ==
