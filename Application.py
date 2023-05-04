import socket
import argparse
from struct import *
import os
import threading
import queue
import random
import time
TIMEOUT = 0.5
header_format = '!IIHH'
def create_packet(seq, ack, flags, win, data):
    header = pack(header_format, seq, ack, flags, win)
    packet = header + data
    return packet
def parse_flags(flags):
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    return syn, ack, fin
def parse_header(header):
    seq, ack, flags, win = unpack(header_format, header)
    return seq, ack, flags, win
def send_packet(socket, packet, addr):
    socket.sendto(packet, addr)
def recv_packet(socket, size=1472):
    msg, addr = socket.recvfrom(size)
    seq, ack, flags, win = parse_header(msg[:12])
    syn, ack_flag, fin = parse_flags(flags)
    return msg, addr, seq, ack, syn, ack_flag, fin
def send_ack(socket, seq, addr):
    ack_packet = create_packet(seq, seq+1, 4, 0, b'')
    send_packet(socket, ack_packet, addr)
    print(f"Sent ACK packet for seq {seq} to client.")
def recv_ack(socket):
    try:
        msg, addr, seq, ack, syn, ack_flag, fin = recv_packet(socket)
        if ack_flag:
            return ack, addr
        else:
            return None, None
    except socket.timeout:
        return None, None            

def stop_and_wait(args):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    syn_packet = create_packet(0, 0, 8, 0, b'')
    send_packet(client_socket, syn_packet, (args.ip, args.port))
    print("Sent packet with SYN flag to server.")

    client_socket.settimeout(5)
    ignore_ack_once = args.test
    while True:
        msg, server_addr, seq, ack, syn, ack_flag, fin = recv_packet(client_socket)
        if ack_flag and ack == 1:
            print("Received ACK packet from server.")
            send_ack(client_socket, 0, server_addr)
            print("Three way handshake is complete!")
            break
    seq_number = 1
    with open(args.file, "rb") as f:
        while True:
            data = f.read(1460)
            if not data:
                break
            data_packet = create_packet(seq_number, 0, 0, 0, data)
            send_packet(client_socket, data_packet, (args.ip, args.port))
            print(f"Sent packet with file data (seq {seq_number}) to server.")

            while True:
                try:
                    msg, server_addr, seq, ack, syn, ack_flag, fin = recv_packet(client_socket)
                    if ack_flag and ack == seq_number + 1:
                        print(f"Received ACK packet for seq {seq_number} from server.")
                        break
                except socket.timeout:
                    print(f"Timeout waiting for ACK for seq {seq_number}. Retransmitting...")
                    send_packet(client_socket, data_packet, (args.ip, args.port))
            seq_number += 1

    fin_packet = create_packet(seq_number, 0, 2, 0, b'')
    send_packet(client_socket, fin_packet, (args.ip, args.port))
    print("Sent packet with FIN flag to server.")
    client_socket.close()
def gbn_client(args):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(5)  # Set socket timeout to 5 seconds
    syn_packet = create_packet(0, 0, 8, 0, b'')
    send_packet(client_socket, syn_packet, (args.ip, args.port))
    print("Sent packet with SYN flag to server.")
   
    with open(args.file, "rb") as f:
        while True:
            try:
                msg, server_addr, seq, ack, syn, ack_flag, fin = recv_packet(client_socket)

                if ack_flag and ack == 1:
                    print("Received ACK packet from server.")
                    print("Three-way handshake connection is established.")
                    break
            except socket.timeout:
                print("Timeout waiting for SYN-ACK packet. Resending SYN packet.")
                send_packet(client_socket, syn_packet, (args.ip, args.port))

        base = 1
        next_seq = 1
        window_size = 3
        pkt_buffer = queue.Queue()
        eof = False
        while not eof or not pkt_buffer.empty():
            while next_seq < base + window_size and not eof:
                data = f.read(1460)
                if not data:
                    eof = True
                else:
                    data_packet = create_packet(next_seq, 0, 0, 0, data)
                    send_packet(client_socket, data_packet, (args.ip, args.port))
                    print(f"Sent packet with file data (seq {next_seq}) to server.")
                    pkt_buffer.put((next_seq, data_packet))
                    next_seq += 1

            if pkt_buffer.empty():
                break

            try:
                msg, server_addr, seq, ack, syn, ack_flag, fin = recv_packet(client_socket)
                if ack_flag and seq==base:
                        _, removed_packet = pkt_buffer.get()
                        base += 1
                    
            except socket.timeout:
                print(f"Timeout waiting for ACKs. Resending unacknowledged packets starting from {base}.")
                for i in range(pkt_buffer.qsize()):
                    seq, data_packet = pkt_buffer.queue[i]
                    send_packet(client_socket, data_packet, (args.ip, args.port))
                    print(f"Resent packet with file data (seq {seq}) to server.")

        fin_packet = create_packet(next_seq, 0, 2, 0, b'')
        send_packet(client_socket, fin_packet, (args.ip, args.port))
        print("Sent packet with FIN flag to server.")

def sr_client(args):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(5)  # Set socket timeout to 5 seconds
    syn_packet = create_packet(0, 0, 8, 0, b'')
    send_packet(client_socket, syn_packet, (args.ip, args.port))
    print("Sent packet with SYN flag to server.")

    with open(args.file, "rb") as f:
        while True:
            try:
                msg, server_addr, seq, ack, syn, ack_flag, fin = recv_packet(client_socket)

                if ack_flag and ack == 1:
                    print("Received ACK packet from server.")
                    print("Three-way handshake connection is established.")
                    break
            except socket.timeout:
                print("Timeout waiting for SYN-ACK packet. Resending SYN packet.")
                send_packet(client_socket, syn_packet, (args.ip, args.port))

        base = 1
        next_seq = 1
        window_size = 3
        pkt_buffer = queue.Queue()
        acked_packets = set()
        eof = False
        while not eof or not pkt_buffer.empty():
            while next_seq < base + window_size and not eof:
                data = f.read(1460)
                if not data:
                    eof = True
                else:
                    data_packet = create_packet(next_seq, 0, 0, 0, data)
                    send_packet(client_socket, data_packet, (args.ip, args.port))
                    print(f"Sent packet with file data (seq {next_seq}) to server.")
                    pkt_buffer.put((next_seq, data_packet))
                    next_seq += 1

            if pkt_buffer.empty():
                break

            try:
                msg, server_addr, seq, ack, syn, ack_flag, fin = recv_packet(client_socket)
                if ack_flag:
                    acked_packets.add(seq)
                    if seq == base:
                        while base in acked_packets:
                            _, removed_packet = pkt_buffer.get()
                            base += 1
            except socket.timeout:
                print("Timeout waiting for ACKs. Resending unacknowledged packets.")
                for i in range(pkt_buffer.qsize()):
                    seq, data_packet = pkt_buffer.queue[i]
                    if seq not in acked_packets:
                        send_packet(client_socket, data_packet, (args.ip, args.port))
                        print(f"Resent packet with file data (seq {seq}) to server.")

        fin_packet = create_packet(next_seq, 0, 2, 0, b'')
        send_packet(client_socket, fin_packet, (args.ip, args.port))
        print("Sent packet with FIN flag to server.")


def server(args):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)# Making the socket. 
    server_socket.bind((args.ip, args.port))# Binding the socket
    print("-------------------------------------")
    print(f"Server is listening on port {args.port}")# INFO
    print("-------------------------------------")
    recvd_file = open(args.file, "wb")# Opening a file with the name given by the user and start writing the data we get in that file. 
    buffer = [None] * (args.window_size * 2)
    base=1
    expected_seq = 1
    prev_seq = None  # Keep track of the previous sequence number
    
    #New
    base = 0
    received_packets = {}
    skip_ack=False
    skipnr=args.test
    #New
    out_of_order_buffer = {}
    while True:# 
        msg, client_addr, seq, ack, syn, ack_flag, fin = recv_packet(server_socket)# The parameters we recieve from the client. 
        if syn:# If a packet SYN flag recv
            print("Received packet with SYN flag.")# INFO
            send_ack(server_socket, 0, client_addr)
        elif fin:# If the server recvieve a packet with fin flag!
            print("Received packet with FIN flag.")#INFO
            recvd_file.close()
            print("File transfer complete. File saved as", args.file)#INFO
            break
        elif ack:# This is for the thre way handshake 
            continue
        if args.reliability =='gbn':
                if seq == base:
                    if seq==skipnr and not skip_ack :
                        print(f"Skiping the ack for {seq}")
                        skip_ack=True
                        continue
                    else:
                        print("Received file data packet.")
                        recvd_file.write(msg[12:])
                        base += 1
                        ack_packet = create_packet(seq, base, 4, 0, b'')
                        send_packet(server_socket, ack_packet, client_addr)
                        print(f"Sent ACK packet for seq {seq} to client.")
                
                else:
                    print(f"Received out-of-order packet with seq {seq}. Discarding and not sending ACK.")
            
        elif args.reliability == 'sr':
            print(f"Received file data packet with packet {seq}.")
            if seq == base:
                if seq==skipnr and not skip_ack:
                    print(f"skipping ack for packet{seq} ")
                    skip_ack=True  
                    continue
                else:
                    recvd_file.write(msg[12:])
                    base += 1
                    while base in out_of_order_buffer:
                        recvd_file.write(out_of_order_buffer.pop(base))
                        base += 1
            else:
                out_of_order_buffer[seq] = msg[12:]

            ack_packet = create_packet(seq, base, 4, 0, b'')
            send_packet(server_socket, ack_packet, client_addr)
            print(f"Sent ACK packet for seq {seq} to client.")
        elif args.reliability=='stop_and_wait':
            if prev_seq == seq:  # Check if it's a duplicate packet
                  print("Received duplicate packet.")# INFO
            elif seq==skipnr and not skip_ack:
                print(f"Skipping the ack for packet with seq {seq}")
                skip_ack=True
                continue
            else: 
                print("Received file data packet.")
                recvd_file.write(msg[12:])# From every packet we get, we know that the first 12 are the header. Thats why we write after those 12. 
                prev_seq = seq  # Update the previous sequence number
            # Send ACK for every received packet
            ack_packet = create_packet(seq, seq+1, 4, 0, b'')# Creating an ack for every packet we recive. 
            send_packet(server_socket, ack_packet, client_addr)# Sending the ack. 
            print(f"Sent ACK packet for seq {seq} to client.")# INFO
def client(args):
    if args.reliability == 'stop_and_wait':
        stop_and_wait(args)
    elif args.reliability == 'gbn':
        gbn_client(args)
    elif args.reliability == 'sr':
        sr_client(args)
    else:
        print("Not working on client side.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--client",        action="store_true", help="Run as client.")
    parser.add_argument("-s", "--server",        action="store_true", help="Run as server.")
    parser.add_argument('-i', '--ip',            type=str,            default="10.0.0.1",   help='Server IP address.')
    parser.add_argument("-f", "--file",          type=str,            required=True,        help="File to transfer.")
    parser.add_argument('-p', '--port',          default=3030,        type=int,             help='Server port number.')
    parser.add_argument("-r", "--reliability",   type=str,            choices=["stop_and_wait", "gbn", "sr"], default= 'stop_and_wait', help="Reliability function to use.")
    parser.add_argument("-t", "--test",          type=int,            default=-1,           help="Ignore for the ack with specified seq number")
    parser.add_argument('-w', '--window_size',   default=5, type=int, help="THe window size")
    args = parser.parse_args()
    if args.client:
        client(args)
    elif args.server:
        server(args)
