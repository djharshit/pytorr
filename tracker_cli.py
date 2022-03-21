"""
Tracker program to and save the details of peers and files given
by them.
"""

import socket
import threading
import json
import logging
import hashlib
import pickle


class UsersDetails:
    """Class for handling user login and register.

    This class perform two tasks:
        1. Register the new peer and act accordingly
        2. Login the existing peer, if success then update the
           new port of the user

    Attributes:
        peer_port (int): Port of the peer from which this class is called
    """

    def __init__(self, peer_port: int):
        self.peer_port = peer_port

    def peer_register(self, dtls: list) -> str:
        """Registration of the peer for first time and
           Save details in details.json.

        Args:
            dtls (list): ['Uid', 'Name', 'Password']

        Returns:
            msg: Register message
        """
        details_lock.acquire()

        with open('users.json', 'r+') as f:
            usrs = json.load(f)

            for i in usrs['users']:
                if int(dtls[0]) == i['uid']:
                    m = 'Uid existed'
                    break

            else:
                pwd = hashlib.sha256(dtls[2].encode()).hexdigest()
                # print(pwd)
                d = dict(uid=int(dtls[0]), name=dtls[1],
                         password=pwd, port=self.peer_port)

                usrs['users'].append(d)

                f.truncate(0)
                f.seek(0)
                json.dump(usrs, f, indent=4)

                m = 'User details saved'
                logging.debug(f'Peer {self.peer_port} -> {dtls[0]} {dtls[1]} registerd')

        details_lock.release()
        return m

    def peer_login(self, dtls: list) -> str:
        """Login of peer using his details and
           updating its new port in both files.

        Args:
            dtls (list): ['Uid', 'Password']

        Returns:
            msg: Login message
        """
        details_lock.acquire()

        with open('users.json', 'r+') as f:
            users = json.load(f)

            for i in users['users']:
                if int(dtls[0]) == i['uid']:
                    pwd = hashlib.sha256(dtls[1].encode()).hexdigest()
                    # print(pwd)
                    if pwd == i['password']:
                        logging.debug(f'Peer {self.peer_port} -> {dtls[0]} logged in')

                        old_port = i['port']
                        i['port'] = self.peer_port
                        m = f"Login-successful {i['uid']} {i['name']} {i['port']}"

                        # Update the port no if login success in details
                        f.truncate(0)
                        f.seek(0)
                        json.dump(users, f, indent=4)

                        self.update_ports(old_port)
                        break

                    else:
                        m = 'Wrong-password'
                        break
            else:
                m = 'Uid-not-found'

        details_lock.release()
        return m

    def update_ports(self, old_port: int) -> None:
        """Update the port no of the file it has send in files.

        Args:
            old_port (int): Old port of the peer
        """
        files_lock.acquire()

        with open('files.json', 'r+') as f:
            files = json.load(f)

            for j in files['files']:
                if old_port in j['PeerPorts']:

                    j['PeerPorts'].remove(old_port)
                    j['PeerPorts'].append(self.peer_port)

            f.truncate(0)
            f.seek(0)
            json.dump(files, f, indent=4)

        files_lock.release()


class FileOperation:
    """Class for handling all file related operations.

    This class perform four tasks:
        1. Register a new file in the files
        2. Show only name and size of all files to the peer
        3. Return all details of a particular file to the peer
        4. Update the current PeerPorts list of the file

    Attributes:
        peer_port (int): Port of the peer from which this class is called
        uid (int): Uid of the peer from which this class is called
    """

    def __init__(self, peer_port: int, uid: int):
        self.peer_port = peer_port
        self.uid = uid

    def file_entry(self, file_block: dict) -> str:
        """Save file details provided by peer in the files.

        Args:
            file_block (dict): Dictionary of file details

        Returns:
            str: File details saved
        """
        files_lock.acquire()

        logging.debug(f'Peer {self.peer_port} Uid {self.uid} Savefile name {file_block["FileName"]}')

        with open('files.json', 'r+') as f:
            files = json.load(f)

            files['files'].append(file_block)

            f.truncate(0)
            f.seek(0)
            json.dump(files, f, indent=4)

        files_lock.release()
        return 'File details saved'

    def file_show(self) -> dict:
        """Show only the names and size of all files so that the peer can
           choose one from it.

        Returns:
            dict: File names and size dictionary
        """
        files_lock.acquire()

        logging.debug(f'Peer {self.peer_port} Uid {self.uid} Ask for files')

        d = {}
        with open('files.json') as f:
            files = json.load(f)
            for i in files['files']:
                fname, fsize = i['FileName'], i['TotalSize']
                d[fname] = fsize

        files_lock.release()
        return d

    def file_detail(self, name: str) -> dict:
        """Give all details of the particular file to the peer

        Args:
            name (str): Name of the file

        Returns:
            dict: The file details dictionary
        """
        files_lock.acquire()

        logging.debug(f'Peer {self.peer_port} Uid {self.uid} Ask for file {name} detail')

        with open('files.json') as f:
            files = json.load(f)

            for i in files['files']:
                if i['FileName'] == name:
                    detail = i
                    break

        files_lock.release()
        return detail

    def update_peer(self, fname: str):
        """Update the file PeerPorts to the port of the peer.

        Args:
            fname (str): File name to which port be added
        """
        files_lock.acquire()

        with open('files.json', 'r+') as f:
            files = json.load(f)

            for i in files['files']:
                if i['FileName'] == fname:
                    if self.peer_port in i['PeerPorts']:
                        break
                    i['PeerPorts'].append(self.peer_port)

                    f.truncate(0)
                    f.seek(0)
                    json.dump(files, f, indent=4)

                    break
        files_lock.release()

    def delete_peer(self):
        """Delete the peer from PeerPorts if it is logged out.
        """
        files_lock.acquire()

        with open('files.json', 'r+') as f:
            files = json.load(f)

            for i in files['files']:
                if self.peer_port in i['PeerPorts']:
                    i['PeerPorts'].remove(self.peer_port)

            f.truncate(0)
            f.seek(0)
            json.dump(files, f, indent=4)

        files_lock.release()


class MyPeer:
    """Class for handling the peer messages and act accordingly.

    This class perform one task:
        1. Chat with the particular peer and act accordingly to
           the condition

    Attributes:
        conn (socket.socket): Connection object of the peer client
        peer_port (int): Port of the peer from which it is chatting
    """

    def __init__(self, conn, peer_port: int):
        self.conn = conn
        self.peer_port = peer_port
        self.detail = []
        self.uid = 0

        self.user_obj = UsersDetails(peer_port)
        self.file_obj = FileOperation(peer_port, 0)

    def peer_chat(self):
        """Chat with the particular peer and act accordingly to
           the condition.
        """
        while True:
            try:
                msg = self.conn.recv(1024).decode()
            except ConnectionResetError:
                print(f'[+] Peer {self.peer_port} unexpectedly disconnected')
                logging.info(f'Peer {self.peer_port} unexpectedly disconnected')
                break

            print(f'Peer {self.peer_port} -> {msg}')
            logging.info(f'Peer {self.peer_port} -> {msg}')

            if msg == 'register':
                msg = self.conn.recv(1024).decode()

                print(self.peer_port, '->', msg)
                msg = msg.split()
                msg = self.user_obj.peer_register(msg)
                self.conn.send(msg.encode())

            elif msg == 'login':
                msg = self.conn.recv(1024).decode()

                print(self.peer_port, '->', msg)
                msg = self.user_obj.peer_login(msg.split())

                data = pickle.dumps(msg)
                self.conn.send(data)

                self.detail = msg.split()[1:]
                if self.detail != []:
                    self.file_obj.uid = self.uid = self.detail[0]

            elif msg == 'sendfile':
                data_length = self.conn.recv(1024).decode()
                data = self.conn.recv(int(data_length))

                file_block = pickle.loads(data)
                if file_block == 'No-File':
                    msg = 'No-File'
                else:
                    msg = self.file_obj.file_entry(file_block)

                self.conn.send(msg.encode())

            elif msg == 'getfiles':
                d = self.file_obj.file_show()
                data = pickle.dumps(d)
                self.conn.send(data)

            elif msg == 'getfiledetail':
                fname = self.conn.recv(1024).decode()

                if fname != 'No-File':
                    d = self.file_obj.file_detail(fname)

                    data = pickle.dumps(d)
                    data_length = str(len(data))

                    self.conn.send(data_length.encode())
                    self.conn.send(data)

            elif msg == 'more':
                fname = self.conn.recv(1024).decode()
                self.file_obj.update_peer(fname)

            elif msg == 'bye':
                # self.file_obj.delete_peer()
                print('[+] Disconnected from peer', self.peer_port)
                logging.warning(f'Peer {self.peer_port} -> disconnected')
                self.conn.close()
                break

            else:
                self.conn.send(b'Wrong input')

# ====== Main ======

# Log file configurations
log_format = '{asctime} | {levelname} | {lineno} | {threadName} | {message}'
logging.basicConfig(filename='tracker.log', level=logging.DEBUG, style='{',
                    format=log_format, filemode='a')

# Setting Locks for the files
details_lock = threading.RLock()
files_lock = threading.RLock()


tracker_port = int(input('Enter tracker port:'))
tracker_server = socket.socket()

host = '127.0.0.1'  # socket.gethostbyname(comp_nme)
tracker_server.bind((host, tracker_port))
tracker_server.listen(10)

print('[+] Tracker started on', tracker_port)
logging.warning(f'Tracker started on {tracker_port}')

while True:
    conn, addr = tracker_server.accept()
    tracker_server.settimeout(None)

    peer_port = conn.recv(10).decode()
    print('[+] New Peer', peer_port)

    my_peer = MyPeer(conn, int(peer_port))

    t = threading.Thread(target=my_peer.peer_chat)
    logging.info(f'New Peer {peer_port} with thread {t.name}')
    t.start()

tracker_server.close()
