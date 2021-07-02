"""
Copyrights ©
Code by: Faizan Ahmed (245112) and M. Deedahwar Mazhar (243516)
Class: BESE-9A
Subject: Computer Networks
Project: Downloading large mp4 file from single server using TCP, downloading from multiple servers using TCP + File Segmentation + File Recombination
"""
# import statements
from socket import *        #Import socket for the socket (IP/TCP) connection between client and the server
from threading import *     #Import threading to introduce multiple servers
from time import *          #To calculate the running time of the program
import os                   #To use the functions like getting path of the file
import argparse             #To enter the command line arguments as flags

# Class ServerThread to create multiple threads for multiple servers
class ServerThread(Thread):
    global pointer
    global filename

    def __init__(self, port, serverNumber):
        """
        This is the constructor of this class
        It is used to intialize the values
        Port and Server number
        """
        Thread.__init__(self)
        self.port = port                    # Sets the port number to the current port (thread) being dealt
        self.serverNumber = serverNumber    # Server number tells the number of the current connected server

    def run(self):
        """
        This function performs the main functionality.
        It takes the file name and file size and divides the file into fragments
        Sends them to the server
        And receives the fragments of the file sent by the server
        It also handles any server failure
        """
        while True:
            #increasing the scope of the variables by declaring them global
            global pointer
            global fileName
            global bytes_transferred
            global number_of_fragments
            global path
            global rest
            global total_bytes_transferred
            global start
            global start_time
            global download_speed
            global stop
            global total_bytes
            global fragment_recv_elapsed_time
            
            threadLock.acquire()
            ######################CREATING SOCKET#############################
            client_socket = socket(AF_INET, SOCK_STREAM)
            try:
                pointer_inner = pointer
                #connecting the socket with the server
                client_socket.connect((serverIP, self.port))

                print(client_socket.recv(1024).decode())
                client_socket.send(fileName.encode())                     #sending file name to the server
                print(client_socket.recv(1024).decode())

                file_status = (client_socket.recv(1024)).decode()         #recieving the file status weather it is available or not

                ######################IF FILE IS NOT FOUND#######################
                if file_status == "notfound":
                    print("Disconnecting")
                    exit()                           #exiting the program
                    threadLock.release()             #releasing the server threads
                    client_socket.close()            #closing the client socket
                    break

                #printing the total number of fragments into which file is divided
                print("Number of segments into which the file is divided: ", number_of_fragments)

                #sending the pointer to the server. This pointer tells how many bytes of the file have been received
                client_socket.send(str(pointer).encode())

                global file_size
                #Receiving the file size
                file_size = int((client_socket.recv(1024)).decode())
                print("File size = ", file_size)                    #printing the file size

                #changing variable type
                number_of_fragments = int(number_of_fragments)

                #Sending the number of fragments to the server
                client_socket.send(str(number_of_fragments).encode())
                fragmentSize = file_size // number_of_fragments     #calculating size of each segment

                if file_size % 2 != 0:
                    total_bytes_transferred += 1/number_of_fragments
                    

                #sending server number
                client_socket.send(str(self.serverNumber).encode())

                ####################CHECKING IF FILE IS GREATER THAN 5MB OR NOT###################
                if 5242880 <= file_size:
                    #If file is grater than or equal to 5MB
                    #Sending the file
                    if self.serverNumber == 1:
                        recv_file = open(path, "ab")    #opening the file in the specified path
                    else:
                        recv_file = open(path, "ab")    #opening the file in the specified path

                    print("\nReceiving...\n")
                    sleep(2)

                    #####PRINTING THE OUTPUT REPORTING METRICS#####
                    while True:
                        sleep(3)
                        rest += 3
                        start_recv_time = time()
                        if (self.serverNumber == 1 and start == False):
                            start_time = start_recv_time

                        #receiving the file from the server
                        data = client_socket.recv(fragmentSize)
                        if not data:
                            break

                        #measuring file/segment transferring time
                        stop_time = time()
                        if (self.serverNumber == 1 and start == False):
                            fragment_recv_elapsed_time = stop_time - start_recv_time
                        else:
                            fragment_recv_elapsed_time = (stop_time - start_recv_time) - (rest - 3)

                        #writing the received data in the opened file
                        recv_file.write(data)

                        #getting the values stored in the variables
                        bytes_transferred[self.serverNumber-1] += len(data)
                        total_bytes_transferred += len(data)
                        download_time = stop_time - start_time
                        download_speed[self.serverNumber -1] = round((len(data) / download_time) / 1024, 3)
                        start = True

                    #Closing the file
                    recv_file.close()
                    print("The required fragment is recieved successfully")
                    threadLock.release()

                ##########IF FILE IS LESS THAN 5MB##########
                else:
                    print("File size less than 5 MB")
                    sleep(5)
                    threadLock.release()
                    client_socket.close()
                    exit()
                break

            #########IN CASE OF ANY ERROR#########
            except:
                global server_ports

                #if the client server connection is disrupted
                print("Connection lost to the server " + str(self.serverNumber))
                #the program will try to reconnect to the currently available ports
                print("\nReconnecting...\n")
                active_server_ports = []

                ########THIS IS DONE TO REDISTRIBUTE THE FILE AND RECEIVE IT FROM THE AVAILABLE SERVERS########
                active_server_ports = getActiveServers(server_ports)
                number_of_fragments = 0

                #number of fragments will be equal to the aount of servers available
                number_of_fragments = len(active_server_ports)

                ###########IF NO SERVER IS ACTIVE THEN THE PROGRAM WILL BE EXITED GRACEFULLY#########
                if len(active_server_ports) == 0:
                    print("Connection left: None")
                    print("Exiting...")
                    sleep(5)
                    exit()                      #exiting the program
                    threadLock.release()
                    client_socket.close()       #closing the client socket

                ###########IF SERVERS ARE ACTIVE THEN IT WILL START THE PROGRAM AGAIN########
                else:
                    pointer = 0
                    total_bytes_transferred = 0
                    if os.path.exists(path):
                        os.remove(path)         #if a half downloaded file already exits in that directory it will be deleted and will be redistributed among available servers
                    print("file deleted")
                    threadLock.release()
                    print("Connected to server(s) at port(s): ", *active_server_ports)

                    #Creating threads again
                    startThreads(active_server_ports)
                    break


##################################################    FUNCTIONS   ######################################################

def getActiveServers(all_ports):
    """
    This function is used to get the list of currently available servers
    it takes the list of all server ports
    and returns the list of the active ports after checking
    """
    global active_servers
    active_servers = []
    for available_ports in all_ports:
        check_socket = socket(AF_INET, SOCK_STREAM)
        result_of_check = check_socket.connect_ex((serverIP, available_ports))      #checking if the port is active
        if result_of_check == 0:
            active_servers.append(available_ports)                                  #appending the active port into the list
        check_socket.close()
    return active_servers                                                           #retrunung the list f active ports/servers


def pointerCheck(file_location):
    """
    This function is to cater the download resumption part of this program
    it gets the pointer to the number of bytes downloaded
    so therefore when we resume the download, the file starts downloading from where it left
    """
    if os.path.exists(file_location):
        downloaded_size = os.stat(file_location).st_size                            #getting the size in bytes of the downloaded file
        print(downloaded_size / 1024, " KBs already downloaded")
        return downloaded_size
    else:
        return 0


def startThreads(ports_available):
    """
    This function starts the threads
    Since this rogram uses multi-threading to
    make connections with multiple servers
    """
    global number_of_fragments
    number_of_fragments = 0
    for list in range(0, len(ports_available)):
        newThread = ServerThread(ports_available[list], list + 1)
        newThread.start()                   #this transfers the action to the run function of the class
        number_of_fragments += 1            #increasing number of fragments (it will be equal to the number of servers)
        Threads.append(newThread)

def output():
    """
    This function is to print the output
    Output includes speed, downloaded bytes etc
    The format of printing was a requirement
    """
    global total_bytes_transferred
    global file_size
    stop = False
    if total_bytes_transferred == file_size:
        sleep(1)
        stop= True
    
    
    total_bytes_delivered = 0
    
    os.system('cls')
    fragmentSize = int(file_size) // number_of_fragments
    for s in range(0, len(ports_available)):
        total_bytes[s] = fragmentSize
        total_bytes_delivered += bytes_transferred[s]

        #printing format
        print("Server ", s+1, ": ", "<", bytes_transferred[s], ">",
              "/", "<", total_bytes[s], ">", ", downloading speed: ", "<",  download_speed[s], ">", "  kb/s\n")
    if start == True :
        complete_file_speed = round((total_bytes_delivered/fragment_recv_elapsed_time)/1024, 3)

        #printing format
        print("Total: ", "<", total_bytes_delivered, ">", "/", "<", file_size,
              ">", " , downloading speed: ", "<", complete_file_speed, ">", "  kb/s\n")
    else:
        print("Total: ", "<", total_bytes_delivered, ">", "/", "<", file_size,
              ">", " , downloading speed: ", "<", 0, ">", "  kb/s\n")
    if stop == True :
        print("Download completed")         #exiting program
    else:
        sleep(interval)
        output()        #recursion

##################################################    MAIN CODE   ######################################################

#Command line arguments
#Flags input
#Requirement of this project
parser = argparse.ArgumentParser(description = "Client wants to download a video file from multiple servers.")

#-i flag for intervval
parser.add_argument("-i", "--interval", help = "Interval in seconds.", type=int, default = 3)
#-o flag for output path
parser.add_argument("-o", "--output_path", help = "Location of output file (complete path without file name).", type = str, default = "C:\\Users\\Deedahwar\\Desktop\\client")
#-a flag for server IP
parser.add_argument("-a", "--serverIP", help = "Server IP address.", type = str, default = gethostname())
#-p for list of ports
parser.add_argument("-p", "--portsList", nargs = "+", help = "List of port numbers", type = int, default=[12345, 12346, 12347, 12348])
#-r flag to answer the resumption question
parser.add_argument("-r", "--resume", type = str, help = "Do you want to resume the disrupted download [Y/N]?", default="Y")

args = parser.parse_args()

#parsing all the argument to the variables
interval = args.interval            #the interval for this client
location = args.output_path         #output location of the file received
serverIP = args.serverIP            #IP address of the server
server_ports = args.portsList       #list of server ports
resume = args.resume                #weather to resume the disrupted download or not

#Initializing variables
number_of_fragments = 0             # Number of fragments into which the file will be divided

total_bytes_transferred = 0         #Total number of bytes received
bytes_transferred = [0, 0, 0, 0]    #Number of bytes transferred to the client
total_bytes = [0, 0, 0, 0]          #List of bytes for all the servers
download_speed = [0, 0, 0, 0]       #Downlaoding speed
start = False                       #Boolean start
stop = False                        #and stop variables
rest = 0                            #resting time
start_time = 0                      #starting time of the file transfer

Threads = []                        #variable for threads
file_size = "0"                       #variable for file size
threadLock = Lock()                 #Locking the threads

#Function call to get the list of all active ports/servers
ports_available = getActiveServers(server_ports)

if len(ports_available) < 4:
    print("\nConnection to port(s) ", *(list(set(server_ports) - set(ports_available))), "due to unavailability")

print("Connected to server(s) at port(s): ", *ports_available)

#Getting the name of the file from the user
fileName = input("Enter the name of the MP4 file (with .mp4): ")

#joining the output path and file name to get a full name with extension
path = os.path.join(location, fileName)

#calling the pointer check function to check weather a file already exist in the path specified
pointer = pointerCheck(path)

#catering the resumption part
if pointer == 0:
    print("\nStarting download...\n")
if pointer != 0:
    print("\nFile found of size: ", os.stat(path).st_size)
    if resume == "N" or resume == "n":
        os.remove(path)
        pointer = 0
        print("\nFile removed, starting from 0%")
    else:
        print("\nResuming...\n")

#Starting to createthreads
startThreads(ports_available)

#Creating threads to display the output
displayThread = Thread(target = output())
displayThread.start()



#stopping the execution of the program as long as the threads are running
for i in Threads:
    i.join()
displayThread.join()

#Printing the rest of the statements
if os.path.exists(path):

    if file_size == os.stat(path).st_size - pointer or file_size - 1 == os.stat(path).st_size - pointer:
        print("The .mp4 file has been successfully recieved")

    if file_size != 0:
        print("The location of the recieved file: ", path)                                      #location of the receieved file
        print("List of ports connected on this client: ", *getActiveServers(server_ports))      #list of connected ports
        print("IP Addresses of the connected servers: ")                                        #IP address of the host
        for i in range(len(ports_available)):
            ip = gethostname()
            print(ip, sep=", ")


####################################################   THE END   #######################################################
