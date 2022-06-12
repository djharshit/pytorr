import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import a

# ====== GUI ======
wind = tk.Tk()
wind.title('Peer program')
wind.geometry('600x400')
wind.resizable(0, 0)

wind.rowconfigure(0, weight=1)
wind.columnconfigure(0, weight=1)

style = ttk.Style()
theme_names = ('winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative')
style.theme_use(theme_names[0])

# ====== Variables ======
details = []
file_detail = {}
all_files = []
download_peers = {}
uid_var = tk.StringVar()
name_var = tk.StringVar()
pwd_var = tk.StringVar()
current_file = tk.StringVar()
tracker_port_var = tk.IntVar()
my_port_var = tk.IntVar()


def start_myserver(*args):
    global my_port

    try:
        my_port = my_port_var.get()
    except:
        messagebox.showerror('Invalid', 'Wrong port number')
    else:
        my_server = a.MyServer(my_port)

        a.threading.Thread(target=my_server.accept_connections).start()

        my_port_label['text'] = f'Peer Port - {my_port}'
        second_frame.tkraise()
        trck_frame_1.tkraise()


def check_tracker(*args):
    global tracker_obj

    try:
        tracker_port = tracker_port_var.get()
    except:
        messagebox.showerror('Invalid', 'Wrong port number')
    else:
        tracker_obj = a.MyClient(tracker_port)

        if tracker_obj.server_connect():
            tracker_obj.send_msg(str(my_port).encode())
            trck_frame_2.tkraise()
            # messagebox.showinfo('Success', f'Connected to {tracker_port}')
        else:
            messagebox.showwarning('Sleeping', f'Tracker {tracker_port} is sleeping')


def login(*args):
    global details

    if not (uid_var.get() and pwd_var.get()):
        messagebox.showwarning('Invalid', 'One detail is missing')
        trck_frame_3.tkraise()
        return

    user = uid_var.get() + ' ' + pwd_var.get()
    tracker_obj.send_msg(b'login')
    tracker_obj.send_msg(user.encode())

    data = tracker_obj.receive_msg()

    tracker_msg, *details = a.pickle.loads(data).split()

    if tracker_msg in ['Wrong-password', 'Uid-not-found']:
        messagebox.showwarning('Invalid', tracker_msg)
    else:
        uid_var.set('')
        pwd_var.set('')
        name_var.set('')
        trck_frame_5.tkraise()


def register(*args):
    if not (uid_var.get() and pwd_var.get() and name_var.get()):
        messagebox.showwarning('Invalid', 'One detail is missing')
        trck_frame_3.tkraise()
        return

    user = uid_var.get() + ' ' + name_var.get() + ' ' + pwd_var.get()
    tracker_obj.send_msg(b'register')
    tracker_obj.send_msg(user.encode())

    tracker_msg = tracker_obj.receive_msg().decode()

    if tracker_msg == 'Uid existed':
        messagebox.showwarning('Invalid', tracker_msg)
    else:
        uid_var.set('')
        pwd_var.set('')
        name_var.set('')
        trck_frame_2.tkraise()

def sendfile(*args):
    global file_name

    file_name = filedialog.askopenfilename(initialdir='files/')
    if file_name:
        file_name = file_name.split('/')[-1]
        tracker_obj.send_msg(b'sendfile')

        file_block = a.FileOperation(file_name).send_file_detail()
        file_block['FileOwner'] = int(details[0]), details[1]
        file_block['PeerPorts'] = [my_port]

        data = a.pickle.dumps(file_block)
        data_length = str(len(data))

        tracker_obj.send_msg(data_length.encode())
        tracker_obj.send_msg(data)

        tracker_msg = tracker_obj.receive_msg().decode()
        messagebox.showinfo('Success', tracker_msg)

def getfiles(*args):
    global all_files

    all_files.clear()
    tracker_obj.send_msg(b'getfiles')

    data = tracker_obj.receive_msg()
    f = a.pickle.loads(data)

    if not f:
        messagebox.showwarning('Invalid', 'No file to display')
        return

    for i, j in f.items():
        all_files.append(f'{i} {j}')

    files_menu = tk.OptionMenu(trck_frame_6, current_file, *all_files)
    files_menu.grid(row=1, column=1, padx=20, pady=10)
    files_menu.grid_propagate(0)

    trck_frame_6.tkraise()

def getfiledetail(*args):
    global file_detail

    if not current_file.get():
        messagebox.showwarning('Invalid', 'Select a file first!')
        return

    s = ''
    tracker_obj.send_msg(b'getfiledetail')
    tracker_obj.send_msg(current_file.get().split()[0].encode())
    data_length = tracker_obj.receive_msg().decode()
    data = tracker_obj.receive_msg(int(data_length))

    file_detail = a.pickle.loads(data)

    for i, j in file_detail.items():
        if i in ['SHAofEveryBlock', 'SHAofFullFile']:
            continue
        s += f'{i} {j} \n'
    file_detail_label['text'] = s

def get_my_details(*args):
    def disappear():
        a.time.sleep(3)
        details_label['text'] = ''

    global details
    details_label['text'] = f'Uid: {details[0]}\nName: {details[1]} \
                             \nPort: {details[2]}'
    a.threading.Thread(target=disappear).start()

def download_file(*args):
    discon_button.state(['disabled'])

    if not current_file.get():
        messagebox.showwarning('Invalid', 'Select a file first!')
        return

    fname = current_file.get().split()[0]
    tracker_obj.send_msg(b'getfiledetail')
    tracker_obj.send_msg(fname.encode())

    data_length = tracker_obj.receive_msg().decode()
    data = tracker_obj.receive_msg(int(data_length))

    file_detail = a.pickle.loads(data)

    download_peers = {}  # Peers dict to download file from them

    for peer_client_port in file_detail['PeerPorts']:
        peer_client_obj = a.MyClient(peer_client_port)

        if peer_client_obj.server_connect():
            print('[+] Connected to peer', peer_client_port)

            download_peers[peer_client_port] = peer_client_obj
            peer_client_obj.send_msg(str(my_port).encode())
        else:
            print(peer_client_port, 'is sleeping')

    peers_no = len(download_peers)

    if peers_no == 0:
        print('No peer available')
        return

    if file_detail['NoBlocks'] % peers_no == 0:
        each_parts = file_detail['NoBlocks'] // peers_no
    else:
        each_parts = (file_detail['NoBlocks'] // peers_no) + 1

    a.time.sleep(0.5)
    fname = file_detail['FileName']
    f, l = 1, each_parts
    last = left = file_detail['NoBlocks']
    thrds = []
    tic = a.time.time()

    for k, client in download_peers.items():
        left -= each_parts

        client.send_msg(f'sendfile {fname} {f} {l}'.encode())

        fileop = a.FileOperation(fname, client)

        t = a.threading.Thread(target=fileop.receive_file,
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

    toc = a.time.time()
    print(fname, 'fully received in', round(toc-tic, 3), 'sec')
    tracker_obj.send_msg(b'more')
    tracker_obj.send_msg(fname.encode())

    discon_button.state(['!disabled'])

def disconnect_tracker(*args):
    global tracker_obj
    global details

    tracker_port_var.set('')
    tracker_obj.send_msg(b'bye')
    tracker_obj.client.close()
    details.clear()
    del tracker_obj

    trck_frame_1.tkraise()


def back(*args):
    trck_frame_2.tkraise()
    uid_var.set('')
    pwd_var.set('')
    name_var.set('')


# ====== Frames ======
initial_frame = ttk.Frame(wind, height=400, width=600)
second_frame = ttk.Frame(wind, height=400, width=600)

initial_frame.grid(row=0, column=0, sticky='nsew')
second_frame.grid(row=0, column=0, sticky='nsew')
initial_frame.grid_propagate(0)
second_frame.grid_propagate(0)

# ====== Initial Frame ======
head_label = ttk.Label(initial_frame, text='Peer program',
                       font=('', 20, 'bold'))
head_label.grid(row=0, column=0, padx=25, pady=5, columnspan=2)

my_port_label = ttk.Label(initial_frame, text='Enter your peer port')
my_port_label.grid(row=1, column=0, padx=25, pady=5, sticky=tk.E)

my_port_entry = ttk.Entry(initial_frame, textvariable=my_port_var)
my_port_entry.grid(row=1, column=1, padx=25, pady=5, sticky=tk.W)

my_port_button = ttk.Button(initial_frame, text='Start',
                            command=start_myserver)
my_port_button.grid(row=2, column=0, padx=25, pady=5, columnspan=2)

my_port_entry.focus()
initial_frame.bind(sequence='<Return>', func=start_myserver)

# ====== Second Frame ======
my_port_frame = ttk.Frame(second_frame, height=20, width=600) #, bg='yellow')
tracker_frame = ttk.Frame(second_frame, height=170, width=600) #, bg='red')
peer_frame = ttk.Frame(second_frame, height=210, width=600) #, bg='blue')

my_port_frame.grid(row=0, column=0, sticky='nsew')
tracker_frame.grid(row=1, column=0, sticky='nsew')
peer_frame.grid(row=2, column=0, sticky='nsew')
my_port_frame.grid_propagate(0)
tracker_frame.grid_propagate(0)
peer_frame.grid_propagate(0)

my_port_label = ttk.Label(my_port_frame, font=('', 20))
my_port_label.pack()

# ====== Tracker Connect Frame ======
trck_frame_1 = ttk.Frame(tracker_frame, height=170, width=600) #, bg='green')
trck_frame_1.grid(row=0, column=0)
trck_frame_1.grid_propagate(0)

head_label = ttk.Label(trck_frame_1, text='Tracker\nConnect', font=('', 15))
trck_label = ttk.Label(trck_frame_1, text='Enter tracker port')
trck_entry = ttk.Entry(trck_frame_1, textvariable=tracker_port_var)
connect_button = ttk.Button(trck_frame_1, text='Connect',
                            command=check_tracker)
quit_button = ttk.Button(trck_frame_1, text='Quit',
                         command=wind.destroy)
head_label.grid(row=0, column=0, rowspan=2, padx=20, pady=10)
trck_label.grid(row=0, column=1, padx=20, pady=10)
trck_entry.grid(row=0, column=2, padx=20, pady=10)
connect_button.grid(row=1, column=1, padx=20, pady=10)
quit_button.grid(row=1, column=2, padx=20, pady=10)

trck_entry.focus()
trck_frame_1.bind(sequence='<Return>', func=check_tracker)

# ====== Tracker Login or Register or Disconn Frame ======
trck_frame_2 = ttk.Frame(tracker_frame, height=170, width=600) #, bg='cyan')
trck_frame_2.grid(row=0, column=0)
trck_frame_2.grid_propagate(0)

login_button = ttk.Button(trck_frame_2, text='Login',
                          command=trck_frame_3.tkraise)
reg_button = ttk.Button(trck_frame_2, text='Register',
                        command=trck_frame_4.tkraise)
discon_button = ttk.Button(trck_frame_2, text='Disconnect',
                           command=disconnect_tracker)
login_button.grid(row=0, column=0, padx=30, pady=50)
reg_button.grid(row=0, column=1, padx=30, pady=50)
discon_button.grid(row=0, column=2, padx=30, pady=50)

# wind.bind('<Return>', lambda x: ...)

# ====== Tracker Login Frame ======
trck_frame_3 = ttk.Frame(tracker_frame, height=170, width=600)
trck_frame_3.grid(row=0, column=0)
trck_frame_3.grid_propagate(0)

head_label = ttk.Label(trck_frame_3, text='Login\nPage', font=('', 15))
head_label.grid(row=0, column=0, rowspan=3, padx=20, pady=10)

uid_label = ttk.Label(trck_frame_3, text='Enter your uid')
pwd_label = ttk.Label(trck_frame_3, text='Enter your password')
uid_label.grid(row=0, column=1, padx=20, pady=10)
pwd_label.grid(row=1, column=1, padx=20, pady=10)

uid_entry = ttk.Entry(trck_frame_3, textvariable=uid_var)
pwd_entry = ttk.Entry(trck_frame_3, textvariable=pwd_var, show='*')
uid_entry.grid(row=0, column=2, padx=20, pady=10)
pwd_entry.grid(row=1, column=2, padx=20, pady=10)

back_button = ttk.Button(trck_frame_3, text='Back',
                         command=back)
login_button = ttk.Button(trck_frame_3, text='Submit', command=login)
back_button.grid(row=2, column=1, padx=20, pady=10)
login_button.grid(row=2, column=2, padx=20, pady=10)

uid_entry.focus()
trck_frame_3.bind(sequence='<Return>', func=login)

# ====== Tracker Register Frame ======
trck_frame_4 = ttk.Frame(tracker_frame, height=170, width=600)
trck_frame_4.grid(row=0, column=0)
trck_frame_4.grid_propagate(0)

head_label = ttk.Label(trck_frame_4, text='Register\nPage', font=('', 15))
head_label.grid(row=0, column=0, rowspan=4, padx=20, pady=10)

name_label = ttk.Label(trck_frame_4, text='Enter your name')
uid_label = ttk.Label(trck_frame_4, text='Enter your uid')
pwd_label = ttk.Label(trck_frame_4, text='Enter your password')
name_label.grid(row=0, column=1, padx=20, pady=10)
uid_label.grid(row=1, column=1, padx=20, pady=10)
pwd_label.grid(row=2, column=1, padx=20, pady=10)

name_entry = ttk.Entry(trck_frame_4, textvariable=name_var)
uid_entry = ttk.Entry(trck_frame_4, textvariable=uid_var)
pwd_entry = ttk.Entry(trck_frame_4, textvariable=pwd_var, show='*')
name_entry.grid(row=0, column=2, padx=20, pady=10)
uid_entry.grid(row=1, column=2, padx=20, pady=10)
pwd_entry.grid(row=2, column=2, padx=20, pady=10)

back_button = ttk.Button(trck_frame_4, text='Back',
                         command=back)
login_button = ttk.Button(trck_frame_4, text='Submit', command=register)
back_button.grid(row=3, column=1, padx=20, pady=10)
login_button.grid(row=3, column=2, padx=20, pady=10)

name_entry.focus()
trck_frame_4.bind(sequence='<Return>',
                  func=lambda x: change_frame(trck_frame_2))

# ====== Tracker Sendfile or Getfile Frame ======
trck_frame_5 = ttk.Frame(tracker_frame, height=170, width=600) #, bg='pink')
trck_frame_5.grid(row=0, column=0)
trck_frame_5.grid_propagate(0)

head_label = ttk.Label(trck_frame_5, text='Options\nPage', font=('', 15))
head_label.grid(row=0, column=0, rowspan=2, padx=20, pady=10)

send_button = ttk.Button(trck_frame_5, text='Send File',
                         command=sendfile)
get_button = ttk.Button(trck_frame_5, text='Get File',
                        command=getfiles)
my_detail_button = ttk.Button(trck_frame_5, text='My Details',
                              command=get_my_details)
discon_button = ttk.Button(trck_frame_5, text='Disconnect',
                           command=disconnect_tracker)
details_label = ttk.Label(trck_frame_5, font=('', 10))

send_button.grid(row=0, column=1, padx=20, pady=10)
get_button.grid(row=0, column=2, padx=20, pady=10)
my_detail_button.grid(row=1, column=1, padx=20, pady=10)
discon_button.grid(row=1, column=2, padx=20, pady=10)
details_label.grid(row=0, column=3, rowspan=3, padx=20, pady=10)

# ====== Tracker Getfile Frame ======
trck_frame_6 = ttk.Frame(tracker_frame, height=170, width=600) #, bg='orange')
trck_frame_6.grid(row=0, column=0)
trck_frame_6.grid_propagate(0)

head_label = ttk.Label(trck_frame_6, text='File\nDetails\nPage', font=('', 15))
head_label.grid(row=0, column=0, rowspan=2, padx=20, pady=10)

file_name_label = ttk.Label(trck_frame_6, text='All Files')
# files_menu = tk.OptionMenu(trck_frame_6, current_file, value=None)
yes_button = ttk.Button(trck_frame_6, text='Get Detail', command=getfiledetail)
no_button = ttk.Button(trck_frame_6, text='Cancel',
                       command=trck_frame_5.tkraise)
download_button = ttk.Button(trck_frame_6, text='Download',
                             command=lambda: a.threading.Thread(target=download_file).start())
file_detail_label = ttk.Label(trck_frame_6)

file_name_label.grid(row=0, column=1, padx=20, pady=10)
# files_menu.grid(row=1, column=1, padx=20, pady=10)
yes_button.grid(row=0, column=2, padx=20, pady=10)
no_button.grid(row=1, column=2, padx=20, pady=10)
file_detail_label.grid(row=0, column=3, rowspan=2, padx=20, pady=10)
download_button.grid(row=2, column=2, padx=20, pady=10)

# ====== Peer Frame ======
peer_label = ttk.Label(peer_frame, text='Peer Logs')
peer_label.grid(row=0, column=0, padx=5, pady=5)

yScroll = tk.Scrollbar(peer_frame, orient=tk.VERTICAL)
yScroll.grid(row=1, column=1, sticky='ns')

peer_list = tk.Listbox(peer_frame, height=8, width=90, selectmode=tk.SINGLE, yscrollcommand=yScroll.set)
peer_list.grid(row=1, column=0, padx=15, pady=5)

yScroll['command'] = peer_list.yview

# peer_list.insert(tk.END, f'Peer {self.peer_port} -> disconnected')

initial_frame.tkraise()

wind.mainloop()
